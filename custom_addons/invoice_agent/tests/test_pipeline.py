"""End-to-end pipeline test: OCR -> Claude -> map -> draft account.move.

The full chain ``_create_move_from_extraction`` is exercised with both
external services mocked:

* ``invoice.ocr.service._extract_text`` — returns a frozen OCR string so CI
  does not need the tesseract binary.
* ``invoice.llm.service.extract_invoice`` — returns a real schema-validated
  ``InvoiceExtraction`` pydantic model so the mapping code runs against the
  exact object shape the production path produces. The Claude API is never
  touched.

Assertions follow the task brief: a fixture PDF produces a draft vendor bill
(``move_type == 'in_invoice'``, ``state == 'draft'``) with the partner and
totals resolved, and the balance guard rejects internally-inconsistent
extractions before any move is created.
"""

import base64
import json
from unittest.mock import patch

from odoo.addons.invoice_agent.models.invoice_extraction import (
    _PYDANTIC_AVAILABLE,
    InvoiceExtraction,
)
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tools import file_path


def ensure_chart_of_accounts(env):
    """Load the Generic COA for the test company when none is configured.

    Mirrors ``test_extraction.py`` — CI installs on a fresh DB without demo
    data, so journals/accounts/taxes must be loaded explicitly.
    """
    company = env.company
    if not company.chart_template:
        env["account.chart.template"].try_loading(
            "generic_coa",
            company=company,
            install_demo=False,
        )
    env.flush_all()


def _load_frozen_extraction_text():
    """Read the frozen Claude answer from the existing fixture."""
    path = file_path("invoice_agent/tests/fixtures/claude_response.json")
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload["content"][0]["text"]


