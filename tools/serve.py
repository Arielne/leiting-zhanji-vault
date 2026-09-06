#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/serve.py — xem vault trên điện thoại theo thời gian thực.

Làm gì:
    1. Theo dõi mọi file *.md ở gốc vault và mọi ảnh trong _assets/
    2. Có thay đổi -> tự chạy lại export.py
    3. Phục vụ _export/ qua Wi-Fi để điện thoại mở được
    4. Trang trên điện thoại tự tải lại khi bản xuất đổi — không phải bấm gì

Nghĩa là: sửa markdown trên máy, lưu, ngó sang điện thoại, đã thấy nội dung mới.

Chạy:
    python tools/serve.py            # cổng mặc định 8787
    python tools/serve.py 9000       # đổi cổng

Dừng: Ctrl+C

Lưu ý:
    - Máy tính và điện thoại phải cùng một mạng Wi-Fi.
    - Lần đầu chạy, Windows Firewall sẽ hỏi cho phép Python mở cổng. Phải bấm
      "Allow" / "Cho phép", nếu không điện thoại sẽ không vào được.
    - Chỉ thư mục _export/ được phục vụ. Markdown gốc, _inbox/ và .git/ không
      bị lộ ra mạng.
    - Đây là mạng nội bộ, không ra Internet. Tắt bằng Ctrl+C là hết.
"""
from __future__ import annotations

import socket
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import export  # noqa: E402  (phải chèn sys.path trước)

ROOT = export.ROOT
ASSETS = export.ASSETS
EXPORT = export.EXPORT

CHU_KY_QUET = 1.0          # giây giữa hai lần kiểm tra thay đổi
CHU_KY_HOI = 2000          # mili giây giữa hai lần trang hỏi "có bản mới chưa"

# Tăng mỗi lần xuất lại. Trang trên điện thoại so số này để biết khi nào reload.
_phien_ban = 0
_khoa = threading.Lock()

# Script nhỏ chèn vào lúc phục vụ. KHÔNG ghi vào file trên đĩa — wiki.html
# phải giữ nguyên là bản offline tự chứa, chép sang điện thoại là chạy được.
SCRIPT_TU_TAI_LAI = """
<script>
(function(){
 var pb=null;
 async function ngo(){
  try{
   var r=await fetch('/__phienban',{cache:'no-store'});
   var t=(await r.text()).trim();
   if(pb===null){pb=t;}
   else if(t!==pb){location.reload();}
  }catch(e){}
 }
 setInterval(ngo,__CHUKY__);
 ngo();
})();
</script>
"""


def chu_ky_thu_muc():
    """Chữ ký của toàn bộ nguồn. Đổi chữ ký = có gì đó vừa sửa."""
    muc = []
    for p in sorted(ROOT.glob("*.md")):
        try:
            st = p.stat()
            muc.append((p.name, st.st_mtime_ns, st.st_size))
        except OSError:
            pass
    if ASSETS.is_dir():
        for p in sorted(ASSETS.glob("*")):
            if p.is_file():
                try:
                    st = p.stat()
                    muc.append(("_assets/" + p.name, st.st_mtime_ns, st.st_size))
                except OSError:
                    pass
    return tuple(muc)


def canh_gac():
    """Chạy nền: thấy nguồn đổi thì xuất lại và tăng số phiên bản."""
    global _phien_ban
    truoc = chu_ky_thu_muc()
    while True:
        time.sleep(CHU_KY_QUET)
        sau = chu_ky_thu_muc()
        if sau == truoc:
            continue
        truoc = sau
        try:
            if export.xuat(im_lang=True):
                with _khoa:
                    _phien_ban += 1
                print("  [%s] nguồn đổi -> đã xuất lại (phiên bản %d)"
                      % (time.strftime("%H:%M:%S"), _phien_ban))
        except Exception as e:                      # noqa: BLE001
            print("  [%s] xuất lại HỎNG: %s" % (time.strftime("%H:%M:%S"), e))


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):                               # noqa: N802
        duong = self.path.split("?")[0]

        if duong == "/__phienban":
            with _khoa:
                than = str(_phien_ban).encode("ascii")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(than)))
            self.end_headers()
            self.wfile.write(than)
            return

        if duong in ("/", "/index.html", "/wiki.html"):
            self._tra_wiki()
            return

        super().do_GET()

    def _tra_wiki(self):
        f = EXPORT / "wiki.html"
        if not f.is_file():
            self.send_error(404, "Chua co wiki.html — chay tools/export.py truoc")
            return
        doc = f.read_text(encoding="utf-8")
        chen = SCRIPT_TU_TAI_LAI.replace("__CHUKY__", str(CHU_KY_HOI))
        if "</body>" in doc:
            doc = doc.replace("</body>", chen + "</body>", 1)
        else:
            doc += chen
        than = doc.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(than)))
        self.end_headers()
        self.wfile.write(than)

    def end_headers(self):
        # Đừng để trình duyệt điện thoại giữ bản cũ trong bộ nhớ đệm.
        # Đặt ở đây một lần, áp cho mọi phản hồi kể cả file tĩnh.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def log_message(self, fmt, *args):
        # Im lặng: log từng request làm rối, mà thông tin hữu ích đã in ở watcher.
        pass


def ip_noi_bo():
    """IP của máy trong mạng LAN. UDP connect không gửi gói nào ra ngoài."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    cong = 8787
    if len(sys.argv) > 1:
        try:
            cong = int(sys.argv[1])
        except ValueError:
            print("Cổng phải là số. Ví dụ: python tools/serve.py 9000")
            return 2

    print("Xuất lần đầu...")
    if not export.xuat():
        return 1

    threading.Thread(target=canh_gac, daemon=True).start()

    try:
        may_chu = ThreadingHTTPServer(
            ("0.0.0.0", cong), partial(Handler, directory=str(EXPORT)))
    except OSError as e:
        print("")
        print("Không mở được cổng %d: %s" % (cong, e))
        print("Cổng có thể đang bị chiếm. Thử cổng khác:")
        print("    python tools/serve.py %d" % (cong + 1))
        return 1

    ip = ip_noi_bo()
    print("")
    print("=" * 58)
    print("  Mở trên ĐIỆN THOẠI (cùng Wi-Fi):")
    print("      http://%s:%d" % (ip, cong))
    print("")
    print("  Mở trên máy này:")
    print("      http://127.0.0.1:%d" % cong)
    print("=" * 58)
    print("")
    print("Sửa file .md rồi lưu — trang trên điện thoại tự tải lại sau ~%ds."
          % (CHU_KY_HOI // 1000 + 1))
    print("Ctrl+C để dừng.")
    print("")

    try:
        may_chu.serve_forever()
    except KeyboardInterrupt:
        print("")
        print("Đã dừng.")
    finally:
        may_chu.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
