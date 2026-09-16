from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
from zoneinfo import ZoneInfo


SHOP_TIMEZONE = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True)
class IdentityRef:
    entity_type: str
    source_id: str
    canonical_id: str
    display_label: str | None
    confidence: str = "confirmed"


@dataclass(frozen=True)
class StaffAssignment:
    employee: IdentityRef
    source_assignment_id: str | None
    role_label: str | None
    designation_label: str | None


@dataclass(frozen=True)
class LineItem:
    position: int
    source_line_id: str | None
    service: IdentityRef
    displayed_amount: Decimal
    staff_assignments: tuple[StaffAssignment, ...]


@dataclass(frozen=True)
class ConsumptionRecord:
    source_system: str
    source_domain: str
    source_record_id: str
    source_primary_key: str
    canonical_id: str
    source_recorded_at: datetime
    posted_amount: Decimal
    customer: IdentityRef
    line_items: tuple[LineItem, ...]
    source_updated_at: datetime | None
    source_url: str
    fetched_at: datetime
    raw_payload: dict
    capture_context: dict
    redacted_fields: tuple[str, ...]
    evidence_class: str = "SYSTEM_FACT"


def _required_string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be a non-empty string")
    return value.strip()


def _money(value: object, path: str) -> Decimal:
    try:
        amount = Decimal(_required_string(value, path))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{path} must be a valid decimal amount") from exc
    if not amount.is_finite():
        raise ValueError(f"{path} must be finite")
    return amount.quantize(Decimal("0.01"))


def _datetime(value: object, path: str, *, allow_none: bool = False) -> datetime | None:
    if value is None and allow_none:
        return None
    raw = _required_string(value, path)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        try:
            parsed = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
        except ValueError as exc:
            raise ValueError(f"{path} must be an ISO timestamp or YYYY-MM-DD HH:MM:SS") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=SHOP_TIMEZONE)
    return parsed


def _identity(entity_type: str, source_id: object, display_label: object = None) -> IdentityRef:
    clean_id = _required_string(source_id, f"{entity_type}.source_id")
    label = display_label.strip() if isinstance(display_label, str) and display_label.strip() else None
    return IdentityRef(
        entity_type=entity_type,
        source_id=clean_id,
        canonical_id=f"meiguanjia:{entity_type}:{clean_id}",
        display_label=label,
    )


