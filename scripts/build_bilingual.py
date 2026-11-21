#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""组装双语对照 HTML 并转 PDF——文献精细翻译第 4 步。

用法:
    python build_bilingual.py --frags <分片目录> --out-html <成品.html> [--out-pdf <成品.pdf>]

约定:
    - 分片按文件名排序拼接：frag_head.html（含 <style>、标题区）、frag_body*.html（正文）、
      frag_tail.html（可选，收尾）。最后自动补 </body></html>（若分片未含）。
    - 分片中相对路径的 <img src="build/xxx.png"> 会解析为绝对 file 路径；
      --inline-imgs（默认开）时内嵌为 base64，使 HTML 自包含、任何预览环境图形可见。
    - PDF 由 Edge 无头打印生成（A4，@page 边距由 frag_head 的 CSS 控制）。
"""
import argparse, base64, glob, os, subprocess, sys
from pathlib import Path
from urllib.parse import quote

EDGE_CANDIDATES = [
    r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    r"C:/Program Files/Microsoft/Edge/Application/msedge.exe",
]

def find_edge():
    for p in EDGE_CANDIDATES:
        if os.path.exists(p):
            return p
    raise SystemExit("未找到 msedge.exe，请把本机 Edge 路径加入 EDGE_CANDIDATES")

def resolve_img(src: str, base: Path) -> Path | None:
    p = Path(src)
    if not p.is_absolute():
        p = (base / src).resolve()
        if not p.exists():
            p2 = Path.cwd() / src
            if p2.exists():
                return p2
    return p if p.exists() else None

def inline_imgs(html: str, base: Path) -> str:
    import re
    def repl(m):
        src = m.group(1)
        if src.startswith("data:"):
            return m.group(0)
        p = resolve_img(src, base)
        if not p:
            print(f"警告: 图片缺失 {src}")
            return m.group(0)
        mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
        data = base64.b64encode(p.read_bytes()).decode()
        return f'src="data:{mime};base64,{data}"'
    return re.sub(r'src="([^"]+)"', repl, html)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frags", required=True)
    ap.add_argument("--out-html", required=True)
    ap.add_argument("--out-pdf")
    ap.add_argument("--no-inline-imgs", action="store_true")
    args = ap.parse_args()

    frags_dir = Path(args.frags)
    parts = sorted(glob.glob(str(frags_dir / "frag_*.html")))
    if not parts:
        raise SystemExit(f"{frags_dir} 下没有 frag_*.html 分片")
    html = "".join(Path(p).read_text(encoding="utf-8") for p in parts)
    if "</body>" not in html:
        html += "\n</body>\n</html>\n"

    if not args.no_inline_imgs:
        html = inline_imgs(html, frags_dir)

    out_html = Path(args.out_html)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    if args.out_pdf:
        Path(args.out_pdf).parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html, encoding="utf-8")
    print(f"html -> {out_html} ({out_html.stat().st_size/1024:.0f} KB)")

    if args.out_pdf:
        edge = find_edge()
        uri = out_html.resolve().as_uri()
        out_pdf = str(Path(args.out_pdf).resolve())
        r = subprocess.run(
            [edge, "--headless", "--disable-gpu", "--no-pdf-header-footer",
             f"--print-to-pdf={out_pdf}", uri],
            capture_output=True, text=True, timeout=120)
        if Path(out_pdf).exists():
            print(f"pdf  -> {out_pdf} ({Path(out_pdf).stat().st_size/1024:.0f} KB)")
        else:
            print("pdf 生成失败：", r.stderr[-500:] if r.stderr else r.stdout[-500:])
            sys.exit(1)

if __name__ == "__main__":
    main()
