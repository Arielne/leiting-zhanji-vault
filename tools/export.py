#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/export.py — xuat vault markdown ra MOT file HTML duy nhat.

Vi sao ton tai:
    Vault nay de doc luc dang choi, tren dien thoai, thuong la khong co mang.
    Nen ban xuat phai la mot file .html tu chua: anh nhung base64, khong CDN,
    khong font ngoai, mo bang trinh duyet nao cung chay.

Nguyen tac:
    - Markdown la BAN GOC. HTML la BAN XUAT. Khong bao gio sua nguoc lai.
    - Khong de len _export/leiting_zhanji_wiki_v05.html (ban goc lich su).
    - Khong dung thu vien ngoai. Chi stdlib.

Chay:
    python tools/export.py

Ket qua:
    _export/wiki.html
"""
from __future__ import annotations

import base64
import hashlib
import html
import re
import sys
from pathlib import Path

# Console Windows mac dinh cp1252, khong in duoc Han tu / tieng Viet co dau.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "_assets"
EXPORT = ROOT / "_export"
OUT = EXPORT / "wiki.html"

# Khong bao gio ghi de nhung file nay.
PROTECTED = {"leiting_zhanji_wiki_v05.html"}

# CLAUDE.md la huong dan cho tro ly, khong phai noi dung wiki -> khong xuat.
# Muon xuat ca no thi xoa khoi tap hop nay.
EXCLUDE = {"CLAUDE.md"}

# Ghim len dau, truoc cac note danh so.
PIN_FIRST = ["_CONTEXT.md"]

MIME = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
}

warnings: list[str] = []


# --------------------------------------------------------------------------
# frontmatter
# --------------------------------------------------------------------------
def split_frontmatter(text):
    """Tach khoi --- ... --- o dau file. Parser toi thieu, du cho vault nay."""
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
# anh
# --------------------------------------------------------------------------
_img_cache = {}


def data_uri(name):
    if name in _img_cache:
        return _img_cache[name]
    path = ASSETS / name
    if not path.is_file():
        # thu tim khong phan biet hoa thuong
        hit = None
        for p in ASSETS.glob("*"):
            if p.name.lower() == name.lower():
                hit = p
                break
        if hit is None:
            return None
        path = hit
    mime = MIME.get(path.suffix.lower(), "application/octet-stream")
    uri = "data:%s;base64,%s" % (mime, base64.b64encode(path.read_bytes()).decode("ascii"))
    _img_cache[name] = uri
    return uri


def embed_image(name):
    name = name.split("|")[0].strip()
    uri = data_uri(name)
    if uri is None:
        warnings.append("THIEU ANH: _assets/%s duoc nhung nhung khong tim thay file" % name)
        return ('<span class="img-missing">chua co anh: <code>%s</code></span>'
                % html.escape(name))
    alt = html.escape(name, quote=True)
    return ('<a class="shot" href="%s" target="_blank" rel="noopener">'
            '<img loading="lazy" alt="%s" title="%s" src="%s"></a>'
            % (uri, alt, alt, uri))


# --------------------------------------------------------------------------
# inline
# --------------------------------------------------------------------------
def inline(text, ctx):
    slots = []

    def keep(frag):
        slots.append(frag)
        return "\x00%d\x01" % (len(slots) - 1)

    # ![[anh.jpg]] — phai xu ly truoc [[...]]
    text = re.sub(r"!\[\[([^\]]+?)\]\]", lambda m: keep(embed_image(m.group(1))), text)
    # `code`
    text = re.sub(r"`([^`\n]+)`",
                  lambda m: keep("<code>%s</code>" % html.escape(m.group(1))), text)
    # [[note]] hoac [[note|nhan]]
    text = re.sub(r"\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]",
                  lambda m: keep(wikilink(m.group(1).strip(), m.group(2), ctx)), text)
    # [nhan](url)
    text = re.sub(
        r"\[([^\]\n]+?)\]\(([^)\s]+)\)",
        lambda m: keep('<a href="%s" target="_blank" rel="noopener">%s</a>'
                       % (html.escape(m.group(2), quote=True), html.escape(m.group(1)))),
        text)

    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<em>\1</em>", text)

    return re.sub(r"\x00(\d+)\x01", lambda m: slots[int(m.group(1))], text)


def wikilink(target, label, ctx):
    stem = target.split("#")[0].strip()
    shown = html.escape(label.strip() if label else target)
    anchor = ctx["anchors"].get(stem.lower())
    if anchor:
        return '<a class="wl" href="#%s">%s</a>' % (anchor, shown)
    # Chua co note tuong ung — danh dau, dung tao link chet.
    warnings.append("WIKILINK CHUA CO NOTE: [[%s]]" % target)
    return '<span class="wl-missing" title="chua co note nay">%s</span>' % shown


def plain(text):
    """Bo markup, dung lam khoa localStorage on dinh."""
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


def is_table_sep(line):
    s = line.strip()
    if "|" not in s or "-" not in s:
        return False
    cells = [c.strip() for c in s.strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{1,}:?", c) for c in cells)


def split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def blocks(lines, ctx, key):
    out = []
    i, n = 0, len(lines)

    while i < n:
        line = lines[i]
        s = line.strip()

        if not s:
            i += 1
            continue

        # khoi code
        if s.startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append('<pre class="code"><code>%s</code></pre>'
                       % html.escape("\n".join(buf)))
            continue

        # tieu de
        m = HEAD_RE.match(s)
        if m:
            lvl = min(len(m.group(1)) + 1, 6)   # '#' trong note -> h2, '##' -> h3 ...
            out.append('<h%d class="md-h">%s</h%d>'
                       % (lvl, inline(m.group(2).strip(), ctx), lvl))
            i += 1
            continue

        # duong ke
        if HR_RE.match(line):
            out.append("<hr>")
            i += 1
            continue

        # bang
        if "|" in s and i + 1 < n and is_table_sep(lines[i + 1]):
            head = split_row(lines[i])
            aligns = []
            for c in split_row(lines[i + 1]):
                if c.startswith(":") and c.endswith(":"):
                    aligns.append("center")
                elif c.endswith(":"):
                    aligns.append("right")
                else:
                    aligns.append("left")
            i += 2
            body = []
            while i < n and "|" in lines[i] and lines[i].strip():
                body.append(split_row(lines[i]))
                i += 1
            th = "".join('<th style="text-align:%s">%s</th>'
                         % (aligns[k] if k < len(aligns) else "left", inline(c, ctx))
                         for k, c in enumerate(head))
            trs = []
            for row in body:
                tds = "".join('<td style="text-align:%s">%s</td>'
                              % (aligns[k] if k < len(aligns) else "left", inline(c, ctx))
                              for k, c in enumerate(row))
                trs.append("<tr>%s</tr>" % tds)
            out.append('<div class="tablewrap"><table><thead><tr>%s</tr></thead>'
                       "<tbody>%s</tbody></table></div>" % (th, "".join(trs)))
            continue

        # callout Obsidian: > [!warning] Tieu de
        m = CALLOUT_RE.match(s)
        if m:
            kind = m.group(1).lower()
            title = m.group(3).strip()
            i += 1
            inner_lines = []
            while i < n and lines[i].lstrip().startswith(">"):
                inner_lines.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            head = ('<div class="cal-head"><span class="cal-icon">%s</span><b>%s</b></div>'
                    % (html.escape(CALLOUT_ICON.get(kind, "i")),
                       inline(title, ctx) if title else html.escape(kind)))
            body_html = blocks(inner_lines, ctx, key) if inner_lines else ""
            out.append('<div class="callout cal-%s">%s%s</div>'
                       % (html.escape(kind, quote=True), head, body_html))
            continue

        # trich dan thuong
        if s.startswith(">"):
            buf = []
            while i < n and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append("<blockquote>%s</blockquote>" % blocks(buf, ctx, key))
            continue

        # danh sach
        if LIST_RE.match(line):
            i, frag = parse_list(lines, i, ctx, key)
            out.append(frag)
            continue

        # doan van
        buf = []
        while i < n and lines[i].strip():
            cur = lines[i]
            if (HEAD_RE.match(cur.strip()) or HR_RE.match(cur) or LIST_RE.match(cur)
                    or cur.lstrip().startswith(">") or cur.strip().startswith("```")):
                break
            if "|" in cur and i + 1 < n and is_table_sep(lines[i + 1]):
                break
            buf.append(cur.strip())
            i += 1
        if buf:
            out.append("<p>%s</p>" % inline(" ".join(buf), ctx))

    return "".join(out)


def parse_list(lines, i, ctx, key):
    items = []
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
            # dong noi tiep cua item truoc
            if items and (line.startswith("  ") or line.startswith("\t")):
                items[-1][2] += " " + line.strip()
                i += 1
                continue
            break
        items.append([len(m.group(1).expandtabs(4)),
                      m.group(2) not in ("-", "*", "+"),
                      m.group(3)])
        i += 1

    parts = []
    stack = []
    for indent, ordered, content in items:
        tag = "ol" if ordered else "ul"
        while stack and indent < stack[-1][0]:
            parts.append("</li></%s>" % stack.pop()[1])
        if not stack or indent > stack[-1][0]:
            parts.append('<%s class="md-list">' % tag)
            stack.append((indent, tag))
        else:
            parts.append("</li>")
        parts.append("<li>%s" % render_item(content, ctx, key))
    while stack:
        parts.append("</li></%s>" % stack.pop()[1])
    return i, "".join(parts)


def render_item(content, ctx, key):
    m = TASK_RE.match(content.strip())
    if not m:
        return inline(content, ctx)
    done = m.group(1).lower() == "x"
    text = m.group(2)
    # Khoa bam theo NOI DUNG chu khong theo vi tri
    # -> sap xep lai note khong lam mat tick.
    slug = hashlib.sha1(plain(text).encode("utf-8")).hexdigest()[:10]
    return ('<label class="task"><input type="checkbox" data-save="%s/%s"%s>'
            "<span>%s</span></label>"
            % (html.escape(key, quote=True), slug,
               " checked" if done else "", inline(text, ctx)))


# --------------------------------------------------------------------------
# thu thap note
# --------------------------------------------------------------------------
def collect():
    found = {}
    for p in ROOT.glob("*.md"):
        if p.name not in EXCLUDE:
            found[p.name] = p
    ordered = []
    for name in PIN_FIRST:
        if name in found:
            ordered.append(found.pop(name))
    for k in sorted(found):
        ordered.append(found[k])
    return ordered


def slugify(stem):
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", stem).strip("-").lower()
    return "n-" + (s or "note")


# --------------------------------------------------------------------------
# CSS / JS — giu tinh than ban v0.5: nen toi, tim kiem loc theo section,
# checkbox luu bang localStorage.
# --------------------------------------------------------------------------
CSS = """
:root{--bg:#050b14;--panel:#0b1a2d;--line:#1d4666;--cyan:#4ed5ff;--gold:#ffd765;
--green:#64e29a;--red:#ff6f7d;--purple:#b06cff;--text:#eef7ff;--muted:#9eb3c8;
--shadow:0 18px 50px rgba(0,0,0,.35)}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
/* overflow-x:hidden CHI dat tren html. Dat them tren body se ep body thanh
   overflow-y:auto -> body tro thanh vung cuon -> thanh nav position:sticky
   het dinh. Tran ngang da duoc chan bang .tablewrap{overflow-x:auto} va
   overflow-wrap:anywhere ben duoi. */