def parse_page_capture(capture: dict, *, now: datetime | None = None) -> ConsumptionRecord:
    """Normalize one selected bill row from the read-only page capture format."""
    if capture.get("source_system") != "meiguanjia":
        raise ValueError("source_system must be meiguanjia")
    if capture.get("source_domain") != "transaction_consumption":
        raise ValueError("source_domain must be transaction_consumption")
    parsed_url = urlparse(_required_string(capture.get("source_url"), "source_url"))
    if parsed_url.hostname != "vip3.meiguanjia.net" or not parsed_url.path.endswith("/shair/bill!bill.action"):
        raise ValueError("source_url must be the observed Meiguanjia 项目消费 page")

    captured_at = _datetime(capture.get("captured_at"), "captured_at") if capture.get("captured_at") else now
    if captured_at is None:
        raise ValueError("captured_at or now is required")
    page = capture.get("page")
    if not isinstance(page, dict) or page.get("selected_record_only") is not True:
        raise ValueError("page metadata must identify a selected record capture")
    if page.get("complete") is not True:
        raise ValueError("capture page is incomplete; refusing to ingest a potentially stale page")
    visible_count = page.get("visible_record_count")
    source_total = page.get("source_total_count")
    if not isinstance(visible_count, int) or not isinstance(source_total, int) or visible_count != source_total:
        raise ValueError("visible row count must match the source result count for this capture")

    query = capture.get("query")
    if not isinstance(query, dict):
        raise ValueError("query date range is required")
    start_value = query.get("start_date")
    end_value = query.get("end_date")
    if bool(start_value) != bool(end_value):
        raise ValueError("query date range must include both dates, or neither")
    start_date = _required_string(start_value, "query.start_date") if start_value else None
    end_date = _required_string(end_value, "query.end_date") if end_value else None

    records = capture.get("records")
    if not isinstance(records, list) or len(records) != 1:
        raise ValueError("capture must contain exactly one selected source record")
    row = records[0]
    source_record_id = _required_string(row.get("source_record_id"), "source_record_id")
    selected_bill = _required_string(page.get("selected_bill_number"), "page.selected_bill_number")
    if source_record_id != selected_bill:
        raise ValueError("selected bill number does not match the captured row")

    recorded_at = _datetime(row.get("source_recorded_at"), "source_recorded_at")
    assert recorded_at is not None
    recorded_day = recorded_at.date().isoformat()
    if start_date and end_date and not start_date <= recorded_day <= end_date:
        raise ValueError("captured row timestamp is outside the selected date range")

    customer = _identity("customer", row.get("customer_source_id"))
    line_rows = row.get("line_items")
    if not isinstance(line_rows, list) or not line_rows:
        raise ValueError("at least one line item is required")
    line_items: list[LineItem] = []
    for position, item in enumerate(line_rows, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"line_items[{position - 1}] must be an object")
        service = _identity("service", item.get("source_service_id"), item.get("service_label"))
        staff_rows = item.get("staff_assignments")
        if not isinstance(staff_rows, list) or not staff_rows:
            raise ValueError(f"line_items[{position - 1}] must retain its visible staff assignments")
        assignments = tuple(
            StaffAssignment(
                employee=_identity("employee", staff.get("source_employee_id"), staff.get("display_label")),
                source_assignment_id=(str(staff["source_assignment_id"]) if staff.get("source_assignment_id") else None),
                role_label=(str(staff["role_label"]).strip() if staff.get("role_label") else None),
                designation_label=(str(staff["designation_label"]).strip() if staff.get("designation_label") else None),
            )
            for staff in staff_rows
        )
        line_items.append(
            LineItem(
                position=position,
                source_line_id=(str(item["source_line_id"]) if item.get("source_line_id") else None),
                service=service,
                displayed_amount=_money(item.get("amount_displayed"), f"line_items[{position - 1}].amount_displayed"),
                staff_assignments=assignments,
            )
        )

    raw_payload = {
        "source_record_id": source_record_id,
        "source_primary_key": _required_string(row.get("source_primary_key"), "source_primary_key"),
        "source_recorded_at": _required_string(row.get("source_recorded_at"), "source_recorded_at"),
        "customer_source_id": customer.source_id,
        "posted_amount_displayed": _required_string(row.get("posted_amount_displayed"), "posted_amount_displayed"),
        "line_items": line_rows,
        "source_updated_at": row.get("source_updated_at"),
        "redacted_fields": sorted(set(row.get("redacted_fields", []))),
    }
    capture_context = {
        "method": _required_string(capture.get("capture_method"), "capture_method"),
        "query": {
            "start_date": start_date,
            "end_date": end_date,
            "date_range_verified": bool(start_date and end_date),
        },
        "page": {
            "visible_record_count": visible_count,
            "source_total_count": source_total,
            "complete": True,
            "selected_record_only": True,
        },
    }
    return ConsumptionRecord(
        source_system="meiguanjia",
        source_domain="transaction_consumption",
        source_record_id=source_record_id,
        source_primary_key=_required_string(row.get("source_primary_key"), "source_primary_key"),
        canonical_id=f"meiguanjia:transaction:{source_record_id}",
        source_recorded_at=recorded_at,
        posted_amount=_money(row.get("posted_amount_displayed"), "posted_amount_displayed"),
        customer=customer,
        line_items=tuple(line_items),
        source_updated_at=_datetime(row.get("source_updated_at"), "source_updated_at", allow_none=True),
        source_url=_required_string(capture.get("source_url"), "source_url"),
        fetched_at=captured_at,
        raw_payload=raw_payload,
        capture_context=capture_context,
        redacted_fields=tuple(raw_payload["redacted_fields"]),
    )
