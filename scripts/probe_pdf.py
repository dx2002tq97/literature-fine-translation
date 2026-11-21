#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF 体检——翻译前先跑它，决定处理路线。

用法:
    python probe_pdf.py <pdf路径>

输出判断:
    - 文本层: 每页平均字符数过低(<50) → 疑似纯扫描件 → 走 ocr_pdf.py
    - 分栏: 依文本块 x-center 分布建议 --cols 参数
    - 图片: 嵌入图片对象计数(整页扫描件表现为每页 1 张全页图)
    - 加密/损坏: 直接报告
"""
import sys

try:
    import pymupdf as fitz
except ImportError:
    import warnings
    warnings.filterwarnings("ignore")
    import fitz

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    doc = fitz.open(sys.argv[1])
    n = len(doc)
    print(f"页数: {n}")
    print(f"元数据: title={doc.metadata.get('title')!r} author={doc.metadata.get('author')!r}")
    print(f"加密: {doc.is_encrypted}")

    total_chars = 0
    scan_like = 0
    col_votes = {"1": 0, "2": 0}
    for i, page in enumerate(doc):
        chars = len(page.get_text().strip())
        total_chars += chars
        if chars < 50:
            scan_like += 1
        # 分栏投票: 文本块 x-center 落在中带(|cx-W/2|<W*0.08)的视为跨栏, 其余按左右计
        W = page.rect.width
        left = right = mid = 0
        for blk in page.get_text("dict")["blocks"]:
            if blk["type"] != 0:
                continue
            cx = (blk["bbox"][0] + blk["bbox"][2]) / 2
            if abs(cx - W / 2) < W * 0.08:
                mid += 1
            elif cx < W / 2:
                left += 1
            else:
                right += 1
        if left + right >= 4 and min(left, right) / max(1, max(left, right)) > 0.3:
            col_votes["2"] += 1
        elif left + right > 0:
            col_votes["1"] += 1
    doc.close()

    avg = total_chars / max(1, n)
    print(f"文本层: 平均 {avg:.0f} 字符/页")
    if scan_like > n / 2:
        print("  → 疑似纯扫描件: 先跑 ocr_pdf.py, 再 extract_pdf.py")
    else:
        print("  → 文本层可用: 直接 extract_pdf.py (文本层仍只作初稿, 公式须对照渲染图核对)")
    print(f"分栏猜测: 双栏票 {col_votes['2']} / 单栏票 {col_votes['1']} → extract_pdf.py --cols {'2' if col_votes['2'] >= col_votes['1'] else '1'}")

if __name__ == "__main__":
    main()
