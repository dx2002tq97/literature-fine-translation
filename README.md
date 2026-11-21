# Literature Fine Translation（文献精细翻译 Skill）

面向科研精读的英文文献**逐段精译** WorkBuddy Skill——不是机器批量直译流水线，而是一套由 Agent 执行的「解析 → 核对 → 精译 → 双栏排版 → 结构化摘要」完整工作流。

## 特性

- **逐段精译**：译文由 Agent 直接产出，不调用任何外部翻译 API / 翻译引擎；准确严谨优先，不增不删原文信息
- **双栏对照排版**：左栏英文原文、右栏中文译文逐段配对，输出自包含 HTML 与 A4 PDF（Edge 无头打印）
- **术语一致**：术语与缩写译后括号保留原文（如「击穿判据（breakdown criterion）」），跨文献术语表持续沉淀
- **图形保真**：图片、曲线图、表格不翻译，按原位置以裁剪图嵌入；公式保留原编号，必须与扫描页裁片逐一核对
- **扫描件可靠**：文本层只作初稿，公式/上标引文/化学式强制对照渲染图人工核对；纯扫描件可走 Tesseract OCR 兜底
- **可进化**：用户习惯记录进 `references/user-habits.md`，稳定条款上提 SKILL.md；术语沉淀进 `references/glossary.md`
- **结构化摘要**：背景目的 / 核心判据及物理机制 / 方法 / 关键参数与结论 / 适用条件与局限，五条目模板

## 目录结构

```
literature-fine-translation/
├── SKILL.md                      # 工作流、翻译原则、校对清单、环境依赖
├── scripts/
│   ├── extract_pdf.py            # PDF 解析：分栏文本块 + 块坐标 JSON + 整页渲染图
│   └── build_bilingual.py        # 分片组装 + 图片内嵌 base64 + Edge 打印 PDF
└── references/
    ├── glossary.md               # 术语表（英文 | 中文 | 缩写 | 备注），随使用积累
    └── user-habits.md            # 用户习惯日志（空模板，随使用填充）
```

## 安装

复制到 WorkBuddy 用户 skill 目录：

```
~/.workbuddy/skills/literature-fine-translation/
```

## 依赖

| 用途 | 组件 |
|---|---|
| PDF 解析与图形裁剪 | Python + PyMuPDF（`pip install pymupdf`） |
| 扫描件 OCR 兜底 | Tesseract（可选，路径写进 SKILL.md 环境表即可） |
| HTML → PDF | Edge / Chrome 无头打印（`--headless --print-to-pdf`） |

具体路径按本机情况填入 SKILL.md 的「环境依赖」表。

## 工作流概要

1. `extract_pdf.py` 解析 PDF（分栏文本、坐标、渲染图）
2. 建/载术语表
3. 逐段精译（写入 `frag_body*.html` 分片）
4. `build_bilingual.py` 组装 + 出 PDF
5. 结构化摘要
6. 按校对清单逐项质检后交付

## 适用范围

- 学术论文、技术报告等英文文献的精读级翻译
- 不适用：日常句子/邮件翻译；工程图纸原位替换；快速浏览大意