def _frozen_llm_result():
    """Build the dict shaped like ``invoice.llm.service.extract_invoice``.

    The parsed payload is validated through the real pydantic schema, so the
    mapping layer receives the same ``InvoiceExtraction`` object type as in
    production. The pages live at 1350.00 total (850 + 500) which keeps the
    golden fixture balanced.
    """
    frozen_answers = {
        "acme_hosting": {
            "vendor_name": "ACME Supplies LLC",
            "vendor_vat": "US123456789",
            "invoice_date": "2026-07-01",
            "due_date": "2026-07-31",
            "currency": "EUR",
            "subtotal": 1350.0,
            "tax_total": 0.0,
            "amount_total": 1350.0,
            "lines": [
                {"name": "Server hosting", "quantity": 1.0, "price_unit": 850.0},
                {"name": "Setup fee", "quantity": 1.0, "price_unit": 500.0},
            ],
        },
    }

    def result_for(ocr_text):
        # The frozen LLM answer is identical for any OCR text in this suite.
        answer = frozen_answers["acme_hosting"]
        parsed = InvoiceExtraction.model_validate(answer)
        return {
            "parsed": parsed,
            "model": "claude-opus-4-8",
            "usage": {
                "input_tokens": 210,
                "output_tokens": 142,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
            "stop_reason": "end_turn",
        }

    return result_for


@tagged("post_install", "-at_install")
class TestExtractionPipeline(TransactionCase):
    """Drive a fixture PDF through the full OCR → LLM → move chain."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_chart_of_accounts(cls.env)
        # Vendor fixture matched by VAT first (the golden payload carries it).
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "ACME Supplies LLC",
                "vat": "US123456789",
                "company_id": False,
            },
        )
        cls.purchase_journal = cls.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", cls.env.company.id)],
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

    def _attachment(self, name="fixture-bill.pdf"):
        """Fake PDF binary stored as an ir.attachment (OCR never runs)."""
        return self.env["ir.attachment"].create(
            {
                "name": name,
                "datas": base64.b64encode(b"%PDF-1.4 fixture pipeline bill").decode(
                    "ascii",
                ),
                "mimetype": "application/pdf",
                "res_model": "account.move",
                "res_id": 0,
            },
        )

    def test_full_chain_creates_draft_move_with_totals(self):
        if not _PYDANTIC_AVAILABLE:
            self.skipTest("pydantic unavailable in this image")
        attachment = self._attachment()
        ocr_text = _load_frozen_extraction_text()

        with (
            patch.object(
                self.env["invoice.ocr.service"].__class__,
                "_extract_text",
                return_value={"text": ocr_text, "confidence": 0.92},
            ),
            patch.object(
                self.env["invoice.llm.service"].__class__,
                "extract_invoice",
                side_effect=_frozen_llm_result(),
            ),
        ):
            move = self.env["account.move"]._create_move_from_extraction(attachment)

        # The record exists, is a draft vendor bill, never posted.
        self.assertTrue(move.exists())
        self.assertEqual(move.move_type, "in_invoice")
        self.assertEqual(move.state, "draft")

        # Partner matched by VAT from the extraction.
        self.assertEqual(move.partner_id, self.partner)

        # Dates mapped through fields.Date.
        self.assertEqual(move.invoice_date.isoformat(), "2026-07-01")
        self.assertEqual(move.invoice_date_due.isoformat(), "2026-07-31")

        # Lines written via Command.create, totals computed by Odoo core.
        self.assertEqual(len(move.invoice_line_ids), 2)
        self.assertAlmostEqual(move.amount_untaxed, 1350.0, places=2)
        self.assertAlmostEqual(move.amount_total, 1350.0, places=2)

        # Pipeline metadata persisted for the review workflow.
        self.assertEqual(move.ai_extraction_status, "extracted")
        self.assertTrue(move.ai_review_required)
        self.assertAlmostEqual(move.ai_extracted_total, 1350.0, places=2)
        self.assertEqual(move.ai_source_attachment_id, attachment)
        self.assertTrue(move.extraction_json)

    def test_balance_guard_rejects_divergent_line_sum(self):
        """An extraction whose lines do not add up must not create a move."""
        if not _PYDANTIC_AVAILABLE:
            self.skipTest("pydantic unavailable in this image")
        attachment = self._attachment()

        unbalanced = {
            "vendor_name": "ACME Supplies LLC",
            "vendor_vat": "US123456789",
            "invoice_date": "2026-07-01",
            "due_date": "2026-07-31",
            "currency": "EUR",
            "subtotal": 1350.0,
            "tax_total": 0.0,
            # Lines sum to 1000.00 but the grand total says 9999.00
            "amount_total": 9999.0,
            "lines": [
                {"name": "Server hosting", "quantity": 1.0, "price_unit": 850.0},
                {"name": "Setup fee", "quantity": 1.0, "price_unit": 150.0},
            ],
        }

        def result_for(ocr_text):
            return {
                "parsed": InvoiceExtraction.model_validate(unbalanced),
                "model": "claude-opus-4-8",
                "usage": {},
                "stop_reason": "end_turn",
            }

        with (
            patch.object(
                self.env["invoice.ocr.service"].__class__,
                "_extract_text",
                return_value={"text": "some ocr", "confidence": 0.9},
            ),
            patch.object(
                self.env["invoice.llm.service"].__class__,
                "extract_invoice",
                side_effect=result_for,
            ),
        ):
            with self.assertRaises(ValidationError):
                self.env["account.move"]._create_move_from_extraction(attachment)

        # Nothing was persisted for the rejected extraction.
        self.assertEqual(
            self.env["account.move"].search_count(
                [("ai_source_attachment_id", "=", attachment.id)],
            ),
            0,
        )

    def test_unmatched_vendor_leaves_partner_empty(self):
        """Unknown vendor → partner_id stays empty, never a wrong guess."""
        if not _PYDANTIC_AVAILABLE:
            self.skipTest("pydantic unavailable in this image")
        attachment = self._attachment()

        unknown = {
            "vendor_name": "Totally Unknown Vendor XYZ",
            "vendor_vat": None,
            "invoice_date": "2026-07-01",
            "due_date": None,
            "currency": "USD",
            "subtotal": None,
            "tax_total": None,
            "amount_total": 100.0,
            "lines": [
                {"name": "Mystery service", "quantity": 1.0, "price_unit": 100.0},
            ],
        }

        def result_for(ocr_text):
            return {
                "parsed": InvoiceExtraction.model_validate(unknown),
                "model": "claude-opus-4-8",
                "usage": {},
                "stop_reason": "end_turn",
            }

        with (
            patch.object(
                self.env["invoice.ocr.service"].__class__,
                "_extract_text",
                return_value={"text": "some ocr", "confidence": 0.9},
            ),
            patch.object(
                self.env["invoice.llm.service"].__class__,
                "extract_invoice",
                side_effect=result_for,
            ),
        ):
            move = self.env["account.move"]._create_move_from_extraction(attachment)

        self.assertFalse(move.partner_id)
        self.assertEqual(move.state, "draft")
