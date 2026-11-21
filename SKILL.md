---
name: literature-fine-translation
description: "英语文献精细翻译（科研精读向）。当用户给出英文文献 PDF/论文并要求「精细翻译」「双语对照」「双栏对照翻译」「文献精读翻译」「结构化摘要」时使用。区别于机器批量翻译：由 Agent 逐段精读精译，术语与缩写译后括号保留原文，图形不译保持原位，产出左右双栏对照排版与结构化中文摘要。触发词：精细翻译、双语对照、双栏对照、翻译这篇文献、文献精读、结构化摘要。"
agent_created: true
user-invocable: true
---

# 英语文献精细翻译（Literature Fine Translation）

## 定位

面向科研精读的**逐段精译**，不是机器批量直译。核心产出两件：

1. **双栏对照排版**——左栏英文原文不变，右栏中文译文与原文排版一致
2. **结构化中文摘要**——可直接用于后续研究引用

## 何时使用

- 用户给出英文文献 PDF/论文，要求精细翻译、双语对照、双栏对照、精读翻译
- 用户要求产出文献的结构化中文摘要

**不适用**：日常句子/邮件翻译（直接译）；工程图纸原位替换类任务（属其他 skill 域）；只需快速了解大意（直接读 PDF 摘要即可）。

## 翻译原则（硬约束）

1. **准确严谨第一**：宁可直译不发挥；不增不删原文信息；长难句可拆分但逻辑关系必须保真。
2. **术语与缩写**：译后以括号保留原文——如「击穿判据（breakdown criterion）」「监督学习（supervised learning）」。全文统一，以 `references/glossary.md` 为准；新术语翻译时登记入表。
3. **图形不译**：图片、曲线图、示意图、照片一律不翻译、不改画，保持原位置与原排版；图注文字需译（同样括号保留关键术语）。
4. **公式与符号**：公式保留原编号与原排版，公式内文字（变量说明）随正文处理。
5. **排版一致**：右栏译文的段落划分、标题层级、列表、图表位置与左栏原文逐一对应。

## 工作流

1. **体检定路线**：运行 `scripts/probe_pdf.py <pdf>`——判断文本层/分栏/图片，决定路线：文本层可用 → 直接 extract；纯扫描件 → 先 `scripts/ocr_pdf.py` 再 extract。
2. **读取与解析**：运行 `scripts/extract_pdf.py <pdf> --out <目录> --cols <probe 建议>`，得到左右栏文本块、块坐标 JSON 与整页渲染图。文本层只作初稿，公式/上标引文/化学式必须对照渲染图人工核对后落稿（用 `scripts/crop_region.py` 按坐标裁高清裁片）。
2. **建术语初表**：通读标题/摘要，把核心术语按 `references/glossary.md` 格式先登记，再动笔。
3. **逐段精译**：按章节顺序翻译；每译完一节自查术语一致性。篇幅长时分批进行，避免上下文丢失导致前后术语漂移。译文写入 `frag_body*.html` 分片（左英右中配对结构，见 `scripts/build_bilingual.py` 头注）。
4. **双栏排版**：运行 `scripts/build_bilingual.py --frags <分片目录> --out-html <成品.html> --out-pdf <成品.pdf>`；脚本自动内嵌图片为 base64（HTML 自包含）并调用 Edge 无头打印出 PDF。文献中的原理图/机制图/数据表若需单独取用：`export_figures.py`（电子版矢量导出）、`crop_region.py + trace_vector.py`（扫描版描摹）、`extract_tables.py`（表格 → CSV）。
5. **结构化摘要**（见下）。
6. **校对收尾**：运行 `scripts/check_pairs.py <分片目录>`（配对数/标签配平/图片存在/公式编号连续/占位符残留，退出码把关）；再抽查 3-5 处术语是否前后一致、有无漏段；渲染 PDF 首末页与图表页视检。

## 环境依赖（首次安装时按本机实际情况填写）

| 项 | 要求 | 示例 |
|---|---|---|
| Python + PyMuPDF | `pip install pymupdf` | 系统 `python` |
| OCR（可选，纯扫描件兑底） | Tesseract ≥ 5，记录绝对路径 | `C:/Program Files/Tesseract-OCR/tesseract.exe` |
| HTML→PDF | Edge 或 Chrome 无头打印 | Edge 安装目录下的 `msedge.exe` |
| 图形裁剪 | PyMuPDF `get_pixmap(dpi=200, clip=rect)`，坐标来自 `blocks_p<n>.json` 与渲染图目测 | — |

若所在平台有 builtin 的 PDF 阅读能力，纯阅读/问答类任务可走之；本 skill 的翻译流程用 PyMuPDF 直控以保证坐标与图形处理能力。

## 结构化摘要模板

按以下条目组织，条理清晰，服务于后续研究引用：

1. **研究背景与目的**——为什么做、要解决什么问题
2. **核心判据及其物理机制**——判据的表达式/表述、物理图像
3. **理论或实验方法**——建模/推导/实验手段与条件
4. **关键参数与主要结论**——数值、适用范围、验证结果
5. **适用条件与局限性**——判据在什么条件下成立、哪里会失效

## 校对清单（交付前逐项过）

1. **术语一致性**：同一术语全文译名统一；首现处括号保留原文；与 `references/glossary.md` 无冲突
2. **段落完整性**：原文每段都有对应译文；跨栏/跨页合并段两端都要译到
3. **公式核对**：每条公式与扫描页裁片逐一比对（箭头、上下标、电荷符号、积分限、系数）
4. **引文上标**：superscript 编号与扫描页一致（OCR 常丢/错）
5. **图形未动**：图表、照片未翻译未改画；位置与原文对应；图注已译且标「译注」的补充说明清晰
6. **页界标注**：原文页码分隔线完整
7. **成品视检**：PDF 首末页 + 图表页渲染抽查；预览环境图形可见（图片须已内嵌）

## 进化机制

用户的翻译习惯、排版偏好、摘要要求，记录到 `references/user-habits.md`（含日期）；反复出现、已稳定的要求上提到本文件对应小节。术语沉淀到 `references/glossary.md`。

## Resources（工具箱十件套）

- `scripts/probe_pdf.py`——体检：文本层/分栏/图片 → 决定处理路线
- `scripts/extract_pdf.py`——解析：分栏文本块、块坐标 JSON、整页渲染图
- `scripts/crop_region.py`——按坐标裁高清区域（公式/图表核对与嵌入）
- `scripts/ocr_pdf.py`——纯扫描件 OCR 兜底（tesseract）
- `scripts/export_figures.py`——图表导出：矢量区域聚类 → 矢量 PDF/SVG + 高清 PNG
- `scripts/trace_vector.py`——位图描摹矢量化：扫描版原理图/曲线图 → SVG 线稿（opencv）
- `scripts/extract_tables.py`——数据表提取：线段网格重建 → CSV/Markdown（扫描版提示 OCR 路线）
- `scripts/build_bilingual.py`——分片组装 + 图片内嵌 + Edge 打印 PDF
- `scripts/check_pairs.py`——交付前校验：配对/标签/图片/公式编号/占位符
- `scripts/draw_schematic.py`——参数化科研示意图生成：结构化分层 SVG（语义 g 层/注释/虚线可控，Inkscape/Illustrator 可编辑）；图元库持续扩充（现支持 cylinder）
- `references/glossary.md`——术语表（英文 | 中文 | 缩写 | 备注），跨文献累积
- `references/user-habits.md`——用户习惯与要求日志
