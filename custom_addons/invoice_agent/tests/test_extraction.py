"""TransactionCase tests for the invoice_agent extraction state machine.

Covered here:

* ``_invoice_agent_schedule_extraction``: pending -> processing
* ``_run_extraction`` with a frozen (mocked) Claude response: processing ->
  extracted, with ``ai_confidence``, per-line ``ai_confidence``,
  ``ai_extracted_total`` and the payload fields mapped to the move.
* malformed Claude JSON: degrades the move to ``failed`` with
  ``ai_error_message`` set — it must never raise through the caller.
* the ``create_from_extraction`` facade: happy path and error codes.

The Claude client is never touched: ``_claude_messages_create`` is replaced by
a double that replays ``tests/fixtures/claude_response.json``, so the suite is
deterministic and offline.

Why not ``AccountTestInvoicingCommon``? That common class assumes a chart of
accounts (journals/accounts/taxes) is already loaded — true on demo or
localization-enabled databases, but CI installs ``invoice_agent`` on a fresh
DB. This suite loads the Generic COA explicitly and hand-rolls the two
fixtures it needs (a partner and a purchase journal), mirroring the existing
``test_bulk_wizard.py`` style in this module.
"""

import json
import types
from unittest.mock import patch

from odoo.addons.invoice_agent.models.account_move import (
    AccountMove as AccountMoveModel,
)
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tools import file_path


def ensure_chart_of_accounts(env):
    """Load the Generic COA for the test company when none is configured.

    CI installs ``invoice_agent`` on a fresh DB with no demo data, so no chart
    template is loaded for the main company. Loading ``generic_coa`` creates
    the journals/accounts/taxes the accounting fixtures need. Mirrors the
    pattern used in ``addons/account`` tests (``try_loading`` in
    ``test_company_branch.py``).
    """
    company = env.company
    if not company.chart_template:
        env["account.chart.template"].try_loading(
            "generic_coa",
            company=company,
            install_demo=False,
        )
    env.flush_all()


def _load_fixture_text():
    """Read the frozen Anthropic message and return the assistant's text.

    ``file_path`` resolves relative to the configured addons paths, so the
    fixture loads regardless of the current working directory.
    """
    path = file_path("invoice_agent/tests/fixtures/claude_response.json")
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload["content"][0]["text"]


def _fake_claude_response(raw_text):
    """Build an object shaped like anthropic's Messages response."""

    class _ContentBlock:
        def __init__(self, text):
            self.text = text

    return types.SimpleNamespace(content=[_ContentBlock(raw_text)])


class InvoiceAgentTestCommon(TransactionCase):
    """Shared, fresh-DB-safe fixtures for the invoice_agent test suite."""

    @classmethod
    def setUpClass(cls):
        # cls.env is created by TransactionCase.setUpClass — load the chart
        # only afterwards, but before any accounting records are built.
        super().setUpClass()
        ensure_chart_of_accounts(cls.env)
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "ACME Supplies LLC",
                "company_id": False,
            },
        )
        cls.purchase_journal = cls.env["account.journal"].search(
            [
                ("type", "=", "purchase"),
                ("company_id", "=", cls.env.company.id),
            ],
            limit=1,
        )
        if not cls.purchase_journal:
            cls.purchase_journal = cls.env["account.journal"].create(
                {
                    "name": "Test Purchase Journal",
                    "type": "purchase",
                    "code": "TPJ",
                },
            )
        cls.env.flush_all()


