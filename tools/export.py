#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/export.py — xuất vault markdown ra MỘT file HTML duy nhất.

Vì sao tồn tại:
    Vault này để đọc lúc đang chơi, trên điện thoại, thường là không có mạng.
    Nên bản xuất phải là một file .html tự chứa: ảnh nhúng base64, không CDN,
    không font ngoài, mở bằng trình duyệt nào cũng chạy.

Nguyên tắc:
    - Markdown là BẢN GỐC. HTML là BẢN XUẤT. Không bao giờ sửa ngược lại.
    - Không đè lên _export/leiting_zhanji_wiki_v05.html (bản gốc lịch sử).
    - Không dùng thư viện ngoài. Chỉ stdlib.

Chạy:
    python tools/export.py

Kết quả:
    _export/wiki.html

Muốn xem trực tiếp trên điện thoại theo thời gian thực: xem tools/serve.py
"""
from __future__ import annotations

import base64
import hashlib
import html
import re
import sys
from pathlib import Path

# Console Windows mặc định cp1252, không in được Hán tự / tiếng Việt có dấu.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "_assets"
EXPORT = ROOT / "_export"
OUT = EXPORT / "wiki.html"

# Không bao giờ ghi đè những file này.
PROTECTED = {"leiting_zhanji_wiki_v05.html"}

# CLAUDE.md là hướng dẫn cho trợ lý, không phải nội dung wiki -> không xuất.
# Muốn xuất cả nó thì xoá khỏi tập hợp này.
EXCLUDE = {"CLAUDE.md"}

# Ghim lên đầu, trước các note đánh số.
PIN_FIRST = ["_CONTEXT.md"]

MIME = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
}

canh_bao: list[str] = []


# --------------------------------------------------------------------------
# frontmatter
# --------------------------------------------------------------------------
def tach_frontmatter(text):
    """Tách khối --- ... --- ở đầu file. Parser tối thiểu, đủ cho vault này."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, lines
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, lines
    meta = {}
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if ":" not in raw:
            continue
        key, _, val = raw.partition(":")
        key = key.strip()
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            items = [v.strip().strip("\"'") for v in val[1:-1].split(",")]
            meta[key] = [v for v in items if v]
        else:
            meta[key] = val.strip("\"'")
    return meta, lines[end + 1:]


# --------------------------------------------------------------------------
# ảnh
# --------------------------------------------------------------------------
_bo_nho_anh = {}


def data_uri(ten):
    if ten in _bo_nho_anh:
        return _bo_nho_anh[ten]
    duong_dan = ASSETS / ten
    if not duong_dan.is_file():
        # thử tìm không phân biệt hoa thường
        trung = None
        for p in ASSETS.glob("*"):
            if p.name.lower() == ten.lower():
                trung = p
                break
        if trung is None:
            return None
        duong_dan = trung
    mime = MIME.get(duong_dan.suffix.lower(), "application/octet-stream")
    uri = "data:%s;base64,%s" % (
        mime, base64.b64encode(duong_dan.read_bytes()).decode("ascii"))
    _bo_nho_anh[ten] = uri
    return uri


def nhung_anh(ten):
    ten = ten.split("|")[0].strip()
    uri = data_uri(ten)
    if uri is None:
        canh_bao.append(
            "Thiếu ảnh: _assets/%s được nhúng nhưng không tìm thấy file" % ten)
        return ('<span class="img-missing">chưa có ảnh: <code>%s</code></span>'
                % html.escape(ten))
    alt = html.escape(ten, quote=True)
    return ('<a class="shot" href="%s" target="_blank" rel="noopener">'
            '<img loading="lazy" alt="%s" title="%s" src="%s"></a>'
            % (uri, alt, alt, uri))


