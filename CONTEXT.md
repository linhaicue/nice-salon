# Project Context: Enterprise AI for a Hair Salon

This project explores how a real operating business can become AI-enabled by improving its recurring decision and work loops. The hair salon is the first real business used to test the approach; the project is not scoped as a churn-prediction product or a replacement for Meiguanjia.

## Goal and operating model

The long-term goal is to shorten and improve the business feedback loop:

```text
SENSE → UNDERSTAND → DECIDE → ACT → MEASURE → LEARN
```

AI should help people notice meaningful changes, connect evidence across the business, make better decisions, coordinate work, and learn from outcomes. A feature is valuable only when it improves a real business outcome. People remain responsible for business decisions and actions.

## Tracks and current pins

**Wayfinder Track — D1 OPEN**: choose the first real business decision loop worth augmenting with AI. No candidate is selected yet. C2 (appointment → arrival → service → rebooking) is unsuitable for the current operating workflow because the shop does not use Meiguanjia appointments or SMS as a regular process. C4 (demand × capacity mismatch) remains unproven; workflow reality is UNKNOWN. Do not turn a candidate into a product design before its real workflow is established.

**Foundation Track — #10 OPEN, parallel with D1**: build only the smallest durable foundation that does not depend on the selected D1 scenario. Current pin is Slice 1:

```text
real Meiguanjia consumption record
→ authenticated, read-only page acquisition
→ Raw Evidence + provenance
→ evidence classification
→ minimal canonical record
→ customer / employee / service identity links
→ sync state and freshness
→ current fact views
```

Slice 1 is a mechanism proof, not the final data-coverage target. After it passes, stop and return to Wayfinder; do not automatically start a full source sweep.

## Sources and coverage

Meiguanjia is currently the most important structured business source. It is one view of the business, not the whole business and not necessarily the only future source. The long-term target is systematic coverage of Meiguanjia data that is both meaningful to business and readable under the authorized account. Coverage is incremental and excludes copying every UI element, irrelevant log, or duplicate report. Other sources such as WeChat/WeCom and external platforms remain future sources until separately scoped.

Meiguanjia is **strictly read-only** for this project. Do not create, modify, delete, send, or save business data or configuration there. Do not rebuild reports that Meiguanjia already provides merely to reproduce them; future AI value is expected from useful cross-domain understanding and assistance with real work.

## Evidence language and truth boundaries

Keep these evidence classes distinct:

- `SYSTEM_FACT`: a business record or state explicitly recorded by an operational source.
- `SOURCE_DERIVED_METRIC`: an analysis computed by a source system; retain its source attribution and do not present it as a raw fact.
- `OBSERVED_SIGNAL`: a signal from behavior, conversation, review, or another observation source.
- `HUMAN_REPORT`: information reported by a person, with context and source retained where available.
- `AI_INFERENCE`: a model-generated interpretation or hypothesis.

Use the broader distinction `FACT ≠ DERIVED ≠ INFERENCE`. Never silently promote an inference to a fact. A Meiguanjia transaction/consumption record does not by itself prove physical arrival or completed service.

Identity links must preserve confidence: `confirmed`, `probable`, or `unknown`. Do not force-match a person across sources when evidence is insufficient. Keep source IDs and provenance so a current view can be traced to its evidence.

## Current canonical evidence

The domain term is **Transaction / Consumption Record**: a source-recorded consumption entry that does not by itself establish physical arrival or completed service. The first real water-bill sample showed one consumed project associated with multiple employees, with role and designated/non-designated distinctions. The minimum relationship shape currently recorded is:

```text
Transaction / Consumption Record
└── LineItem[]
    └── StaffAssignment[]
```

This expresses an observed relationship; it is not a complete or implemented database schema. Do not infer service completion, staff revenue allocation, cancellation semantics, or other unobserved details from this shape.

## Verified evidence and open questions (2026-09-16)

- #11 research is **closed with a decision**: v0 Source Contract is authenticated page-level read through the logged-in Meiguanjia UI. The date range, page-level pagination, repeat reads, and visible record IDs had positive evidence. The shop was open during same-day sampling, so the record count naturally increased.
- The internal POST body and low-level pagination parameters remain unknown and are non-blocking; do not replay internal requests outside the page.
- Slice implementation still must prove the query-completion event hook, explicit empty-result behavior, and completeness when business data changes during a multi-page scan.
- Raw Evidence persistence, sync/change semantics, freshness, canonical persistence, identity mapping, and current views have not yet been implemented or accepted.
- D1 evidence is incomplete: C4 workflow reality is UNKNOWN. Do not fill gaps with invented examples.

The current source of status and next work is [Master Map #1](https://github.com/linhaicue/nice-salon/issues/1), [Foundation #10](https://github.com/linhaicue/nice-salon/issues/10), and [Slice 1 research #11](https://github.com/linhaicue/nice-salon/issues/11). The research evidence is in [foundation-slice-1-report.md](./docs/research/foundation-slice-1-report.md). Accepted architectural rationale is in [docs/adr](./docs/adr/).

## Hard boundaries

- Keep the Master Map frozen unless new evidence challenges a top-level assumption.
- Keep D1 open until a real, measurable, actionable business loop is selected.
- Do not design full schemas, Store State, signal/finding/action engines, operating memory, or multiple agents ahead of evidence and a validated loop.
- Raw evidence, source-derived results, deterministic derivations, human reports, and AI inferences remain distinguishable and traceable.
- Build only what the current pin requires; a long-term coverage goal is not permission to implement every domain now.

Update this context when an accepted decision, verified evidence, or current pin changes. Use GitHub issues for active scope and work; use `docs/research/` for evidence; use ADRs for durable decisions and their rationale.