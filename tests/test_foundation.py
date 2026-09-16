from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nice_salon.meiguanjia import parse_page_capture
from nice_salon.store import FoundationStore


def capture(*, amount: str = "75.00", captured_at: str = "2026-09-16T12:00:00+08:00") -> dict:
    return {
        "source_system": "meiguanjia",
        "source_domain": "transaction_consumption",
        "source_url": "https://vip3.meiguanjia.net/shair/bill!bill.action?set=manage&billFlag=0",
        "capture_method": "authenticated_page_dom",
        "captured_at": captured_at,
        "query": {"start_date": "2026-09-16", "end_date": "2026-09-16"},
        "page": {
            "visible_record_count": 1,
            "source_total_count": 1,
            "complete": True,
            "selected_record_only": True,
            "selected_bill_number": "X260916073849",
        },
        "records": [
            {
                "source_record_id": "X260916073849",
                "source_primary_key": "802598593711",
                "source_recorded_at": "2026-09-16 10:50:59",
                "customer_source_id": "customer-fixture-1",
                "posted_amount_displayed": amount,
                "line_items": [
                    {
                        "source_service_id": "1005",
                        "source_line_id": "803620403927",
                        "service_label": "设计总监剪发",
                        "amount_displayed": "75.0",
                        "staff_assignments": [
                            {
                                "source_employee_id": "4214986",
                                "source_assignment_id": "804884237634",
                                "display_label": "3号 首席 [设计师甲]",
                                "role_label": "首席",
                                "designation_label": "指定",
                            },
                            {
                                "source_employee_id": "23153179",
                                "source_assignment_id": "804884237636",
                                "display_label": "22号 助理 [助理乙]",
                                "role_label": "助理",
                                "designation_label": "非指定",
                            },
                        ],
                    }
                ],
                "source_updated_at": None,
                "redacted_fields": ["customer_display_name", "customer_phone", "payment_breakdown", "cashier_display_name"],
            }
        ],
    }


class MeiguanjiaCaptureTests(unittest.TestCase):
    def test_parses_realistic_record_and_preserves_multi_staff_semantics(self) -> None:
        result = parse_page_capture(capture())
        self.assertEqual(result.evidence_class, "SYSTEM_FACT")
        self.assertEqual(result.source_record_id, "X260916073849")
        self.assertEqual(result.customer.source_id, "customer-fixture-1")
        self.assertEqual(result.line_items[0].service.source_id, "1005")
        self.assertEqual(len(result.line_items[0].staff_assignments), 2)
        self.assertEqual(result.line_items[0].staff_assignments[0].role_label, "首席")
        self.assertEqual(result.line_items[0].staff_assignments[1].designation_label, "非指定")
        self.assertIsNone(result.source_updated_at)
        self.assertIn("customer_phone", result.redacted_fields)
        self.assertTrue(result.capture_context["query"]["date_range_verified"])

    def test_missing_visible_date_range_is_recorded_as_unverified(self) -> None:
        no_dates = capture()
        no_dates["query"] = {"start_date": None, "end_date": None}
        result = parse_page_capture(no_dates)
        self.assertFalse(result.capture_context["query"]["date_range_verified"])

    def test_refuses_mismatched_or_incomplete_page_evidence(self) -> None:
        bad = capture()
        bad["page"]["complete"] = False
        with self.assertRaisesRegex(ValueError, "incomplete"):
            parse_page_capture(bad)

        bad = capture()
        bad["page"]["source_total_count"] = 2
        with self.assertRaisesRegex(ValueError, "row count"):
            parse_page_capture(bad)

    def test_refuses_service_semantics_when_identity_evidence_is_missing(self) -> None:
        bad = capture()
        bad["records"][0]["line_items"][0]["staff_assignments"][0]["source_employee_id"] = None
        with self.assertRaisesRegex(ValueError, "source_id"):
            parse_page_capture(bad)


class FoundationStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "foundation.sqlite3"
        self.store = FoundationStore(self.database)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_ingest_is_idempotent_and_traceable(self) -> None:
        first = self.store.ingest_capture(capture())
        second_capture = capture(captured_at="2026-09-16T12:03:00+08:00")
        second = self.store.ingest_capture(second_capture)
        self.assertEqual(first["result"], "inserted")
        self.assertEqual(second["result"], "unchanged")
        self.assertNotEqual(first["evidence_id"], second["evidence_id"])

        traced = self.store.trace("X260916073849")
        self.assertEqual(traced["source"]["record_id"], "X260916073849")
        self.assertEqual(traced["source"]["evidence_id"], second["evidence_id"])
        self.assertIn("capture_context", traced["raw_evidence"])
        self.assertEqual(traced["raw_evidence"]["capture_context"]["page"]["source_total_count"], 1)
        self.assertEqual(len(traced["line_items"][0]["staff_assignments"]), 2)
        self.assertIsNone(traced["source"]["source_updated_at"])
        self.assertIn("does not establish arrival", traced["business_semantics"])

        customer = self.store.customer_current_view("customer-fixture-1")
        self.assertEqual(customer["record_count"], 1)
        self.assertEqual(customer["records"][0]["evidence_id"], second["evidence_id"])
        self.assertEqual(customer["freshness"]["capture_scope"], "selected_record_only")
        self.assertGreaterEqual(customer["freshness"]["age_seconds"], 0)
        employee = self.store.employee_current_view("4214986")
        self.assertEqual(employee["assigned_record_count"], 1)
        self.assertEqual(employee["records"][0]["source_record_id"], "X260916073849")

    def test_changed_record_updates_current_view_but_keeps_old_evidence(self) -> None:
        first = self.store.ingest_capture(capture())
        second = self.store.ingest_capture(capture(amount="76.00", captured_at="2026-09-16T12:05:00+08:00"))
        self.assertEqual(second["result"], "updated")
        self.assertNotEqual(first["evidence_id"], second["evidence_id"])
        traced = self.store.trace("X260916073849")
        self.assertEqual(traced["posted_amount"], "76.00")
        self.assertEqual(traced["source"]["evidence_id"], second["evidence_id"])
        with self.store._connection() as connection:
            raw_count = connection.execute("SELECT COUNT(*) FROM raw_evidence").fetchone()[0]
        self.assertEqual(raw_count, 2)


if __name__ == "__main__":
    unittest.main()