# --------------------------------------------------------------------------
# inline
# --------------------------------------------------------------------------
def inline(text, ctx):
    o = []

    def giu(frag):
        o.append(frag)
        return "\x00%d\x01" % (len(o) - 1)

    # ![[ảnh.jpg]] — phải xử lý trước [[...]]
    text = re.sub(r"!\[\[([^\]]+?)\]\]", lambda m: giu(nhung_anh(m.group(1))), text)
    # `code`
    text = re.sub(r"`([^`\n]+)`",
                  lambda m: giu("<code>%s</code>" % html.escape(m.group(1))), text)
    # [[note]] hoặc [[note|nhãn]]
    text = re.sub(r"\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]",
                  lambda m: giu(wikilink(m.group(1).strip(), m.group(2), ctx)), text)
    # [nhãn](url)
    text = re.sub(
        r"\[([^\]\n]+?)\]\(([^)\s]+)\)",
        lambda m: giu('<a href="%s" target="_blank" rel="noopener">%s</a>'
                      % (html.escape(m.group(2), quote=True),
                         html.escape(m.group(1)))),
        text)

    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<em>\1</em>", text)

    return re.sub(r"\x00(\d+)\x01", lambda m: o[int(m.group(1))], text)


def wikilink(dich, nhan, ctx):
    ten = dich.split("#")[0].strip()
    hien = html.escape(nhan.strip() if nhan else dich)
    neo = ctx["neo"].get(ten.lower())
    if neo:
        return '<a class="wl" href="#%s">%s</a>' % (neo, hien)
    # Chưa có note tương ứng — đánh dấu, đừng tạo link chết.
    canh_bao.append("Wikilink chưa có note: [[%s]]" % dich)
    return '<span class="wl-missing" title="chưa có note này">%s</span>' % hien


def bo_markup(text):
    """Bỏ markup, dùng làm khoá localStorage ổn định."""
    text = re.sub(r"!?\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]", r"\1", text)
    text = re.sub(r"\[([^\]]+?)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*`~#>]", "", text)
    return " ".join(text.split())


# --------------------------------------------------------------------------
# block
# --------------------------------------------------------------------------
HR_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
HEAD_RE = re.compile(r"^(#{1,6})\s+(.*)$")
LIST_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
CALLOUT_RE = re.compile(r"^>\s*\[!(\w+)\]([+-])?\s*(.*)$")
TASK_RE = re.compile(r"^\[([ xX])\]\s+(.*)$")

CALLOUT_ICON = {
    "note": "i", "info": "i", "tip": "*", "hint": "*", "todo": "o",
    "success": "v", "done": "v", "check": "v",
    "question": "?", "help": "?", "faq": "?",
    "warning": "!", "caution": "!", "attention": "!",
    "danger": "!!", "error": "!!", "bug": "!!", "failure": "x",
    "example": "e", "quote": "“", "abstract": "=", "summary": "=",
}


def la_vach_bang(line):
    s = line.strip()
    if "|" not in s or "-" not in s:
        return False
    o = [c.strip() for c in s.strip("|").split("|")]
    return bool(o) and all(re.fullmatch(r":?-{1,}:?", c) for c in o)


