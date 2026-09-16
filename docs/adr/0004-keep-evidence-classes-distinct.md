---
status: accepted
date: 2026-09-16
---

# Keep Evidence Classes Distinct

The system distinguishes `SYSTEM_FACT`, `SOURCE_DERIVED_METRIC`, `OBSERVED_SIGNAL`, `HUMAN_REPORT`, and `AI_INFERENCE`, while recording business domain separately. A source-computed metric is not a raw fact, and an AI inference must never be silently promoted to `SYSTEM_FACT`; this prevents source analysis and model interpretation from becoming false historical truth. See [Foundation #10](https://github.com/linhaicue/nice-salon/issues/10) and [CONTEXT.md](../../CONTEXT.md).