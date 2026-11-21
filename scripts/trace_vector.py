#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""位图描摹矢量化——把扫描版文献的原理图/机制图/曲线图转为 SVG 矢量线稿。

用法:
    python trace_vector.py <图片.png> [--mode line|shape] [--tolerance 1.5] [--out 图.svg] [--preview]
    python trace_vector.py <pdf> --page 5 --rect 35,448,302,710 [--dpi 300] ...  (直接从 PDF 裁)

原理: opencv 阈值分割 → findContours 轮廓提取 → approxPolyDP 折线简化 → SVG path
模式:
    line  描边线稿(默认)——曲线图、原理图、机构简图, fill=none stroke=black
    shape 填充轮廓——色块/实心符号, fill-rule=evenodd
说明: 描摹适合线型图形; 照片类与复杂色图不适合。--preview 输出描摹回绘 PNG 供比对。
"""
import argparse, os

import cv2
import numpy as np

from pdf_common import fitz

def contours_to_svg_path(contours, tolerance):
    parts = []
    for c in contours:
        if cv2.contourArea(c) < 3:  # 噪点
            continue
        approx = cv2.approxPolyDP(c, tolerance, True).reshape(-1, 2)
        if len(approx) < 2:
            continue
        d = "M " + " L ".join(f"{x},{y}" for x, y in approx) + " Z"
        parts.append(d)
    return parts

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="图片文件或 PDF")
    ap.add_argument("--page", type=int, help="PDF 页码(1 起)")
    ap.add_argument("--rect", help="x0,y0,x1,y1 (pt), PDF 模式必填")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--mode", choices=["line", "shape"], default="line")
    ap.add_argument("--tolerance", type=float, default=1.5, help="折线简化容差(px), 越大越平滑越失真")
    ap.add_argument("--out", required=True)
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()

    if args.source.lower().endswith(".pdf"):
        if not (args.page and args.rect):
            raise SystemExit("PDF 模式需 --page 与 --rect")
        x0, y0, x1, y1 = (float(v) for v in args.rect.split(","))
        doc = fitz.open(args.source)
        pix = doc[args.page - 1].get_pixmap(dpi=args.dpi, clip=fitz.Rect(x0, y0, x1, y1))
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if pix.n >= 3 else img[:, :, 0]
        doc.close()
    else:
        gray = cv2.imread(args.source, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            raise SystemExit(f"无法读取图片 {args.source}")

    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    if bw.mean() > 127:  # 前景占比过高 → 反相(深底浅线)
        bw = 255 - bw

    mode = cv2.RETR_CCOMP if args.mode == "shape" else cv2.RETR_LIST
    contours, _ = cv2.findContours(bw, mode, cv2.CHAIN_APPROX_SIMPLE)
    paths = contours_to_svg_path(contours, args.tolerance)

    h, w = bw.shape
    if args.mode == "shape":
        body = "".join(f'<path d="{d}" fill="#000" fill-rule="evenodd" stroke="none"/>' for d in paths)
    else:
        body = "".join(f'<path d="{d}" fill="none" stroke="#000" stroke-width="1"/>' for d in paths)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
           f'width="{w}px" height="{h}px">{body}</svg>')
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"svg  -> {args.out} ({len(paths)} 条路径, {w}x{h}px)")

    if args.preview:
        pre = os.path.splitext(args.out)[0] + "_preview.png"
        canvas = np.full((h, w), 255, np.uint8)
        cv2.drawContours(canvas, contours, -1, 0, 1)
        cv2.imwrite(pre, canvas)
        print(f"预览 -> {pre}")

if __name__ == "__main__":
    main()
