# -*- coding: utf-8 -*-
"""PDF2Zh 模式 - 查找型 translator (配合 babeldoc 的 --clitranslator)。

原理: babeldoc 用 --clitranslator 时, 把 PDF 每个文本块经 stdin 传给本脚本,
本脚本从 "Agent 精译分片" 构建的库中查找对应中文译文并输出。
=> 排版 100% 由 babeldoc 引擎完成(完美还原原稿版式/位置), 译文用我们自己的精译,
   避开在线翻译 API(不稳定/违背用户红线)。

用法(在目标机, 需已装 pdf2zh_next/babeldoc):
  pdf2zh_next.exe --clitranslator \
    --clitranslator-command "python pdf2zh_cli_lookup.py --frags <分片目录>" \
    --lang-in en --lang-out zh-CN <原稿.pdf>
产物: <原名>.zh-CN.dual.pdf (左原稿/右译文) + .mono.pdf (纯译文)

注意:
- babeldoc 传给 stdin 的文本带 {vN} 占位符(公式/下标/引用被保护), 归一化时须去掉。
- 双栏 PDF 会被切成左右栏碎片, 段落级译文匹配率下降; 单栏 PDF 匹配率高。
- 未命中的块返回原文(英文), 保证不乱码。标题/作者等短块建议返回原文或单独补译。
- 引擎收尾常报 SubprocessCrashError -15, 但 dual/mono PDF 已生成, 以产物为准。
"""
import sys, re, glob, os, html, argparse
from difflib import SequenceMatcher


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


def lookup(text, lib):
    key = norm(text)
    if len(key) < 6:
        return text
    best, score = None, 0.0
    probe = key[:150]
    for k, zh in lib:
        m = min(len(probe), len(k))
        if m < 8:
            continue
        r = SequenceMatcher(None, probe[:m], k[:m]).ratio()
        if r > score:
            score, best = r, zh
    if score >= 0.5:
        return best
    for k, zh in lib:
        if len(k) > 20 and (k[:30] in key or key[:30] in k):
            return zh
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frags", required=True, help="精译分片目录(含 frag_body*.html)")
    args = ap.parse_args()
    lib = build_lib(args.frags)
    print(lookup(sys.stdin.read(), lib))


if __name__ == "__main__":
    main()
