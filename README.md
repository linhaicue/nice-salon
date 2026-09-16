# Nice Salon Foundation Slice 1

Minimal, local-only proof of the Foundation path for one Meiguanjia transaction / consumption record:

```text
authenticated page read → redacted raw evidence → SYSTEM_FACT → canonical relationships → current fact views
```

The Meiguanjia UI is strictly read-only. `scripts/capture_meiguanjia_bill.js` only reads the currently rendered bill table; it does not call endpoints or change source data. It returns one selected row and page-level completeness metadata. Names and phone numbers for customers, payment breakdowns, and cashier names are excluded. Runtime snapshots and the SQLite database live under `.local/`, which is git-ignored.

## Capture and ingest

1. Sign in to Meiguanjia yourself and open the `营业记录 → 水单记录 → 项目消费` page.
2. Use the page's normal date/search controls. Wait until the result summary and table footer agree. The capture script checks each visible row against the selected date range when the page exposes one, and records whether all rows for that result are visible.
3. Run the capture function against that authenticated page using the browser automation's read-only page evaluation, passing a visible bill number. Save its returned JSON under `.local/`.
4. In PowerShell:

   ```powershell
   $env:PYTHONPATH = 'src'
   python -m nice_salon ingest .local/real-bill.json
   python -m nice_salon trace X260916073849
   ```

The default database is `.local/foundation.sqlite3`; override it with `NICE_SALON_DB`. Re-ingesting the same row appends another provenance observation and reports it as `unchanged`; changed source fields create an updated current record while earlier raw evidence stays intact.

## Verify

```powershell
python -m unittest discover -s tests -v
```

The current views are deterministic queries over canonical records. A transaction / consumption record is not treated as proof of arrival or completed service. Employee revenue allocation, cancellation semantics, and missing source update timestamps are not inferred.
