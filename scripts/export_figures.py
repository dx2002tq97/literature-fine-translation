#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文献图表导出器——原理图/机制图/曲线图批量导出为矢量 PDF、SVG 与高清 PNG。

用法:
    python export_figures.py <pdf> --out <目录> [--pages 1,3-5] [--min-area 400] [--formats pdf,svg,png]

原理:
    - 电子版 PDF: cluster_drawings() 聚类矢量绘图区域 + 内嵌位图区域 → 逐区导出
      (矢量 PDF/SVG 经 show_pdf_page 裁剪, 线条与文字保持矢量, 缩放无损)
    - 扫描版 PDF: 无矢量对象 → 报告并提示走 crop_region.py + trace_vector.py 描摹
输出: p<页>_fig<序>_<y坐标>.{pdf,svg,png} + manifest.json
"""
import argparse, glob, json, os

try:
    import pymupdf as fitz
except ImportError:
    import warnings
    warnings.filterwarnings("ignore")
    import fitz

def parse_pages(spec, total):
    if not spec:
        return range(1, total + 1)
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return sorted({p for p in out if 1 <= p <= total})

def merge_rects(rects):
    """两两合并重叠矩形, 直到稳定。"""
    rects = [fitz.Rect(r) for r in rects]
    changed = True
    while changed:
        changed = False
        out = []
        for r in rects:
            hit = None
            for i, m in enumerate(out):
                if m.intersects(r):
                    hit = i
                    break
            if hit is None:
                out.append(r)
            else:
                out[hit] |= r
                changed = True
        rects = out
    return rects

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", help="如 1,3-5; 缺省全部")
    ap.add_argument("--min-area", type=float, default=400, help="最小图形面积(pt²), 过滤碎线")
    ap.add_argument("--formats", default="pdf,svg,png")
    ap.add_argument("--dpi", type=int, default=300)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    formats = [f.strip().lower() for f in args.formats.split(",")]
    src = fitz.open(args.pdf)
    pages = parse_pages(args.pages, len(src))
    manifest = []

    for pno in pages:
        page = src[pno - 1]
        page_area = abs(page.rect)
        rects = []
        n_vec = 0
        try:
            clusters = page.cluster_drawings()
            n_vec = len(clusters)
            rects.extend(fitz.Rect(r) for r in clusters)
        except Exception as e:
            print(f"page {pno}: cluster_drawings 失败 {e}")
        for img in page.get_images(full=True):
            for r in page.get_image_rects(img[0]):
                rects.append(fitz.Rect(r))
        rects = [r for r in rects if abs(r) >= args.min_area and abs(r) < 0.85 * page_area]
        rects = merge_rects(rects)
        if not rects:
            print(f"page {pno}: 无独立图形区域 (矢量对象 {n_vec})")
            continue

        base = os.path.join(args.out, f"p{pno}")
        for k, r in enumerate(sorted(rects, key=lambda r: (r.y0, r.x0)), 1):
            stem = f"{base}_fig{k}_{int(r.y0)}"
            entry = {"page": pno, "index": k, "rect": [round(v, 1) for v in r],
                     "vector": n_vec > 0, "files": []}
            if "pdf" in formats:
                nd = fitz.open()
                np_ = nd.new_page(width=r.width, height=r.height)
                np_.show_pdf_page(np_.rect, src, pno - 1, clip=r)
                nd.save(stem + ".pdf")
                nd.close()
                entry["files"].append(os.path.basename(stem + ".pdf"))
            if "svg" in formats:
                tmp = fitz.open()
                tp = tmp.new_page(width=r.width, height=r.height)
                tp.show_pdf_page(tp.rect, src, pno - 1, clip=r)
                with open(stem + ".svg", "w", encoding="utf-8") as f:
                    f.write(tp.get_svg_image())
                tmp.close()
                entry["files"].append(os.path.basename(stem + ".svg"))
            if "png" in formats:
                page.get_pixmap(dpi=args.dpi, clip=r).save(stem + ".png")
                entry["files"].append(os.path.basename(stem + ".png"))
            manifest.append(entry)
        print(f"page {pno}: 导出 {len(rects)} 个图形区域 (矢量对象 {n_vec})")

    src.close()
    mf = os.path.join(args.out, "manifest.json")
    with open(mf, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    if not any(e["vector"] for e in manifest):
        print("提示: 未发现矢量对象——本 PDF 可能是扫描版。图表请用 crop_region.py 裁剪后 trace_vector.py 描摹矢量化。")
    print(f"清单 -> {mf}")

if __name__ == "__main__":
    main()
