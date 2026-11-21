#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按坐标裁剪页面区域为高清 PNG——公式/图表核对与图形嵌入专用。

用法:
    python crop_region.py <pdf> --page 5 --rect 35,448,302,710 [--dpi 200] --out fig1.png

坐标为 PDF 点(pt), 左上原点, 顺序 x0,y0,x1,y1。
坐标来源: extract_pdf.py 产出的 blocks_p<n>.json + 整页渲染图目测框选。
"""
import argparse

from pdf_common import fitz

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--page", type=int, required=True, help="1 起始页码")
    ap.add_argument("--rect", required=True, help="x0,y0,x1,y1 (pt)")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    x0, y0, x1, y1 = (float(v) for v in args.rect.split(","))
    doc = fitz.open(args.pdf)
    page = doc[args.page - 1]
    pix = page.get_pixmap(dpi=args.dpi, clip=fitz.Rect(x0, y0, x1, y1))
    pix.save(args.out)
    doc.close()
    print(f"saved {args.out} ({pix.width}x{pix.height}px, dpi={args.dpi})")

if __name__ == "__main__":
    main()
