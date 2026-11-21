#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""提取 PDF 文本块（按分栏）与整页渲染图——文献精细翻译第 1 步。

用法:
    python extract_pdf.py <pdf路径> --out <输出目录> [--cols 2] [--dpi 100]

输出（写入 --out 目录）:
    col_L<n>.txt / col_R<n>.txt   左/右栏文本块，块内按行、块间按 y 排序（--cols 2 时）
    page<n>.txt                    不分栏全文（--cols 1 或同时生成）
    scan_p<n>.png                  整页渲染图（核对公式/图表/引文上标用）
    blocks_p<n>.json               文本块坐标 {x0,y0,x1,y1,text}（规划图形裁剪区域用）
    pages.json                     页面尺寸与页数汇总

说明:
    - 文本层仅作初稿；公式、上标引文、化学式必须对照 scan_p<n>.png 人工核对后落稿。
    - 纯扫描件（page<n>.txt 近空）时先跑 ocr_pdf.py（Tesseract CLI）再解析。
"""
import argparse, json, os, sys, warnings

from pdf_common import fitz

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cols", type=int, default=2, choices=[1, 2])
    ap.add_argument("--dpi", type=int, default=100)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    doc = fitz.open(args.pdf)
    meta = {"pages": len(doc), "page_sizes": []}

    for i, page in enumerate(doc):
        n = i + 1
        W = page.rect.width
        meta["page_sizes"].append([round(W, 1), round(page.rect.height, 1)])

        d = page.get_text("dict")
        blocks = []
        for blk in d["blocks"]:
            if blk["type"] != 0:
                continue
            x0, y0, x1, y1 = blk["bbox"]
            lines = ["".join(sp["text"] for sp in ln["spans"]).strip()
                     for ln in blk["lines"]]
            lines = [s for s in lines if s]
            if lines:
                blocks.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1,
                               "text": "\n".join(lines)})

        with open(os.path.join(args.out, f"blocks_p{n}.json"), "w", encoding="utf-8") as f:
            json.dump(blocks, f, ensure_ascii=False, indent=1)

        def write_sorted(path, items):
            items.sort(key=lambda b: (round(b["y0"], 1), round(b["x0"], 1)))
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(b["text"] for b in items))

        if args.cols == 2:
            mid = W / 2
            left = [b for b in blocks if (b["x0"] + b["x1"]) / 2 < mid]
            right = [b for b in blocks if (b["x0"] + b["x1"]) / 2 >= mid]
            write_sorted(os.path.join(args.out, f"col_L{n}.txt"), left)
            write_sorted(os.path.join(args.out, f"col_R{n}.txt"), right)
        write_sorted(os.path.join(args.out, f"page{n}.txt"), blocks)

        page.get_pixmap(dpi=args.dpi).save(os.path.join(args.out, f"scan_p{n}.png"))

        imgs = page.get_images(full=True)
        if imgs:
            print(f"page {n}: {len(blocks)} text blocks, {len(imgs)} embedded image(s)")

    with open(os.path.join(args.out, "pages.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    doc.close()
    print(f"done -> {args.out}")

if __name__ == "__main__":
    main()
