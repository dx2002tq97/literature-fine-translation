# -*- coding: utf-8 -*-
"""PDF2Zh 模式 - 查找型 translator (配合 babeldoc 的 --clitranslator)。

原理: babeldoc 用 --clitranslator 时, 把 PDF 每个文本块经 stdin 传给本脚本,
本脚本从 "Agent 精译分片" 构建的库中查找对应中文译文并输出。
=> 图文排版 100% 由 babeldoc 引擎完成(图原位/文字按原稿块位置/双栏还原 = PDF2Zh 效果),
   译文用我们自己的精译, 避开在线翻译 API。

关键机制——碎片裁切:
  双栏 PDF 的段落常被跨栏切成 2~N 个碎片块。若对碎片返回整段译文会超长→引擎缩字。
  本脚本定位碎片在段落中的位置比例, 返回译文的对应片段(按标点修正断点),
  使每个碎片块都有长度相当的中文, 全中文且不缩字。

用法:
  pdf2zh_next.exe --clitranslator \
    --clitranslator-command "python pdf2zh_cli_lookup.py --frags <分片目录>" \
    --lang-in en --lang-out zh-CN <原稿.pdf>
产物: <原名>.zh-CN.dual.pdf (左原稿/右译文) + .mono.pdf (纯译文)

注意:
- babeldoc 传入文本带 {vN} 占位符(公式/下标/引用受保护), 归一化须去掉且去数字。
- 极短块(norm<20, 标题/作者/残句)保留原文, 防误配缩字。
- 引擎收尾常报 SubprocessCrashError -15, 但 dual/mono PDF 已生成, 以产物为准。
"""
import sys, re, glob, os, html, argparse
from difflib import SequenceMatcher

PUNCTS = "。，；：、）】！？”"


def norm(s):
    s = re.sub(r"\{v\d+\}", "", s)
    s = s.replace("-\n", "").replace("— ", "").replace("- ", "")
    s = html.unescape(re.sub(r"<[^>]+>", "", s))
    return re.sub(r"[^a-z]", "", s.lower())  # 去数字: babeldoc 把下标数字抽成占位符


def build_lib(fragdir):
    lib = []
    for f in glob.glob(os.path.join(fragdir, "frag_body*.html")):
        t = open(f, encoding="utf-8").read()
        for m in re.finditer(
            r'<div class="pair">\s*<div class="en">(.*?)</div>\s*<div class="zh">(.*?)</div>\s*</div>',
            t, re.S,
        ):
            en, zh = m.group(1), m.group(2)
            key = norm(en)
            zhc = re.sub(r"<[^>]+>", "", zh).strip()
            if len(key) > 8 and zhc:
                lib.append((key, zhc))
    return lib


def slice_zh(key, k, zh):
    """碎片裁切: 定位 key 在段落 k 中的位置比例, 返回译文 zh 的对应片段(标点修正)。"""
    head = key[:24]
    s = k.find(head)
    if s < 0:
        s = 0
    tail = key[-24:] if len(key) > 24 else key
    e = k.find(tail, s)
    if e < 0:
        e = min(s + len(key), len(k))
    else:
        e += len(tail)
    kl = max(len(k), 1)
    zs, ze = int(s / kl * len(zh)), min(int(e / kl * len(zh)), len(zh))
    # 起点后移到标点后(避免从词中间开始)
    for i in range(zs, max(zs - 16, 1), -1):
        if zh[i - 1] in PUNCTS:
            zs = i
            break
    # 终点延到标点(避免断在词中间)
    for i in range(min(ze, len(zh) - 1), min(ze + 16, len(zh))):
        if zh[i] in PUNCTS:
            ze = i + 1
            break
    return zh[zs:ze].strip()


def lookup(text, lib):
    """极短块保留原文; 其余块两级匹配:
    1) 子串定位: 块开头是某段落的子串 → 碎片块, 按位置比例裁切该段译文;
    2) 整段相似: SequenceMatcher ≥0.5 → 返回整段译文。
    全中文且长度与英文块相当(不缩字)。"""
    key = norm(text)
    if len(key) < 20:
        return text  # 标题/作者/残句: 保留原文
    # 1) 碎片检测: 块开头(40字符)是某段落 k 的子串
    head = key[:40]
    if len(head) >= 15:
        cands = [(k, zh) for k, zh in lib if head in k]
        if cands:
            tail = key[-40:] if len(key) > 40 else key
            best = None
            for k, zh in cands:  # 结尾也能定位的候选更精确
                if tail in k:
                    best = (k, zh)
                    break
            if best is None:
                best = cands[0]
            k, zh = best
            if len(key) >= len(k) * 0.85:
                return zh  # 几乎整段
            piece = slice_zh(key, k, zh)
            if piece:
                return piece
    # 2) 整段相似度匹配
    best, score = None, 0.0
    probe = key[:150]
    for k, zh in lib:
        m = min(len(probe), len(k))
        if m < 12:
            continue
        r = SequenceMatcher(None, probe[:m], k[:m]).ratio()
        if r > score:
            score, best = r, (k, zh)
    if score >= 0.5 and best:
        k, zh = best
        if len(key) >= len(k) * 0.85:
            return zh
        piece = slice_zh(key, k, zh)
        if piece:
            return piece
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frags", required=True, help="精译分片目录(含 frag_body*.html)")
    args = ap.parse_args()
    lib = build_lib(args.frags)
    print(lookup(sys.stdin.read(), lib))


if __name__ == "__main__":
    main()