@tagged("post_install", "-at_install")
class TestExtractionFlow(InvoiceAgentTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # A bill that the worker will consume.
        cls.move = cls.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": cls.partner.id,
                "invoice_date": "2026-07-01",
                "journal_id": cls.purchase_journal.id,
                "ai_extraction_status": "processing",
                "ai_ocr_text": "INVOICE #777\nTotal 1350.00",
            },
        )

    def test_schedule_extraction_flips_pending_to_processing(self):
        move = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner.id,
                "invoice_date": "2026-07-01",
                "journal_id": self.purchase_journal.id,
                "ai_extraction_status": "pending",
            },
        )
        self.assertEqual(move.ai_extraction_status, "pending")

        move._invoice_agent_schedule_extraction()

        self.assertEqual(move.ai_extraction_status, "processing")

    def test_run_extraction_applies_frozen_claude_payload(self):
        fixture_text = _load_fixture_text()

        with patch.object(
            AccountMoveModel,
            "_claude_messages_create",
            lambda self, ocr_text, model="claude-sonnet-4-5": _fake_claude_response(
                fixture_text,
            ),
        ):
            self.move._run_extraction()

        self.assertEqual(self.move.ai_extraction_status, "extracted")
        self.assertAlmostEqual(self.move.ai_confidence, 0.93, places=2)
        self.assertAlmostEqual(self.move.ai_extracted_total, 1350.0, places=2)
        # Vendor matched by name -> extracted_vendor_id back-linked to the move.
        self.assertEqual(
            self.move.ai_extracted_json["extracted_vendor_id"],
            self.partner.id,
        )
        self.assertEqual(self.move.partner_id, self.partner)
        # Per-line confidence is mapped onto the real invoice lines.
        self.assertTrue(self.move.invoice_line_ids)
        self.assertAlmostEqual(
            max(self.move.invoice_line_ids.mapped("ai_confidence")),
            0.95,
            places=2,
        )
        # Computed fields follow from the extracted total.
        self.assertAlmostEqual(self.move.ai_amount_variance, 0.0, places=2)
        self.assertAlmostEqual(self.move.ai_variance_pct, 0.0, places=4)
        self.assertFalse(self.move.ai_needs_review)

    def test_run_extraction_malformed_json_degrades_to_failed(self):
        with patch.object(
            AccountMoveModel,
            "_claude_messages_create",
            lambda self, ocr_text, model="claude-sonnet-4-5": _fake_claude_response(
                "this is not json",
            ),
        ):
            # Must not raise — the pipeline reports failure on the record.
            self.move._run_extraction()

        self.assertEqual(self.move.ai_extraction_status, "failed")
        self.assertTrue(self.move.ai_error_message)
        self.assertIn("malformed JSON", self.move.ai_error_message)

    def test_run_extraction_non_object_payload_degrades_to_failed(self):
        with patch.object(
            AccountMoveModel,
            "_claude_messages_create",
            lambda self, ocr_text, model="claude-sonnet-4-5": _fake_claude_response(
                json.dumps(["not", "an", "object"]),
            ),
        ):
            self.move._run_extraction()

        self.assertEqual(self.move.ai_extraction_status, "failed")
        self.assertIn("non-object", self.move.ai_error_message)

    def test_invalid_confidence_blocked_by_constraint(self):
        self.move.write({"ai_extraction_status": "extracted", "ai_confidence": 0.99})
        with self.assertRaises(ValidationError):
            # Validated status requires confidence >= journal's min (0.75).
            self.move.write(
                {"ai_extraction_status": "validated", "ai_confidence": 0.40},
            )

    def test_facade_create_from_extraction_happy_path(self):
        result = self.env["account.move"].create_from_extraction(
            {
                "partner_id": self.partner.id,
                "invoice_date": "2026-07-05",
                "ref": "FACADE-001",
                "lines": [
                    {
                        "name": "Hosting",
                        "price_unit": 850.0,
                        "quantity": 1,
                    },
                ],
            },
        )

        self.assertTrue(result["success"])
        move = self.env["account.move"].browse(result["id"])
        self.assertTrue(move.exists())
        self.assertEqual(move.move_type, "in_invoice")
        self.assertEqual(move.partner_id, self.partner)
        self.assertEqual(move.ref, "FACADE-001")
        self.assertEqual(move.ai_extraction_status, "pending")
        self.assertEqual(len(move.invoice_line_ids), 1)
        self.assertAlmostEqual(move.amount_total, 850.0, places=2)

    def test_facade_rejects_invalid_line(self):
        result = self.env["account.move"].create_from_extraction(
            {
                "lines": [
                    {"nothing_useful": True},
                ],
            },
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "E4003")

    def test_facade_rejects_missing_lines(self):
        result = self.env["account.move"].create_from_extraction({"legacy": "x"})
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "E4002")

    def test_facade_rejects_non_dict_payload(self):
        result = self.env["account.move"].create_from_extraction(["nope"])
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "E4001")