def tach_hang(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def khoi(lines, ctx, khoa):
    ra = []
    i, n = 0, len(lines)

    while i < n:
        line = lines[i]
        s = line.strip()

        if not s:
            i += 1
            continue

        # khối code
        if s.startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            ra.append('<pre class="code"><code>%s</code></pre>'
                      % html.escape("\n".join(buf)))
            continue

        # tiêu đề
        m = HEAD_RE.match(s)
        if m:
            cap = min(len(m.group(1)) + 1, 6)   # '#' trong note -> h2, '##' -> h3 ...
            ra.append('<h%d class="md-h">%s</h%d>'
                      % (cap, inline(m.group(2).strip(), ctx), cap))
            i += 1
            continue

        # đường kẻ
        if HR_RE.match(line):
            ra.append("<hr>")
            i += 1
            continue

        # bảng
        if "|" in s and i + 1 < n and la_vach_bang(lines[i + 1]):
            dau = tach_hang(lines[i])
            can = []
            for c in tach_hang(lines[i + 1]):
                if c.startswith(":") and c.endswith(":"):
                    can.append("center")
                elif c.endswith(":"):
                    can.append("right")
                else:
                    can.append("left")
            i += 2
            than = []
            while i < n and "|" in lines[i] and lines[i].strip():
                than.append(tach_hang(lines[i]))
                i += 1
            th = "".join('<th style="text-align:%s">%s</th>'
                         % (can[k] if k < len(can) else "left", inline(c, ctx))
                         for k, c in enumerate(dau))
            tr = []
            for hang in than:
                td = "".join('<td style="text-align:%s">%s</td>'
                             % (can[k] if k < len(can) else "left", inline(c, ctx))
                             for k, c in enumerate(hang))
                tr.append("<tr>%s</tr>" % td)
            ra.append('<div class="tablewrap"><table><thead><tr>%s</tr></thead>'
                      "<tbody>%s</tbody></table></div>" % (th, "".join(tr)))
            continue

        # callout Obsidian: > [!warning] Tiêu đề
        m = CALLOUT_RE.match(s)
        if m:
            loai = m.group(1).lower()
            tieu_de = m.group(3).strip()
            i += 1
            trong = []
            while i < n and lines[i].lstrip().startswith(">"):
                trong.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            dau = ('<div class="cal-head"><span class="cal-icon">%s</span><b>%s</b></div>'
                   % (html.escape(CALLOUT_ICON.get(loai, "i")),
                      inline(tieu_de, ctx) if tieu_de else html.escape(loai)))
            than = khoi(trong, ctx, khoa) if trong else ""
            ra.append('<div class="callout cal-%s">%s%s</div>'
                      % (html.escape(loai, quote=True), dau, than))
            continue

        # trích dẫn thường
        if s.startswith(">"):
            buf = []
            while i < n and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            ra.append("<blockquote>%s</blockquote>" % khoi(buf, ctx, khoa))
            continue

        # danh sách
        if LIST_RE.match(line):
            i, doan = doc_danh_sach(lines, i, ctx, khoa)
            ra.append(doan)
            continue

        # đoạn văn
        buf = []
        while i < n and lines[i].strip():
            cur = lines[i]
            if (HEAD_RE.match(cur.strip()) or HR_RE.match(cur) or LIST_RE.match(cur)
                    or cur.lstrip().startswith(">") or cur.strip().startswith("```")):
                break
            if "|" in cur and i + 1 < n and la_vach_bang(lines[i + 1]):
                break
            buf.append(cur.strip())
            i += 1
        if buf:
            ra.append("<p>%s</p>" % inline(" ".join(buf), ctx))

    return "".join(ra)


def doc_danh_sach(lines, i, ctx, khoa):
    muc = []
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            if i + 1 < n and LIST_RE.match(lines[i + 1]):
                i += 1
                continue
            break
        m = LIST_RE.match(line)
        if not m:
            # dòng nối tiếp của mục trước
            if muc and (line.startswith("  ") or line.startswith("\t")):
                muc[-1][2] += " " + line.strip()
                i += 1
                continue
            break
        muc.append([len(m.group(1).expandtabs(4)),
                    m.group(2) not in ("-", "*", "+"),
                    m.group(3)])
        i += 1

    doan = []
    ngan_xep = []
    for thut, co_so, noi_dung in muc:
        the = "ol" if co_so else "ul"
        while ngan_xep and thut < ngan_xep[-1][0]:
            doan.append("</li></%s>" % ngan_xep.pop()[1])
        if not ngan_xep or thut > ngan_xep[-1][0]:
            doan.append('<%s class="md-list">' % the)
            ngan_xep.append((thut, the))
        else:
            doan.append("</li>")
        doan.append("<li>%s" % dung_muc(noi_dung, ctx, khoa))
    while ngan_xep:
        doan.append("</li></%s>" % ngan_xep.pop()[1])
    return i, "".join(doan)


def dung_muc(noi_dung, ctx, khoa):
    m = TASK_RE.match(noi_dung.strip())
    if not m:
        return inline(noi_dung, ctx)
    xong = m.group(1).lower() == "x"
    chu = m.group(2)
    # Khoá bám theo NỘI DUNG chứ không theo vị trí
    # -> sắp xếp lại note không làm mất tích.
    ma = hashlib.sha1(bo_markup(chu).encode("utf-8")).hexdigest()[:10]
    return ('<label class="task"><input type="checkbox" data-save="%s/%s"%s>'
            "<span>%s</span></label>"
            % (html.escape(khoa, quote=True), ma,
               " checked" if xong else "", inline(chu, ctx)))


# --------------------------------------------------------------------------
# thu thập note
# --------------------------------------------------------------------------
def thu_thap():
    thay = {}
    for p in ROOT.glob("*.md"):
        if p.name not in EXCLUDE:
            thay[p.name] = p
    thu_tu = []
    for ten in PIN_FIRST:
        if ten in thay:
            thu_tu.append(thay.pop(ten))
    for k in sorted(thay):
        thu_tu.append(thay[k])
    return thu_tu


def tao_neo(ten_file):
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", ten_file).strip("-").lower()
    return "n-" + (s or "note")


# --------------------------------------------------------------------------
# CSS / JS — giữ tinh thần bản v0.5: nền tối, tìm kiếm lọc theo section,
# checkbox lưu bằng localStorage.
# --------------------------------------------------------------------------
CSS = """
:root{--bg:#050b14;--panel:#0b1a2d;--line:#1d4666;--cyan:#4ed5ff;--gold:#ffd765;
--green:#64e29a;--red:#ff6f7d;--purple:#b06cff;--text:#eef7ff;--muted:#9eb3c8;
--shadow:0 18px 50px rgba(0,0,0,.35)}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
/* overflow-x:hidden CHỈ đặt trên html. Đặt thêm trên body sẽ ép body thành
   overflow-y:auto -> body trở thành vùng cuộn -> thanh nav position:sticky
   hết dính. Tràn ngang đã được chặn bằng .tablewrap{overflow-x:auto} và
   overflow-wrap:anywhere bên dưới. */
html{max-width:100%;overflow-x:hidden}
body{max-width:100%}
/* Không dùng background-attachment:fixed — iOS Safari render sai trên trang dài,
   mà trang này chính là để đọc trên điện thoại. Quầng sáng chỉ ở phần đầu trang. */
html{background:#040910}
body{margin:0;color:var(--text);background-color:#040910;
 background-image:radial-gradient(1100px 560px at 8% -4%,#173b6966,transparent 62%),
 radial-gradient(900px 480px at 100% 4%,#291a5566,transparent 62%),
 linear-gradient(180deg,#050b14 0,#07101d 900px,#040910 1800px);
 background-repeat:no-repeat;
 font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Noto Sans",Arial,sans-serif}
a{color:var(--cyan);text-decoration:none}
a:hover{text-decoration:underline}
img{display:block;max-width:100%}
button,input{font:inherit}
.wrap{width:min(1180px,100%);margin:auto;padding:0 16px 64px}

.hero{padding:40px 0 18px}
.eyebrow{display:inline-flex;gap:8px;align-items:center;padding:7px 10px;
 border:1px solid #2c6289;border-radius:999px;background:#0b2137aa;color:#bfefff;
 font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase}
h1{font-size:clamp(28px,5vw,50px);line-height:1.06;margin:14px 0 10px;letter-spacing:-.035em}
.hero p{color:var(--muted);max-width:820px;margin:0;font-size:clamp(14px,2.4vw,17px)}
.stamps{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
.stamps span{padding:6px 10px;border-radius:999px;background:#0b2035;border:1px solid #214865;
 color:#bfe7ff;font-size:11px;font-weight:700}

.sticky{position:sticky;top:0;z-index:30;background:rgba(4,10,18,.86);
 backdrop-filter:blur(16px);border-top:1px solid #ffffff0b;border-bottom:1px solid #ffffff12;
 margin:0 -16px;padding:10px 16px}
.nav{display:flex;gap:8px;overflow:auto;scrollbar-width:none}
.nav::-webkit-scrollbar{display:none}
.nav a{white-space:nowrap;padding:8px 11px;border-radius:10px;background:#0d2035;
 color:#d9eeff;border:1px solid #173a5a;font-weight:700;font-size:13px}
.nav a:hover{background:#12304e;text-decoration:none}
.toolbar{display:grid;grid-template-columns:1fr auto;gap:10px;margin:16px 0 0}
.search{width:100%;padding:12px 14px;border-radius:12px;border:1px solid #214865;
 background:#061524;color:#fff;outline:none}
.search:focus{border-color:var(--cyan);box-shadow:0 0 0 3px #4ed5ff1b}
.status{padding:12px 14px;border-radius:12px;background:#0d2035;border:1px solid #214865;
 color:#bfe7ff;font-size:13px;white-space:nowrap;align-self:center}
.noresult{display:none;margin:26px 0;padding:18px;border:1px dashed #3b637d;border-radius:16px;
 color:var(--muted);text-align:center}

section{scroll-margin-top:74px;margin:26px 0}
.card{background:linear-gradient(180deg,rgba(14,34,58,.96),rgba(7,18,31,.96));
 border:1px solid var(--line);border-radius:20px;box-shadow:var(--shadow);
 padding:18px 20px;overflow:hidden;min-width:0}
.sec-head{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;
 flex-wrap:wrap;margin-bottom:6px}
.sec-head h2{margin:0;font-size:clamp(21px,3.4vw,31px);letter-spacing:-.02em}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.chip{padding:5px 9px;border-radius:999px;border:1px solid #2b5d83;background:#0b2035;
 color:#cbeaff;font-size:11px;font-weight:800}
.chip.date{border-color:#246b49;color:#9ef0bd;background:#0b281b}
.chip.bad{border-color:#8b3b49;color:#ffb1ba;background:#2c1015}

.card h2.md-h{font-size:20px;margin:22px 0 8px;padding-top:14px;
 border-top:1px solid #ffffff12;color:#fff}
.card h3.md-h{font-size:17px;margin:18px 0 6px;color:#ffe28a}
.card h4.md-h,.card h5.md-h,.card h6.md-h{font-size:15px;margin:14px 0 5px;color:#bfe7ff}
p{margin:9px 0}
hr{border:0;border-top:1px solid #ffffff14;margin:18px 0}
code{background:#071522;border:1px solid #173a55;border-radius:6px;padding:1px 4px;
 font-size:.9em;font-family:ui-monospace,Consolas,"Courier New",monospace}
pre.code{background:#071522;border:1px solid #173a55;border-radius:12px;padding:12px;
 overflow:auto;margin:12px 0}
pre.code code{background:0;border:0;padding:0}
blockquote{margin:12px 0;padding:2px 14px;border-left:3px solid #2b5d83;color:#b9cce0}

.md-list{margin:9px 0;padding-left:22px}
.md-list li{margin:5px 0}
.md-list .md-list{margin:5px 0}
ul.md-list{list-style:none;padding-left:16px}
ul.md-list>li{position:relative;padding-left:14px}
ul.md-list>li:before{content:"";position:absolute;left:0;top:.62em;width:6px;height:6px;
 border-radius:50%;background:#3c7fae}
ul.md-list>li:has(>.task):before{display:none}
ul.md-list>li:has(>.task){padding-left:0}

.task{display:flex;gap:9px;align-items:flex-start;padding:8px 10px;border-radius:11px;
 background:#071522;border:1px solid #24465d;cursor:pointer}
.task input{accent-color:#3fd6ff;margin:2px 0 0;flex:0 0 auto;width:16px;height:16px}
.task input:checked+span{color:#7f9bb0;text-decoration:line-through}

.tablewrap{overflow-x:auto;margin:12px 0;border:1px solid var(--line);border-radius:14px}
table{border-collapse:collapse;width:100%;min-width:min(560px,100%);font-size:13.5px}
th,td{padding:9px 11px;border-bottom:1px solid #ffffff10;vertical-align:top}
th{background:#0d2440;color:#eaf7ff;font-weight:800;white-space:nowrap}
tbody tr:nth-child(even){background:#ffffff05}
tbody tr:last-child td{border-bottom:0}
td .shot{margin-top:6px}

.callout{margin:14px 0;padding:12px 14px;border-radius:14px;border:1px solid #2d5e82;
 border-left:4px solid var(--cyan);background:#0e2540}
.callout .cal-head{display:flex;gap:9px;align-items:center;margin-bottom:4px;color:#fff}
.callout .cal-icon{display:grid;place-items:center;width:22px;height:22px;border-radius:7px;
 background:#173b61;color:var(--cyan);font-weight:900;font-size:12px;flex:0 0 auto}
.callout p{margin:4px 0;color:#bad0e4}
.cal-warning,.cal-caution,.cal-attention,.cal-todo{border-left-color:var(--gold);
 background:#271e0a}
.cal-warning .cal-icon,.cal-caution .cal-icon,.cal-attention .cal-icon,
.cal-todo .cal-icon{background:#3d2f0c;color:var(--gold)}
.cal-warning p,.cal-caution p,.cal-attention p,.cal-todo p{color:#ffe5a5}
.cal-danger,.cal-error,.cal-bug,.cal-failure{border-left-color:var(--red);background:#291015}
.cal-danger .cal-icon,.cal-error .cal-icon,.cal-bug .cal-icon,
.cal-failure .cal-icon{background:#43151d;color:var(--red)}
.cal-danger p,.cal-error p,.cal-bug p,.cal-failure p{color:#ffc5cc}
.cal-tip,.cal-hint,.cal-success,.cal-done,.cal-check{border-left-color:var(--green);
 background:#0b221b}
.cal-tip .cal-icon,.cal-hint .cal-icon,.cal-success .cal-icon,.cal-done .cal-icon,
.cal-check .cal-icon{background:#0d3325;color:var(--green)}
.cal-tip p,.cal-hint p,.cal-success p,.cal-done p,.cal-check p{color:#c7f2d6}

.shot{display:inline-block;border-radius:12px;overflow:hidden;border:1px solid #6f3fa4;
 background:#140c20;box-shadow:0 0 26px #7a46bd22;max-width:220px}
.shot img{width:100%;height:auto}
.img-missing{display:inline-block;padding:4px 8px;border:1px dashed #3b637d;border-radius:9px;
 color:var(--muted);font-size:12px}
.wl{border-bottom:1px dotted #4ed5ff66}
.wl-missing{color:#c08fb5;border-bottom:1px dotted #c08fb566;cursor:help}

.card,.tablewrap,.callout,p,td,th,li{overflow-wrap:anywhere;word-break:break-word}
.hidden-by-search{display:none!important}
footer{margin-top:34px;padding-top:18px;border-top:1px solid #ffffff12;color:#829db2;
 font-size:12px}
footer b{color:#bfe7ff}

@media(max-width:780px){
 .wrap{padding:0 12px 44px}
 .sticky{margin:0 -12px;padding:9px 12px}
 .toolbar{grid-template-columns:1fr}
 .status{white-space:normal;text-align:center}
 .card{padding:14px;border-radius:16px}
 .shot{max-width:150px}
 table{font-size:13px}
 th,td{padding:8px}
}
@media(max-width:430px){
 .hero{padding-top:28px}
 .shot{max-width:120px}
 .sec-head h2{font-size:20px}
}
@media print{
 .sticky,.toolbar,footer{display:none}
 body{background:#fff;color:#000}
 .card{border-color:#ccc;box-shadow:none;background:#fff}
}
"""

JS = """
(function(){
 var q=document.getElementById('search');
 var status=document.getElementById('status');
 var none=document.getElementById('noresult');
 var secs=Array.prototype.slice.call(document.querySelectorAll('section'));
 var base=status?status.textContent:'';

 function loc(){
  var s=q.value.trim().toLowerCase();
  var hit=0;
  secs.forEach(function(sec){
   if(!s){sec.classList.remove('hidden-by-search');hit++;return;}
   var hay=(sec.innerText+' '+(sec.dataset.search||'')).toLowerCase();
   var ok=hay.indexOf(s)>=0;
   sec.classList.toggle('hidden-by-search',!ok);
   if(ok)hit++;
  });
  if(none)none.style.display=(s&&hit===0)?'block':'none';
  if(status)status.textContent=s?(hit+'/'+secs.length+' mục'):base;
 }
 if(q){q.addEventListener('input',loc);}

 // Checkbox lưu bằng localStorage. Khoá bám theo nội dung dòng,
 // nên sắp xếp lại note không làm mất tích.
 document.querySelectorAll('[data-save]').forEach(function(el){
  var k='ltwiki:'+el.dataset.save;
  try{
   var v=localStorage.getItem(k);
   if(v!==null)el.checked=(v==='1');
  }catch(e){}
  el.addEventListener('change',function(){
   try{localStorage.setItem(k,el.checked?'1':'0');}catch(e){}
  });
 });
})();
"""

TRANG = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#07111f">
<meta name="robots" content="noindex, nofollow">
<title>__TITLE__</title>
<style>__CSS__</style>
</head>
<body>
<div class="wrap">
<header class="hero" id="top">
<div class="eyebrow">__EYEBROW__</div>
<h1>Wiki trang bị</h1>
<p>Bản xuất offline từ vault markdown. Ảnh nhúng sẵn trong file, mở trên điện thoại không cần mạng. Ô tìm kiếm lọc theo mục; các ô tích được lưu lại trong trình duyệt.</p>
<div class="stamps">__STAMPS__</div>
</header>
<div class="sticky"><nav class="nav">__NAV__</nav></div>
<div class="toolbar">
<input id="search" class="search" type="search" autocomplete="off"
 aria-label="Tìm trong wiki"
 placeholder="Tìm: 永世决意, 巡航导弹, Liya, farm, tier...">
<div id="status" class="status">__COUNT__ mục</div>
</div>
<div id="noresult" class="noresult">Không có mục nào khớp. Đây là <b>chưa tìm thấy trong vault</b>, không phải <b>không tồn tại trong game</b>.</div>
__BODY__
<footer>
<p>Bản gốc là markdown trong vault. File này là <b>bản xuất</b> — sửa markdown rồi chạy <code>python tools/export.py</code>, đừng sửa thẳng vào đây.</p>
<p>Quy ước: tên Hán tự giữ nguyên, mọi con số phải có nguồn và ngày, "chưa tìm thấy" khác "không tồn tại".</p>
</footer>
</div>
<script>__JS__</script>
</body>
</html>
"""


# --------------------------------------------------------------------------
# dựng trang
# --------------------------------------------------------------------------
def dung_trang():
    """Dựng nội dung HTML, trả về (chuỗi html, số note). Không ghi ra đĩa."""
    canh_bao.clear()
    _bo_nho_anh.clear()

    files = thu_thap()
    if not files:
        return None, 0

    ctx = {"neo": {}}
    for p in files:
        ctx["neo"][p.stem.lower()] = tao_neo(p.stem)

    notes = []
    for path in files:
        meta, than = tach_frontmatter(path.read_text(encoding="utf-8"))
        tieu_de = None
        for k, ln in enumerate(than):
            if ln.strip().startswith("# "):
                tieu_de = ln.strip()[2:].strip()
                than = than[:k] + than[k + 1:]
                break
        if not tieu_de:
            bi_danh = meta.get("aliases")
            tieu_de = (bi_danh[0] if isinstance(bi_danh, list) and bi_danh
                       else path.stem)
        notes.append((path, meta, tieu_de, than))

    ctx_meta = {}
    for path, meta, tieu_de, than in notes:
        if path.name == "_CONTEXT.md":
            ctx_meta = meta
            break

    phan = []
    nav = []

    for path, meta, tieu_de, than in notes:
        neo = tao_neo(path.stem)
        khoa = path.stem
        nav.append('<a href="#%s">%s</a>' % (neo, html.escape(tieu_de)))

        # Chỉ hiện chip mang thông tin: ngày kiểm tra và cảnh báo độ tin cậy.
        # Chip tag đã bỏ — nó chỉ lặp lại tên mục (#context, #slot, #tier...).
        # Tag vẫn tìm kiếm được vì nằm trong data-search.
        chip = []
        kt = meta.get("kiem-tra") or meta.get("kiem-tra-lan-cuoi")
        if kt:
            chip.append('<span class="chip date">kiểm tra: %s</span>'
                        % html.escape(str(kt)))
        else:
            chip.append('<span class="chip bad">thiếu ngày kiểm tra</span>')
            canh_bao.append("Thiếu `kiem-tra` trong frontmatter: %s" % path.name)
        dtc = meta.get("do-tin-cay")
        if dtc:
            chip.append('<span class="chip bad">%s</span>' % html.escape(str(dtc)))

        tim = [path.stem, tieu_de]
        bi_danh = meta.get("aliases")
        if isinstance(bi_danh, list):
            tim.extend(bi_danh)
        the = meta.get("tags")
        if isinstance(the, list):
            tim.extend(the)
            tim.extend("#" + t for t in the)

        phan.append(
            '<section id="%s" data-search="%s"><div class="card">'
            '<div class="sec-head"><h2>%s</h2><div class="chips">%s</div></div>'
            "%s</div></section>"
            % (neo,
               html.escape(" ".join(tim), quote=True),
               html.escape(tieu_de),
               "".join(chip),
               khoi(than, ctx, khoa))
        )

    moc = []
    if ctx_meta.get("ban-game"):
        moc.append("<span>bản game: %s</span>"
                   % html.escape(str(ctx_meta["ban-game"])))
    if ctx_meta.get("kiem-tra-lan-cuoi"):
        moc.append("<span>kiểm tra lần cuối: %s</span>"
                   % html.escape(str(ctx_meta["kiem-tra-lan-cuoi"])))
    moc.append("<span>%d ghi chú &middot; %d ảnh nhúng</span>"
               % (len(notes), len(_bo_nho_anh)))

    doc = (TRANG
           .replace("__TITLE__", "Wiki 雷霆战机：集结 — trang bị, pilot, tier")
           .replace("__EYEBROW__",
                    "雷霆战机：集结〔Lôi Đình Chiến Cơ: Tập Kết〕 &middot; vault cá nhân")
           .replace("__CSS__", CSS)
           .replace("__STAMPS__", "".join(moc))
           .replace("__NAV__", "".join(nav))
           .replace("__COUNT__", str(len(notes)))
           .replace("__BODY__", "".join(phan))
           .replace("__JS__", JS))

    return doc, len(notes)


def xuat(im_lang=False):
    """Dựng và ghi ra _export/wiki.html. Trả về số ký tự đã ghi, 0 nếu hỏng."""
    if OUT.name in PROTECTED:
        print("Từ chối: %s nằm trong danh sách không được ghi đè." % OUT.name)
        return 0
    EXPORT.mkdir(exist_ok=True)

    doc, so_note = dung_trang()
    if doc is None:
        print("Không tìm thấy file .md nào ở gốc vault.")
        return 0

    OUT.write_text(doc, encoding="utf-8")

    if not im_lang:
        print("Đã xuất: %s" % OUT)
        print("  %d ghi chú, %d ảnh nhúng, %.0f KB"
              % (so_note, len(_bo_nho_anh), len(doc.encode("utf-8")) / 1024))
    if canh_bao:
        print("")
        print("Cảnh báo (%d):" % len(canh_bao))
        for w in dict.fromkeys(canh_bao):
            print("  ! %s" % w)
    elif not im_lang:
        print("")
        print("Không có cảnh báo.")
    return len(doc)


def main():
    return 0 if xuat() else 1


if __name__ == "__main__":
    sys.exit(main())
