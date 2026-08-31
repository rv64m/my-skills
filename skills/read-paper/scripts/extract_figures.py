#!/usr/bin/env python3
"""
按 caption 定位并裁剪论文中的图 / 表 / 算法框，输出 PNG + manifest.json。

为什么需要它：论文里的架构图绝大多数是矢量绘制的（matplotlib / TikZ / Illustrator），
`pdfimages` 只能拿到位图对象，对这类图返回空。本脚本改为：
  1. 用正则在文本块里找 caption（Figure / Table / Algorithm N）；
  2. 求 caption 同侧的矢量绘图 bbox、位图 bbox、图内短文本标签的并集；
  3. 用"整段散文文本块"作为边界，防止裁进正文；
  4. 按并集区域渲染该页局部。

用法:
    python extract_figures.py paper.pdf -o out_dir [--dpi 150] [--pages 3-9]

依赖: pymupdf  (pip install pymupdf --break-system-packages -q)
"""
import argparse
import json
import os
import re
import sys

try:
    import pymupdf  # noqa
except ImportError:  # 老版本包名
    try:
        import fitz as pymupdf  # noqa
    except ImportError:
        sys.exit("需要 pymupdf: pip install pymupdf --break-system-packages -q")

CAPTION_RE = re.compile(
    r"^\s*(figure|fig\.?|table|algorithm|alg\.?|chart|exhibit)\s*\.?\s*"
    r"(\d+[a-z]?|[ivxlc]+)\b",
    re.IGNORECASE,
)

# Table/Exhibit 的题注通常在上方，正文在下方；Figure 相反。
CAPTION_ABOVE_CONTENT = {"table", "exhibit", "algorithm", "alg"}


def kind_of(caption_text):
    m = CAPTION_RE.match(caption_text)
    if not m:
        return None, None
    word = m.group(1).lower().rstrip(".")
    word = {"fig": "figure", "alg": "algorithm"}.get(word, word)
    return word, f"{word.capitalize()} {m.group(2)}"


def is_prose(block, text_width):
    """整段正文：够宽 + 词够多。图内标签、表格单元格都不满足。"""
    text = block[4].strip()
    if not text:
        return False
    if CAPTION_RE.match(text):
        return False
    width = block[2] - block[0]
    return len(text.split()) >= 14 and width > 0.45 * text_width


def collect(page, min_area=40):
    """返回 (prose_blocks, atoms)。atoms = 可能属于图表的元素 bbox。"""
    blocks = [b for b in page.get_text("blocks") if b[6] == 0]
    pw = page.rect.width
    prose = [b for b in blocks if is_prose(b, pw)]
    atoms = []
    for b in blocks:
        if b in prose or CAPTION_RE.match(b[4].strip()):
            continue
        atoms.append(pymupdf.Rect(b[:4]))
    for d in page.get_drawings():
        r = pymupdf.Rect(d["rect"])
        if r.get_area() > min_area and r.width < pw * 0.98:
            atoms.append(r)
    for info in page.get_image_info():
        atoms.append(pymupdf.Rect(info["bbox"]))
    return prose, atoms


def region_for(page, cap_rect, kind, prose, atoms):
    """求 caption 对应的图表区域。搜索方向由 kind 决定，失败则反向重试。"""
    page_r = page.rect
    above_first = kind in CAPTION_ABOVE_CONTENT

    def build(search_down):
        if search_down:
            edge = cap_rect.y1
            stops = [b[1] for b in prose if b[1] >= edge + 2]
            limit = min(stops) if stops else page_r.y1
            sel = [a for a in atoms if a.y0 >= edge - 2 and a.y1 <= limit + 2]
        else:
            edge = cap_rect.y0
            stops = [b[3] for b in prose if b[3] <= edge - 2]
            limit = max(stops) if stops else page_r.y0
            sel = [a for a in atoms if a.y1 <= edge + 2 and a.y0 >= limit - 2]
        if not sel:
            return None
        r = pymupdf.Rect(sel[0])
        for a in sel[1:]:
            r |= a
        return r

    rect = build(search_down=above_first)
    if rect is None or rect.height < 18:
        alt = build(search_down=not above_first)
        if alt is not None and (rect is None or alt.height > rect.height):
            rect = alt
    if rect is None:
        return None

    rect |= cap_rect
    rect += (-8, -8, 8, 8)  # padding
    rect &= page_r
    # 防止异常吞掉整页
    if rect.height > page_r.height * 0.92:
        rect.y0 = max(page_r.y0, cap_rect.y0 - page_r.height * 0.8) if not above_first else rect.y0
    return rect


def parse_pages(spec, n):
    if not spec:
        return range(n)
    out = set()
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a) - 1, int(b)))
        else:
            out.add(int(part) - 1)
    return sorted(p for p in out if 0 <= p < n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("-o", "--outdir", default="figures")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--pages", default=None, help="如 3-9 或 2,5,7（1-based）")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    doc = pymupdf.open(args.pdf)
    manifest, seen = [], set()

    for pno in parse_pages(args.pages, doc.page_count):
        page = doc[pno]
        blocks = [b for b in page.get_text("blocks") if b[6] == 0]
        caps = [b for b in blocks if CAPTION_RE.match(b[4].strip())]
        if not caps:
            continue
        prose, atoms = collect(page)
        for b in caps:
            kind, label = kind_of(b[4].strip())
            if not kind or label in seen:
                continue
            rect = region_for(page, pymupdf.Rect(b[:4]), kind, prose, atoms)
            if rect is None or rect.height < 18:
                continue
            seen.add(label)
            fname = re.sub(r"\W+", "_", label).lower() + f"_p{pno+1}.png"
            path = os.path.join(args.outdir, fname)
            page.get_pixmap(clip=rect, dpi=args.dpi).save(path)
            caption = " ".join(b[4].split())
            manifest.append({
                "label": label,
                "kind": kind,
                "page": pno + 1,
                "file": path,
                "caption": caption[:400],
            })

    with open(os.path.join(args.outdir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    for m in manifest:
        print(f"{m['label']:<14} p{m['page']:<4} {m['file']}")
    print(f"\n共 {len(manifest)} 个图表 -> {args.outdir}/manifest.json")
    if not manifest:
        print("未找到 caption。可能是扫描件或非常规排版 —— 改用 pdftoppm 整页渲染。")


if __name__ == "__main__":
    main()
