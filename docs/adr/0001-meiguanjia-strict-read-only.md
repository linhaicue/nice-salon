---
status: accepted
date: 2026-09-16
---

# Meiguanjia Is Strictly Read-Only

This project may read Meiguanjia through an authorized session, but it must never create, modify, delete, send, or save business records or configuration there. We choose read-only access over write-back automation so AI assistance cannot directly mutate the salon's system of record; people remain responsible for real business actions. See [Master Map #1](https://github.com/linhaicue/nice-salon/issues/1) and [Foundation #10](https://github.com/linhaicue/nice-salon/issues/10).