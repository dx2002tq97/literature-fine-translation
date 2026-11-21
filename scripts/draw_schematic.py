#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""科研示意图生成器——参数化生成结构化、可编辑的 SVG 原理图。

用法:
    python draw_schematic.py cylinder --cx 150 --r 80 --ry 28 --h 380 --out cylinder.svg [--png]

特性:
    - 输出语义分层 SVG: 每个部件独立 <g id>, 带中文注释, Inkscape/Illustrator 中可逐元素编辑
    - cylinder: 圆柱透视图——管身 + 底部前缘实线弧 + 底部背面虚线弧(stroke-dasharray) + 顶部椭圆口
    - --png 同时渲染位图预览(pymupdf)

图元库持续扩充: sphere / plane_electrode / needle / gap_arrow / 边界框等, 见 SKILL.md。
"""
import argparse

from pdf_common import fitz

def esc(x):
    return f"{x:.1f}".rstrip("0").rstrip(".")

def svg_cylinder(cx=150, cy_top=60, r=80, ry=28, h=380, sw=2,
                 dash="0.5 6", margin_x=70, margin_bottom=52):
    """圆柱透视: 顶部完整椭圆; 底部前缘实线弧 + 背面虚线弧; 管身矩形遮挡背面弧上半段。"""
    cy_bot = cy_top + h
    W = int(2 * r + 2 * margin_x)
    H = int(cy_top + h + ry + margin_bottom)
    left, right = cx - r, cx + r
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">

  <!-- 第1层：管身（白色填充矩形用于遮挡底部虚线弧穿过管内的部分；两侧竖线为管壁轮廓） -->
  <g id="tube-body">
    <rect x="{esc(left)}" y="{esc(cy_top)}" width="{esc(2 * r)}" height="{esc(h)}" fill="#ffffff" stroke="none"/>
    <line x1="{esc(left)}" y1="{esc(cy_top)}" x2="{esc(left)}" y2="{esc(cy_bot)}" stroke="#000000" stroke-width="{sw}"/>
    <line x1="{esc(right)}" y1="{esc(cy_top)}" x2="{esc(right)}" y2="{esc(cy_bot)}" stroke="#000000" stroke-width="{sw}"/>
  </g>

  <!-- 第2层：底部下半弧（实线，看得见的前缘） -->
  <g id="bottom-front-arc-solid">
    <path d="M {esc(left)},{esc(cy_bot)} A {esc(r)},{esc(ry)} 0 0 0 {esc(right)},{esc(cy_bot)}"
          fill="none" stroke="#000000" stroke-width="{sw}" stroke-linecap="round"/>
  </g>

  <!-- 第3层：底部上半弧（虚线，被管壁挡住的背面轮廓；dasharray 控制虚线样式） -->
  <g id="bottom-back-arc-dashed">
    <path d="M {esc(left)},{esc(cy_bot)} A {esc(r)},{esc(ry)} 0 0 1 {esc(right)},{esc(cy_bot)}"
          fill="none" stroke="#000000" stroke-width="{sw}"
          stroke-dasharray="{dash}" stroke-linecap="round"/>
  </g>

  <!-- 第4层：顶部完整椭圆（实线，管口） -->
  <g id="top-ellipse">
    <ellipse cx="{esc(cx)}" cy="{esc(cy_top)}" rx="{esc(r)}" ry="{esc(ry)}"
             fill="#ffffff" stroke="#000000" stroke-width="{sw}"/>
  </g>
</svg>
'''

KINDS = {"cylinder": svg_cylinder}

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="kind", required=True)
    c = sub.add_parser("cylinder", help="圆柱透视图(虚实底)")
    c.add_argument("--cx", type=float, default=150, help="圆心 x")
    c.add_argument("--cy-top", type=float, default=60, help="顶部椭圆中心 y")
    c.add_argument("--r", type=float, default=80, help="半径")
    c.add_argument("--ry", type=float, default=28, help="椭圆纵半径(透视深度)")
    c.add_argument("--h", type=float, default=380, help="管高")
    c.add_argument("--sw", type=float, default=2, help="线宽")
    c.add_argument("--dash", default="0.5 6", help="背面虚线 dasharray")
    for s in sub.choices.values():
        s.add_argument("--out", required=True)
        s.add_argument("--png", action="store_true", help="同时渲染 PNG 预览")
    args = ap.parse_args()

    svg = KINDS[args.kind](**{k: v for k, v in vars(args).items()
                              if k not in ("kind", "out", "png")})
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"svg  -> {args.out}")

    if args.png:
        d = fitz.open(args.out)
        png = args.out.rsplit(".", 1)[0] + "_preview.png"
        d[0].get_pixmap(dpi=150).save(png)
        d.close()
        print(f"预览 -> {png}")

if __name__ == "__main__":
    main()
