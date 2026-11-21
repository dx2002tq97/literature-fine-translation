#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描件 OCR 兜底——无文本层 PDF 的文字提取。

用法:
    python ocr_pdf.py <pdf> --out <目录> [--pages 1,3-5] [--lang eng]

路线: 整页渲染 PNG → tesseract CLI 逐页识别 → ocr_page<n>.txt
    (比 PyMuPDF 内置 OCR 更可控, 失败不中断, 逐页报错)
依赖: Tesseract ≥ 5 (自动探测 PATH 与常见安装路径), eng 语言包
注意: OCR 结果同样只作初稿——公式/上标/化学式仍须对照渲染图核对。
"""
import argparse, os, shutil, subprocess

CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

def find_tesseract():
    p = shutil.which("tesseract")
    if p:
        return p
    for c in CANDIDATES:
        if os.path.exists(c):
            return c
    raise SystemExit("未找到 tesseract.exe; 请安装 Tesseract OCR 或补全 CANDIDATES 路径")

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
    return [p for p in out if 1 <= p <= total]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", help="如 1,3-5; 缺省全部")
    ap.add_argument("--lang", default="eng")
    ap.add_argument("--dpi", type=int, default=300)
    args = ap.parse_args()

    try:
        import pymupdf as fitz
    except ImportError:
        import warnings
        warnings.filterwarnings("ignore")
        import fitz

    os.makedirs(args.out, exist_ok=True)
    tess = find_tesseract()
    doc = fitz.open(args.pdf)
    pages = parse_pages(args.pages, len(doc))
    for p in pages:
        page = doc[p - 1]
        png = os.path.join(args.out, f"page{p}.png")
        page.get_pixmap(dpi=args.dpi).save(png)
        txt = os.path.join(args.out, f"ocr_page{p}.txt")
        r = subprocess.run([tess, png, txt.rsplit(".", 1)[0], "-l", args.lang, "--psm", "3"],
                           capture_output=True, text=True)
        if os.path.exists(txt):
            print(f"page {p}: OK ({os.path.getsize(txt)} bytes)")
        else:
            print(f"page {p}: FAILED {r.stderr[:200]}")
    doc.close()
    print(f"done -> {args.out} (渲染图已保留, 供公式核对)")

if __name__ == "__main__":
    main()
