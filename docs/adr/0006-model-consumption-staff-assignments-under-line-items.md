---
status: accepted
date: 2026-09-16
---

# Model Staff Assignments Under Consumption Line Items

A real Meiguanjia bill showed a consumed project associated with two employees, with distinct roles and designated/non-designated semantics. Therefore, the minimum canonical relationship must allow `Transaction / Consumption Record → LineItem[] → StaffAssignment[]`; a single transaction-level `employee_id` cannot represent the observed fact. This decision captures only the observed relationship shape, not a complete persisted schema, revenue-allocation rule, cancellation model, or proof that a consumption record means service completion. See the evidence and caveats in [foundation-slice-1-report.md](../research/foundation-slice-1-report.md) and [Foundation #10](https://github.com/linhaicue/nice-salon/issues/10).