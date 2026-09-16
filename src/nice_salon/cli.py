from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .store import FoundationStore


def _database_path() -> Path:
    return Path(os.environ.get("NICE_SALON_DB", ".local/foundation.sqlite3"))


def main() -> int:
    parser = argparse.ArgumentParser(prog="nice-salon")
    subparsers = parser.add_subparsers(dest="command", required=True)
    ingest = subparsers.add_parser("ingest", help="ingest one selected page-captured Meiguanjia record")
    ingest.add_argument("capture", type=Path)
    trace = subparsers.add_parser("trace", help="show the current fact and its raw source evidence")
    trace.add_argument("source_record_id")
    customer = subparsers.add_parser("customer", help="show a customer current fact view")
    customer.add_argument("source_customer_id")
    employee = subparsers.add_parser("employee", help="show an employee current fact view")
    employee.add_argument("source_employee_id")
    args = parser.parse_args()

    store = FoundationStore(_database_path())
    if args.command == "ingest":
        capture = json.loads(args.capture.read_text(encoding="utf-8"))
        result = store.ingest_capture(capture)
    elif args.command == "trace":
        result = store.trace(args.source_record_id)
    elif args.command == "customer":
        result = store.customer_current_view(args.source_customer_id)
    else:
        result = store.employee_current_view(args.source_employee_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
