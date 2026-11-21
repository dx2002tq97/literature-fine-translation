#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工具箱公共模块——统一 PyMuPDF 导入、页码解析、tesseract 探测。

各脚本用法:
    from pdf_common import fitz, parse_pages, find_tesseract

说明:
    - fitz: 优先 import pymupdf(新 API), 回退 import fitz(旧名), 并抑制弃用警告
    - parse_pages("1,3-5", total) -> 有序页码列表(1 起始, 越界剔除, 去重)
    - find_tesseract(): 探测 PATH 与常见安装路径, 找不到抛 SystemExit
"""
import os
import shutil
import warnings

try:
    import pymupdf as fitz
except ImportError:
    warnings.filterwarnings("ignore")
    import fitz

TESSERACT_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

def parse_pages(spec, total):
    """页码选择: "1,3-5" 或 None(全部) -> 有序列表, 1 起始, 越界剔除。"""
    if not spec:
        return list(range(1, total + 1))
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return sorted({p for p in out if 1 <= p <= total})

def find_tesseract():
    """探测 tesseract.exe: PATH 优先, 再常见安装路径。"""
    p = shutil.which("tesseract")
    if p:
        return p
    for c in TESSERACT_CANDIDATES:
        if os.path.exists(c):
            return c
    raise SystemExit("未找到 tesseract.exe; 请安装 Tesseract OCR 或补全 TESSERACT_CANDIDATES 路径")
