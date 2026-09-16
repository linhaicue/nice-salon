from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from .meiguanjia import ConsumptionRecord, parse_page_capture


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS raw_evidence (
    id INTEGER PRIMARY KEY,
    source_system TEXT NOT NULL,
    source_domain TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    source_updated_at TEXT,
    source_url TEXT NOT NULL,
    evidence_class TEXT NOT NULL,
    raw_payload_json TEXT NOT NULL,
    redacted_fields_json TEXT NOT NULL,
    fingerprint TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS raw_evidence_record_idx
    ON raw_evidence(source_system, source_domain, source_record_id, id);

CREATE TABLE IF NOT EXISTS identity_link (
    entity_type TEXT NOT NULL,
    source_system TEXT NOT NULL,
    source_id TEXT NOT NULL,
    canonical_id TEXT NOT NULL,
    display_label TEXT,
    confidence TEXT NOT NULL,
    PRIMARY KEY (entity_type, source_system, source_id)
);

CREATE TABLE IF NOT EXISTS transaction_record (
    canonical_id TEXT PRIMARY KEY,
    source_system TEXT NOT NULL,
    source_domain TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    source_primary_key TEXT NOT NULL,
    source_recorded_at TEXT NOT NULL,
    posted_amount TEXT NOT NULL,
    customer_canonical_id TEXT NOT NULL,
    source_updated_at TEXT,
    evidence_id INTEGER NOT NULL REFERENCES raw_evidence(id),
    fingerprint TEXT NOT NULL,
    UNIQUE(source_system, source_domain, source_record_id)
);

CREATE TABLE IF NOT EXISTS line_item (
    id INTEGER PRIMARY KEY,
    transaction_id TEXT NOT NULL REFERENCES transaction_record(canonical_id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    source_line_id TEXT,
    source_service_id TEXT NOT NULL,
    service_canonical_id TEXT NOT NULL,
    displayed_amount TEXT NOT NULL,
    UNIQUE(transaction_id, position)
);

CREATE TABLE IF NOT EXISTS staff_assignment (
    id INTEGER PRIMARY KEY,
    line_item_id INTEGER NOT NULL REFERENCES line_item(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    source_assignment_id TEXT,
    employee_canonical_id TEXT NOT NULL,
    role_label TEXT,
    designation_label TEXT,
    UNIQUE(line_item_id, position)
);

CREATE TABLE IF NOT EXISTS sync_state (
    source_system TEXT NOT NULL,
    source_domain TEXT NOT NULL,
    last_attempt_at TEXT NOT NULL,
    last_success_at TEXT NOT NULL,
    records_seen INTEGER NOT NULL,
    records_changed INTEGER NOT NULL,
    capture_scope TEXT NOT NULL DEFAULT 'unknown',
    status TEXT NOT NULL,
    last_error TEXT,
    PRIMARY KEY (source_system, source_domain)
);
"""


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _iso(value: datetime) -> str:
    return value.isoformat()


def _money(value: Decimal) -> str:
    return format(value, ".2f")


class FoundationStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.executescript(SCHEMA)
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(sync_state)")}
            if "capture_scope" not in columns:
                connection.execute("ALTER TABLE sync_state ADD COLUMN capture_scope TEXT NOT NULL DEFAULT 'unknown'")
                evidence_rows = connection.execute(
                    "SELECT source_system,source_domain,raw_payload_json FROM raw_evidence ORDER BY id DESC"
                ).fetchall()
                for evidence in evidence_rows:
                    payload = json.loads(evidence["raw_payload_json"])
                    selected_only = payload.get("capture_context", {}).get("page", {}).get("selected_record_only")
                    if selected_only is True:
                        connection.execute(
                            "UPDATE sync_state SET capture_scope='selected_record_only' WHERE source_system=? AND source_domain=?",
                            (evidence["source_system"], evidence["source_domain"]),
                        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def ingest_capture(self, capture: dict) -> dict:
        record = parse_page_capture(capture)
        return self.ingest_record(record)

    def ingest_record(self, record: ConsumptionRecord) -> dict:
        raw_json = _json({"source_record": record.raw_payload, "capture_context": record.capture_context})
        fingerprint = hashlib.sha256(_json(record.raw_payload).encode("utf-8")).hexdigest()
        fetched_at = _iso(record.fetched_at)
        result = "inserted"

        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            old = connection.execute(
                "SELECT fingerprint FROM transaction_record WHERE source_system=? AND source_domain=? AND source_record_id=?",
                (record.source_system, record.source_domain, record.source_record_id),
            ).fetchone()
            if old:
                result = "unchanged" if old["fingerprint"] == fingerprint else "updated"

            cursor = connection.execute(
                """INSERT INTO raw_evidence
                   (source_system,source_domain,source_record_id,fetched_at,source_updated_at,source_url,evidence_class,raw_payload_json,redacted_fields_json,fingerprint)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    record.source_system,
                    record.source_domain,
                    record.source_record_id,
                    fetched_at,
                    _iso(record.source_updated_at) if record.source_updated_at else None,
                    record.source_url,
                    record.evidence_class,
                    raw_json,
                    _json(record.redacted_fields),
                    fingerprint,
                ),
            )
            evidence_id = cursor.lastrowid

            identities = [record.customer]
            for line in record.line_items:
                identities.append(line.service)
                identities.extend(assignment.employee for assignment in line.staff_assignments)
            for identity in identities:
                connection.execute(
                    """INSERT INTO identity_link(entity_type,source_system,source_id,canonical_id,display_label,confidence)
                       VALUES (?,?,?,?,?,?)
                       ON CONFLICT(entity_type,source_system,source_id) DO UPDATE SET
                         display_label=COALESCE(excluded.display_label,identity_link.display_label),
                         confidence=excluded.confidence""",
                    (
                        identity.entity_type,
                        record.source_system,
                        identity.source_id,
                        identity.canonical_id,
                        identity.display_label,
                        identity.confidence,
                    ),
                )

            connection.execute(
                """INSERT INTO transaction_record
                   (canonical_id,source_system,source_domain,source_record_id,source_primary_key,source_recorded_at,posted_amount,customer_canonical_id,source_updated_at,evidence_id,fingerprint)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(canonical_id) DO UPDATE SET
                     source_primary_key=excluded.source_primary_key,
                     source_recorded_at=excluded.source_recorded_at,
                     posted_amount=excluded.posted_amount,
                     customer_canonical_id=excluded.customer_canonical_id,
                     source_updated_at=excluded.source_updated_at,
                     evidence_id=excluded.evidence_id,
                     fingerprint=excluded.fingerprint""",
                (
                    record.canonical_id,
                    record.source_system,
                    record.source_domain,
                    record.source_record_id,
                    record.source_primary_key,
                    _iso(record.source_recorded_at),
                    _money(record.posted_amount),
                    record.customer.canonical_id,
                    _iso(record.source_updated_at) if record.source_updated_at else None,
                    evidence_id,
                    fingerprint,
                ),
            )
            connection.execute("DELETE FROM line_item WHERE transaction_id=?", (record.canonical_id,))
            for line in record.line_items:
                line_cursor = connection.execute(
                    """INSERT INTO line_item(transaction_id,position,source_line_id,source_service_id,service_canonical_id,displayed_amount)
                       VALUES (?,?,?,?,?,?)""",
                    (
                        record.canonical_id,
                        line.position,
                        line.source_line_id,
                        line.service.source_id,
                        line.service.canonical_id,
                        _money(line.displayed_amount),
                    ),
                )
                for position, assignment in enumerate(line.staff_assignments, start=1):
                    connection.execute(
                        """INSERT INTO staff_assignment(line_item_id,position,source_assignment_id,employee_canonical_id,role_label,designation_label)
                           VALUES (?,?,?,?,?,?)""",
                        (
                            line_cursor.lastrowid,
                            position,
                            assignment.source_assignment_id,
                            assignment.employee.canonical_id,
                            assignment.role_label,
                            assignment.designation_label,
                        ),
                    )

            previous = connection.execute(
                "SELECT records_seen,records_changed FROM sync_state WHERE source_system=? AND source_domain=?",
                (record.source_system, record.source_domain),
            ).fetchone()
            records_seen = (previous["records_seen"] if previous else 0) + 1
            records_changed = (previous["records_changed"] if previous else 0) + (result != "unchanged")
            connection.execute(
                """INSERT INTO sync_state(source_system,source_domain,last_attempt_at,last_success_at,records_seen,records_changed,capture_scope,status,last_error)
                   VALUES (?,?,?,?,?,?,?,?,NULL)
                   ON CONFLICT(source_system,source_domain) DO UPDATE SET
                     last_attempt_at=excluded.last_attempt_at,
                     last_success_at=excluded.last_success_at,
                     records_seen=excluded.records_seen,
                     records_changed=excluded.records_changed,
                     capture_scope=excluded.capture_scope,
                     status=excluded.status,
                     last_error=NULL""",
                (
                    record.source_system,
                    record.source_domain,
                    fetched_at,
                    fetched_at,
                    records_seen,
                    records_changed,
                    "selected_record_only",
                    "healthy",
                ),
            )

        return {"result": result, "source_record_id": record.source_record_id, "evidence_id": evidence_id}

    def trace(self, source_record_id: str) -> dict:
        with self._connection() as connection:
            row = connection.execute(
                """SELECT t.*, e.source_url, e.fetched_at, e.source_updated_at AS evidence_source_updated_at,
                          e.evidence_class, e.raw_payload_json, e.redacted_fields_json
                   FROM transaction_record t JOIN raw_evidence e ON e.id=t.evidence_id
                   WHERE t.source_system='meiguanjia' AND t.source_record_id=?""",
                (source_record_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"No stored transaction / consumption record: {source_record_id}")
            lines = connection.execute(
                """SELECT l.*, i.source_id AS service_source_id, i.display_label AS service_label
                   FROM line_item l LEFT JOIN identity_link i ON i.canonical_id=l.service_canonical_id
                   WHERE l.transaction_id=? ORDER BY l.position""",
                (row["canonical_id"],),
            ).fetchall()
            result_lines = []
            for line in lines:
                assignments = connection.execute(
                    """SELECT a.*, i.source_id AS employee_source_id, i.display_label AS employee_label
                       FROM staff_assignment a LEFT JOIN identity_link i ON i.canonical_id=a.employee_canonical_id
                       WHERE a.line_item_id=? ORDER BY a.position""",
                    (line["id"],),
                ).fetchall()
                result_lines.append(
                    {
                        "source_line_id": line["source_line_id"],
                        "service": {"canonical_id": line["service_canonical_id"], "source_id": line["service_source_id"], "label": line["service_label"]},
                        "displayed_amount": line["displayed_amount"],
                        "staff_assignments": [
                            {
                                "employee": {"canonical_id": a["employee_canonical_id"], "source_id": a["employee_source_id"], "label": a["employee_label"]},
                                "role": a["role_label"],
                                "designation": a["designation_label"],
                                "source_assignment_id": a["source_assignment_id"],
                            }
                            for a in assignments
                        ],
                    }
                )
            return {
                "canonical_id": row["canonical_id"],
                "evidence_class": row["evidence_class"],
                "business_semantics": "transaction / consumption record; does not establish arrival or completed service",
                "source": {
                    "system": row["source_system"],
                    "domain": row["source_domain"],
                    "record_id": row["source_record_id"],
                    "primary_key": row["source_primary_key"],
                    "url": row["source_url"],
                    "fetched_at": row["fetched_at"],
                    "source_updated_at": row["evidence_source_updated_at"],
                    "evidence_id": row["evidence_id"],
                },
                "source_recorded_at": row["source_recorded_at"],
                "posted_amount": row["posted_amount"],
                "customer": {"canonical_id": row["customer_canonical_id"]},
                "line_items": result_lines,
                "raw_evidence": json.loads(row["raw_payload_json"]),
                "redacted_fields": json.loads(row["redacted_fields_json"]),
            }

    def customer_current_view(self, source_customer_id: str) -> dict:
        canonical = f"meiguanjia:customer:{source_customer_id}"
        with self._connection() as connection:
            identity = connection.execute(
                "SELECT * FROM identity_link WHERE entity_type='customer' AND source_id=? AND source_system='meiguanjia'",
                (source_customer_id,),
            ).fetchone()
            if identity is None:
                raise KeyError(f"No customer identity link: {source_customer_id}")
            rows = connection.execute(
                """SELECT source_record_id,source_recorded_at,posted_amount,evidence_id
                   FROM transaction_record WHERE customer_canonical_id=? ORDER BY source_recorded_at DESC""",
                (canonical,),
            ).fetchall()
            freshness = self._sync_state(connection)
            return {
                "customer_id": canonical,
                "source_customer_id": source_customer_id,
                "identity_confidence": identity["confidence"],
                "record_count": len(rows),
                "last_consumption_record_at": rows[0]["source_recorded_at"] if rows else None,
                "records": [dict(row) for row in rows],
                "freshness": freshness,
            }

    def employee_current_view(self, source_employee_id: str) -> dict:
        canonical = f"meiguanjia:employee:{source_employee_id}"
        with self._connection() as connection:
            identity = connection.execute(
                "SELECT * FROM identity_link WHERE entity_type='employee' AND source_id=? AND source_system='meiguanjia'",
                (source_employee_id,),
            ).fetchone()
            if identity is None:
                raise KeyError(f"No employee identity link: {source_employee_id}")
            rows = connection.execute(
                """SELECT t.source_record_id,t.source_recorded_at,t.evidence_id,l.source_service_id,
                          l.displayed_amount,a.role_label,a.designation_label
                   FROM staff_assignment a JOIN line_item l ON l.id=a.line_item_id
                   JOIN transaction_record t ON t.canonical_id=l.transaction_id
                   WHERE a.employee_canonical_id=? ORDER BY t.source_recorded_at DESC""",
                (canonical,),
            ).fetchall()
            freshness = self._sync_state(connection)
            return {
                "employee_id": canonical,
                "source_employee_id": source_employee_id,
                "display_label": identity["display_label"],
                "identity_confidence": identity["confidence"],
                "assigned_record_count": len(rows),
                "last_assigned_record_at": rows[0]["source_recorded_at"] if rows else None,
                "records": [dict(row) for row in rows],
                "freshness": freshness,
            }

    @staticmethod
    def _sync_state(connection: sqlite3.Connection) -> dict | None:
        row = connection.execute(
            "SELECT * FROM sync_state WHERE source_system='meiguanjia' AND source_domain='transaction_consumption'"
        ).fetchone()
        if row is None:
            return None
        result = dict(row)
        last_success = datetime.fromisoformat(result["last_success_at"])
        if last_success.tzinfo is None:
            last_success = last_success.replace(tzinfo=timezone.utc)
        result["age_seconds"] = max(
            0,
            int((datetime.now(timezone.utc) - last_success.astimezone(timezone.utc)).total_seconds()),
        )
        return result
