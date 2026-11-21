#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交付前校验——检查翻译分片的完整性与一致性。

用法:
    python check_pairs.py <分片目录>

检查项:
    1. div 标签开闭配平
    2. .pair 行内 en/zh 单元是否一一对应(数量一致)
    3. 图片引用文件是否存在(相对分片目录解析; data: URI 视为已内嵌)
    4. 公式编号 (N) 连续性(发现跳号即警告, 供人工确认)
    5. TODO/占位符残留
退出码: 有问题非 0, 可用于交付前把关。
"""
import glob, os, re, sys

def main():
    frags = sorted(glob.glob(os.path.join(sys.argv[1], "frag_*.html")))
    if not frags:
        print("未找到 frag_*.html")
        sys.exit(1)
    html = "".join(open(f, encoding="utf-8").read() for f in frags)
    problems = []

    if html.count("<div") != html.count("</div>"):
        problems.append(f"div 不配平: <div {html.count('<div')} vs </div> {html.count('</div>')}")

    pairs = len(re.findall(r'class="pair"', html))
    en = len(re.findall(r'class="en[ "]', html)) + len(re.findall(r'class="en"', html))
    zh = len(re.findall(r'class="zh[ "]', html)) + len(re.findall(r'class="zh"', html))
    sec = len(re.findall(r'class="sec"', html))
    print(f"pair 行: {pairs}, sec 节: {sec}, en 单元: {en}, zh 单元: {zh}")
    # en/zh 数量应相等; sec 内各含一对 en/zh, 不计入 pair 检查
    if en != zh:
        problems.append(f"en/zh 单元数不等: {en} vs {zh}")

    for m in re.finditer(r'src="(?!data:)([^"]+)"', html):
        # 与 build_bilingual.py 对齐: 先相对分片目录, 再回退到当前工作目录
        cands = [os.path.join(sys.argv[1], m.group(1)), os.path.join(os.getcwd(), m.group(1))]
        if not any(os.path.exists(c) for c in cands):
            problems.append(f"图片缺失: {m.group(1)}")
    n_data = len(re.findall(r'src="data:image', html))
    print(f"图片: 内嵌 {n_data} 张, 外链 {len(re.findall(chr(115)+chr(114)+chr(99)+chr(61)+chr(34), html)) - n_data} 张")

    eqs = sorted(int(x) for x in re.findall(r"\((\d+)\)</span>", html))
    if eqs:
        gaps = [i for i in range(eqs[0], eqs[-1] + 1) if i not in eqs]
        if gaps:
            problems.append(f"公式编号缺号: {gaps}")
        else:
            print(f"公式编号: ({eqs[0]})–({eqs[-1]}) 连续")

    for kw in ["TODO", "FIXME", "占位"]:
        if kw in html:
            problems.append(f"残留占位符: {kw}")

    if problems:
        print("发现问题:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("全部通过")

if __name__ == "__main__":
    main()
