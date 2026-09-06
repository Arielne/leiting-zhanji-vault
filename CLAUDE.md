# CLAUDE.md — Vault 雷霆战机：集结

Đây là vault ghi chú cá nhân về game 雷霆战机：集结 (Lôi Đình Chiến Cơ: Tập Kết), server Trung Quốc.
Không phải wiki công khai. Mục tiêu duy nhất: **giúp chủ vault ra quyết định nuôi trang bị cho đúng tài khoản của mình.**

Đọc `_CONTEXT.md` trước khi làm bất cứ việc gì.

---

## PHASE 0 — Thiết lập lần đầu

Chạy phần này **một lần duy nhất**, ở lần đầu Claude Code được gọi trong thư mục này.
Sau khi xong, thêm dòng `> [!done] Phase 0 hoàn tất — <ngày>` vào cuối mục này rồi bỏ qua ở các lần sau.

### 0.1 Vault đang nằm sai chỗ

Vault được giải nén tạm ở thư mục Downloads. **Không để nó ở đó.** Windows dọn Downloads, và không ai backup thư mục Downloads.

Chuyển sang một chỗ cố định. Thứ tự ưu tiên:

1. Nếu máy đã có vault Obsidian sẵn (xem 0.2) → chuyển vào làm thư mục con của vault đó.
2. Nếu chưa có → tạo `%USERPROFILE%\Obsidian\LeitingZhanji\`.

Dùng PowerShell, đường dẫn có dấu cách phải bọc ngoặc kép. Sau khi chuyển, xác nhận lại với người dùng đường dẫn mới trước khi làm tiếp.

### 0.2 Kiểm tra Obsidian

Máy có thể chưa cài Obsidian. Kiểm tra theo thứ tự:

```powershell
Test-Path "$env:LOCALAPPDATA\Obsidian\Obsidian.exe"
winget list --id Obsidian.Obsidian
```

Nếu đã có, tìm xem đã có vault nào chưa — Obsidian lưu danh sách vault ở:

```
%APPDATA%\obsidian\obsidian.json
```

Đọc file đó, liệt kê đường dẫn các vault hiện có, báo cho người dùng chọn: nhập vault này vào một vault sẵn có, hay để riêng.

**Nếu chưa cài:** đề xuất `winget install --id Obsidian.Obsidian -e`, nhưng **hỏi trước khi chạy**. Không tự cài phần mềm.

Nếu người dùng không muốn cài Obsidian: vault này vẫn là markdown thuần, mở bằng VS Code hoặc bất cứ editor nào cũng đọc được. Chỉ mất phần hiển thị ảnh `![[...]]`, callout, và backlink. Nói rõ điều đó thay vì ép cài.

### 0.3 Git

```powershell
git init
git add -A
git commit -m "vault ban dau tu file HTML v0.5"
```

Vault gần như toàn text, git cho thấy đúng dòng nào đổi giữa các bản game. Đây là thứ có giá trị nhất khi cần truy lại "hồi đó tôi ghi thế này là dựa vào đâu".

Tạo `.gitignore`:

```
.obsidian/workspace.json
.obsidian/workspace-mobile.json
_inbox/
```

### 0.4 Tạo thư mục làm việc

```
_inbox/     ← chỗ ném screenshot mới chụp, chưa xử lý
```

### 0.5 Viết script xuất HTML

Tạo `tools/export.py`. Yêu cầu:

- Đọc toàn bộ `*.md` ở gốc vault theo thứ tự tên file (00, 01, 02...)
- Chuyển sang HTML một file duy nhất, **nhúng ảnh dạng base64** để xem offline trên điện thoại không cần mạng
- Giữ nguyên tinh thần bản `_export/leiting_zhanji_wiki_v05.html`: nền tối, có ô tìm kiếm lọc theo section, checkbox lưu bằng `localStorage`
- Ghi ra `_export/wiki.html`, **không đè lên file v0.5 cũ**
- Không dùng thư viện ngoài nếu tránh được; nếu cần thì `markdown` là đủ

Chạy thử một lần, mở file kết quả xác nhận ảnh hiện đúng, rồi báo lại.

> [!done] Phase 0 hoàn tất — 2026-09-07
> Vault ở `C:\Users\pc\Downloads\Obsi\Obsidian` (chủ vault chọn, ghi đè ưu tiên trong 0.1 — path này đã có sẵn trong `obsidian.json` nên Obsidian tự nhận).
> Obsidian đã cài sẵn 1.12.7 tại `%LOCALAPPDATA%\Programs\Obsidian`. Git khởi tạo. `_inbox/` và `tools/export.py` đã tạo và chạy thử.

---

## Cấu trúc vault

```
_CONTEXT.md            quy ước + trạng thái tài khoản + bản đồ vault
00-lo-trinh.md         4 bước đang theo
01-build-hien-tai.md   bảng build kèm ảnh thật
02-tier-chien-than.md  bảng tier cộng đồng
03-pilot.md            thứ tự nuôi phi công
04-chien-co.md         战神机体
05-giap.md             战神装甲
06-vu-khi-phu.md       战神副武器
07-lieu-co.md          战神僚机
08-farm-boss.md        checklist ưu tiên cày
09-nguon.md            nguồn kiểm chứng + việc cần làm
10-nhat-ky.md          log quyết định
_assets/               ảnh, đánh số theo thứ tự
_export/               bản HTML xuất ra — CHỈ ĐỌC
_inbox/                screenshot chưa xử lý
tools/export.py        script xuất HTML
tools/serve.py         xem trên điện thoại theo thời gian thực (cùng Wi-Fi)
```

Xem trên điện thoại:

```powershell
python tools\serve.py
```

Mở URL nó in ra trên điện thoại (cùng Wi-Fi). Sửa markdown, lưu, trang tự tải lại.
Không cần cài gì trên điện thoại. Ctrl+C để dừng.

---

## Quy ước bắt buộc

### 1. Mỗi note phải có `kiem-tra` trong frontmatter

```yaml
---
kiem-tra: 2026-09-07
---
```

Game này có tiền lệ nerf âm thầm không thông báo (rương vô tận giới hạn 20, nâng phi công 10 → 5 lần/ngày). Note không có mốc thời gian là note sai đang chờ ngày phát nổ.

**Sửa nội dung note nào thì cập nhật `kiem-tra` của note đó.** Không cập nhật hàng loạt cho những note không đụng tới.

### 2. Phân biệt "chưa tìm thấy" và "không tồn tại"

Đây là luật quan trọng nhất trong vault này.

Trước khi viết "không có", "thiếu", "sai", phải trả lời được: đã tìm ở đâu? Nếu chưa tìm hết thì viết **`chưa xác minh`**, kèm dòng ghi rõ đã tìm ở những nguồn nào.

Ví dụ đúng:
> `chưa xác minh` — đã tìm ở TapTap 新手开荒指南 và 整体攻略, không thấy nhắc tới món này.

Ví dụ sai:
> Món này không có trong game.

### 3. Mọi con số mới phải kèm nguồn và ngày

Không được ghi tier, chỉ số, công thức ghép vào note mà không có link nguồn. Sáu tháng sau chủ vault phải phân biệt được đâu là thứ tự mình kiểm chứng trong game, đâu là thứ đọc từ guide người khác.

Nguồn chia hai nhóm, đã ghi trong `09-nguon.md`:
- **Hiện hành** (TapTap 2025–2026): dùng cho tier và khuyến nghị
- **Legacy** (18183, 4399): CHỈ dùng xác nhận công thức ghép và cơ chế cơ bản. Cấm lấy tier từ đây.

### 4. Tên riêng giữ nguyên tiếng Trung

Trong game chỉ có tiếng Trung. Luôn viết `强袭斗士〔Đấu Sĩ Cường Kích〕` — Hán tự trước, nghĩa Việt trong 〔...〕. Ghi chú thuần tiếng Việt thì lúc đang chơi không đối chiếu được.

### 5. Ảnh

- Chỉ dùng screenshot thật từ game hoặc ảnh từ nguồn TapTap. **Không dùng ảnh do AI sinh.**
- Đặt trong `_assets/`, tên dạng `<số thứ tự>-<slug-không-dấu>.jpg`, tiếp nối số hiện có
- Nhúng bằng `![[tên-file.jpg]]`

### 6. `_export/` chỉ đọc

File HTML là **bản xuất**, markdown là **bản gốc**. Sửa markdown rồi chạy `tools/export.py`. Không bao giờ sửa thẳng vào HTML — hai bên lệch nhau thì sáu tháng sau không ai biết bên nào đúng.

`_export/leiting_zhanji_wiki_v05.html` là bản gốc lịch sử, giữ nguyên vĩnh viễn, không đè.

---

## Quy trình thường gặp

### Cập nhật build từ screenshot mới

1. Đọc ảnh trong `_inbox/`
2. Cập nhật bảng trong `01-build-hien-tai.md` và bảng trạng thái trong `_CONTEXT.md`
3. Nếu cấp trang bị đổi làm lộ trình thay đổi → cập nhật `00-lo-trinh.md`
4. Đổi tên ảnh theo quy ước, chuyển sang `_assets/`
5. Ghi một mục vào `10-nhat-ky.md`: **quyết định gì và vì sao**, không chép lại số liệu
6. Cập nhật `kiem-tra` các note đã sửa
7. Chạy `tools/export.py`
8. `git commit`

### Cập nhật tier sau bản game mới

Đọc lại các bài guide trong `09-nguon.md`. Nếu thứ hạng đổi, ghi **cả bản cũ lẫn bản mới** kèm ngày, đừng xoá trắng bản cũ — chủ vault cần thấy meta dịch chuyển thế nào.

### Việc còn treo

Xem cuối `09-nguon.md`. Hiện có: đối chiếu số hiệu phiên bản game (file HTML ghi 1.27.30, TapTap all-info ngày 07/09/2026 ghi 1.25.31), và tìm ảnh xác minh cho các món T0/T1 đang trống trong `02-tier-chien-than.md`.

---

## Không được làm

- Không tự cài phần mềm. Đề xuất lệnh, hỏi, chờ đồng ý.
- Không sửa file trong `_export/`.
- Không viết số liệu không nguồn.
- Không viết "không tồn tại" khi thực tế là "chưa tìm thấy".
- Không đổi cấu trúc thư mục hay đánh số lại file mà không hỏi.
- Không xoá ảnh trong `_assets/` kể cả khi thấy trùng. Ảnh `19-quyet-y-vinh-the.jpg` trùng với `16` là cố ý giữ.
- Không dịch tên Hán tự thành tiếng Việt rồi bỏ bản gốc.