html{max-width:100%;overflow-x:hidden}
body{max-width:100%}
/* Khong dung background-attachment:fixed — iOS Safari render sai tren trang dai,
   ma trang nay chinh la de doc tren dien thoai. Quang sang chi o phan dau trang. */
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
.chip.tag{border-color:#68409a;color:#dabfff;background:#211132}

.card h2.md-h{font-size:20px;margin:22px 0 8px;padding-top:14px;
 border-top:1px solid #ffffff12;color:#fff}
.card h3.md-h{font-size:17px;margin:18px 0 6px;color:#ffe28a}
.card h4.md-h,.card h5.md-h,.card h6.md-h{font-size:15px;margin:14px 0 5px;color:#bfe7ff}
p{margin:9px 0}
hr{border:0;border-top:1px solid #ffffff14;margin:18px 0}
code{background:#071522;border:1px solid #173a55;border-radius:6px;padding:1px 5px;
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

 function filter(){
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
  if(status)status.textContent=s?(hit+'/'+secs.length+' muc'):base;
 }
 if(q){q.addEventListener('input',filter);}

 // Checkbox luu bang localStorage. Khoa bam theo noi dung dong,
 // nen sap xep lai note khong lam mat tick.
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

PAGE = """<!DOCTYPE html>
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
# main
# --------------------------------------------------------------------------
def main():
    if OUT.name in PROTECTED:
        print("TU CHOI: %s nam trong danh sach khong duoc ghi de." % OUT.name)
        return 2
    EXPORT.mkdir(exist_ok=True)

    files = collect()
    if not files:
        print("Khong tim thay file .md nao o goc vault.")
        return 1

    ctx = {"anchors": {}}
    for p in files:
        ctx["anchors"][p.stem.lower()] = slugify(p.stem)

    notes = []
    for path in files:
        meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
        title = None
        for k, ln in enumerate(body):
            if ln.strip().startswith("# "):
                title = ln.strip()[2:].strip()
                body = body[:k] + body[k + 1:]
                break
        if not title:
            alias = meta.get("aliases")
            title = alias[0] if isinstance(alias, list) and alias else path.stem
        notes.append((path, meta, title, body))

    ctx_meta = {}
    for path, meta, title, body in notes:
        if path.name == "_CONTEXT.md":
            ctx_meta = meta
            break

    parts = []
    nav = []

    for path, meta, title, body in notes:
        anchor = slugify(path.stem)
        key = path.stem
        nav.append('<a href="#%s">%s</a>' % (anchor, html.escape(title)))

        chips = []
        kt = meta.get("kiem-tra") or meta.get("kiem-tra-lan-cuoi")
        if kt:
            chips.append('<span class="chip date">kiem tra: %s</span>' % html.escape(str(kt)))
        else:
            chips.append('<span class="chip bad">THIEU kiem-tra</span>')
            warnings.append("THIEU kiem-tra trong frontmatter: %s" % path.name)
        tags = meta.get("tags")
        if isinstance(tags, list):
            for t in tags:
                if t != "leiting":
                    chips.append('<span class="chip tag">#%s</span>' % html.escape(t))
        dtc = meta.get("do-tin-cay")
        if dtc:
            chips.append('<span class="chip bad">%s</span>' % html.escape(str(dtc)))

        hay = [path.stem, title]
        alias = meta.get("aliases")
        if isinstance(alias, list):
            hay.extend(alias)
        if isinstance(tags, list):
            hay.extend(tags)

        parts.append(
            '<section id="%s" data-search="%s"><div class="card">'
            '<div class="sec-head"><h2>%s</h2><div class="chips">%s</div></div>'
            "%s</div></section>"
            % (anchor,
               html.escape(" ".join(hay), quote=True),
               html.escape(title),
               "".join(chips),
               blocks(body, ctx, key))
        )

    stamps = []
    if ctx_meta.get("ban-game"):
        stamps.append("<span>ban game: %s</span>" % html.escape(str(ctx_meta["ban-game"])))
    if ctx_meta.get("kiem-tra-lan-cuoi"):
        stamps.append("<span>kiem tra lan cuoi: %s</span>"
                      % html.escape(str(ctx_meta["kiem-tra-lan-cuoi"])))
    stamps.append("<span>%d note &middot; %d anh nhung</span>"
                  % (len(notes), len(_img_cache)))

    doc = (PAGE
           .replace("__TITLE__", "Wiki 雷霆战机：集结 — trang bị, pilot, tier")
           .replace("__EYEBROW__", "雷霆战机：集结〔Lôi Đình Chiến Cơ: Tập Kết〕 &middot; vault cá nhân")
           .replace("__CSS__", CSS)
           .replace("__STAMPS__", "".join(stamps))
           .replace("__NAV__", "".join(nav))
           .replace("__COUNT__", str(len(notes)))
           .replace("__BODY__", "".join(parts))
           .replace("__JS__", JS))

    OUT.write_text(doc, encoding="utf-8")

    print("Da xuat: %s" % OUT)
    print("  %d note, %d anh nhung, %.0f KB"
          % (len(notes), len(_img_cache), len(doc.encode("utf-8")) / 1024))
    for path, meta, title, body in notes:
        print("    - %-24s %s" % (path.name, title))
    if warnings:
        print("")
        print("Canh bao (%d):" % len(warnings))
        for w in dict.fromkeys(warnings):
            print("  ! %s" % w)
    else:
        print("")
        print("Khong co canh bao.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
