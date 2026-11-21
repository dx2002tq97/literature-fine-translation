#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据表提取——把文献中的表格导出为 CSV 与 Markdown。

用法:
    python extract_tables.py <pdf> --out <目录> [--pages 1,3-5]

路线:
    1. find_tables() 官方表格识别(兼容性随版本浮动)
    2. 自研线段网格重建: get_drawings 收集横竖线段 → 聚类成网格 → 单元格文字归位
       (pymupdf 2.x 实测 find_tables 对线段表返回空, 自研路线为主力)
    3. 扫描版 PDF: 无矢量线可依 → 提示先 ocr_pdf.py, OCR 表格务必人工核对数值
输出: tables_p<页>_t<序>.csv (utf-8-sig, Excel 直开) / .md
"""
import argparse, csv, os

from pdf_common import fitz, parse_pages

def collect_segments(page):
    """收集水平/垂直线段: {"o":方向, "pos":定位坐标, "a":起点, "b":终点}"""
    segs = []
    for d in page.get_drawings():
        for it in d["items"]:
            if it[0] == "l":
                p1, p2 = it[1], it[2]
                if abs(p1.y - p2.y) < 1.5:
                    segs.append({"o": "h", "pos": p1.y, "a": min(p1.x, p2.x), "b": max(p1.x, p2.x)})
                elif abs(p1.x - p2.x) < 1.5:
                    segs.append({"o": "v", "pos": p1.x, "a": min(p1.y, p2.y), "b": max(p1.y, p2.y)})
            elif it[0] == "re":
                r = it[1]
                if 1 < r.width < page.rect.width * 0.95 and 1 < r.height < page.rect.height * 0.95:
                    segs += [{"o": "h", "pos": r.y0, "a": r.x0, "b": r.x1},
                             {"o": "h", "pos": r.y1, "a": r.x0, "b": r.x1},
                             {"o": "v", "pos": r.x0, "a": r.y0, "b": r.y1},
                             {"o": "v", "pos": r.x1, "a": r.y0, "b": r.y1}]
    return segs

def crossings(s, opp):
    """线段 s 与反方向线段集合的真实交点数(交点须在两线段范围内)。"""
    n = 0
    for t in opp:
        if t["a"] - 1 <= s["pos"] <= t["b"] + 1 and s["a"] - 1 <= t["pos"] <= s["b"] + 1:
            n += 1
    return n

def refine_grid_segs(segs, min_cross=3):
    """迭代剔除非网格线: 交点数 < min_cross 的线不可能是表格网格线
    (孤立的图形边框/装饰线只有 ≤2 个交点)。"""
    segs = list(segs)
    while True:
        hs = [s for s in segs if s["o"] == "h"]
        vs = [s for s in segs if s["o"] == "v"]
        keep = [s for s in hs if crossings(s, vs) >= min_cross] + \
               [s for s in vs if crossings(s, hs) >= min_cross]
        if len(keep) == len(segs) or not keep:
            return keep if keep else []
        segs = keep

def grid_from_segments(segs):
    """先迭代筛除非网格线, 再聚类成网格坐标; 不足两行两列返回 None。"""
    segs = refine_grid_segs(segs)
    hs = sorted({round(s["pos"], 1) for s in segs if s["o"] == "h"})
    vs = sorted({round(s["pos"], 1) for s in segs if s["o"] == "v"})
    # 合并相近坐标(±2pt)
    def merge(vals):
        out = []
        for v in vals:
            if not out or v - out[-1] > 2:
                out.append(v)
        return out
    hs, vs = merge(hs), merge(vs)
    if len(hs) < 2 or len(vs) < 2:
        return None
    return hs, vs

def cells_from_grid(page, hs, vs):
    rows, cols = len(hs) - 1, len(vs) - 1
    grid = [["" for _ in range(cols)] for _ in range(rows)]
    filled = 0
    for wd in page.get_text("words"):
        cx, cy = (wd[0] + wd[2]) / 2, (wd[1] + wd[3]) / 2
        ri = next((i for i in range(rows) if hs[i] <= cy <= hs[i + 1]), None)
        ci = next((j for j in range(cols) if vs[j] <= cx <= vs[j + 1]), None)
        if ri is not None and ci is not None:
            grid[ri][ci] = (grid[ri][ci] + " " + wd[4]).strip()
            filled += 1
    return grid, filled

def to_markdown(data):
    rows = [["" if c is None else str(c).replace("|", "\\|").replace("\n", " ") for c in r] for r in data]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    lines = ["| " + " | ".join(rows[0]) + " |",
             "|" + "|".join(["---"] * width) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(lines)

def save_table(data, stem):
    with open(stem + ".csv", "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows(data)
    with open(stem + ".md", "w", encoding="utf-8") as f:
        f.write(to_markdown(data))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", help="如 1,3-5; 缺省全部")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    doc = fitz.open(args.pdf)
    pages = parse_pages(args.pages, len(doc))
    n_found = 0
    scan_pages = []

    for pno in pages:
        page = doc[pno - 1]
        got = []
        # 路线 1: 官方 find_tables
        try:
            for tab in page.find_tables().tables:
                got.append((tab.extract(), [round(v, 1) for v in tab.bbox]))
        except Exception:
            pass
        # 路线 2: 自研线段网格重建
        try:
            segs = collect_segments(page)
            g = grid_from_segments(segs)
            if g:
                hs, vs = g
                grid, filled = cells_from_grid(page, hs, vs)
                bbox = [min(vs), min(hs), max(vs), max(hs)]
                # 去重: 与 find_tables 结果 bbox 高度重叠则跳过
                dup = any(abs(b[0]-bbox[0]) < 5 and abs(b[1]-bbox[1]) < 5 and
                          abs(b[2]-bbox[2]) < 5 and abs(b[3]-bbox[3]) < 5 for _, b in got)
                if not dup and filled >= max(2, 0.3 * (len(hs)-1) * (len(vs)-1)):
                    got.append((grid, bbox))
        except Exception as e:
            print(f"page {pno}: 网格重建异常 {e}")

        if not got:
            if len(page.get_text().strip()) < 50:
                scan_pages.append(pno)
            continue
        for k, (data, bbox) in enumerate(got, 1):
            stem = os.path.join(args.out, f"tables_p{pno}_t{k}")
            save_table(data, stem)
            n_found += 1
            print(f"page {pno} 表 {k} @ {bbox}: {len(data)} 行 x {len(data[0]) if data else 0} 列 -> {os.path.basename(stem)}.csv/.md")

    doc.close()
    if scan_pages:
        print(f"提示: 页 {scan_pages} 疑似扫描页(无文本层/无表格线)——先跑 ocr_pdf.py, OCR 表格务必人工核对数值再使用")
    if n_found == 0:
        print("未检测到表格。扫描版表格请: crop_region.py 裁表 → ocr_pdf.py 识别 → 人工逐格核对")
    else:
        print(f"共导出 {n_found} 张表 -> {args.out}")

if __name__ == "__main__":
    main()
