# Changelog

本 skill 遵循「用户习惯驱动进化」：行为变更记录于 `references/user-habits.md`，稳定条款上提 SKILL.md。对外版本号在此记录。

## [1.0.0] - 2026-11-22

### Added
- SKILL.md：完整工作流（解析 → 术语表 → 逐段精译 → 双栏排版 → 结构化摘要 → 校对清单）、翻译硬约束、环境依赖表
- `scripts/extract_pdf.py`：PDF 分栏解析（文本块、坐标 JSON、整页渲染图）
- `scripts/build_bilingual.py`：分片组装、图片内嵌 base64、Edge 无头打印 PDF
- `references/glossary.md`：跨文献术语表（空模板，随使用积累）
- `references/user-habits.md`：用户习惯进化日志模板
- 首次端到端实战验证：6 页双栏扫描版期刊论文，含 23 条公式与 3 处图表，全文双语对照 + 结构化摘要
