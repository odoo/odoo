"""Confidence routing, fallbacks and review flags (week-7 milestone).

Covers the four claims the brief makes:

1. **Deterministic confidence sources** — ``confidence.py`` unit checks:
   arithmetic line-sum verification, per-country VAT regex rescue, ISO-13616
   IBAN rescue, and the weighted blend (self-report + OCR conf + math +
   rescue). These are the signals that are *not* log-probs.

2. **Calibrated routing** — a balanced, high-self-report extraction rides the
   Auto kanban column; a garbled one (wrong grand total) lands in Needs
   Review; a human-validated bill is Approved; a payload-less move never
   slips through as Auto.

3. **Runtime threshold** — the global ``invoice_agent.confidence_threshold``
   config parameter overrides the journal threshold, and flipping it back
   re-routes the move (the zero-downtime rollback path).

4. **Review flag + chatter** — sub-threshold bills keep their draft but are
   flagged with ``ai_review_required`` and the reason is posted on the
   chatter, plus the week-7 second-chance path: ``_run_high_effort_pass``
   re-extracts with ``effort='high'`` and re-scores before the bill is
   routed.

The Claude API and Tesseract are never touched: ``extract_invoice`` and
``score_extraction`` are patched where a network call would otherwise
happen, mirroring the pattern used by ``test_pipeline.py``.
"""

from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from odoo.addons.invoice_agent.models import confidence as confidence_lib
from odoo.addons.invoice_agent.models.invoice_extraction import (
    InvoiceExtraction,
    _PYDANTIC_AVAILABLE,
)

GLOBAL_THRESHOLD_PARAM = "invoice_agent.confidence_threshold"


def ensure_chart_of_accounts(env):
    """Load the generic COA so journals carry default accounts (CI paranoia)."""
    company = env.company
    if not company.chart_template:
        env["account.chart.template"].try_loading(
            "generic_coa",
            company=company,
            install_demo=False,
        )
    env.flush_all()


def balanced_payload(amount_total=1350.0, overall=0.95):
    """A schema-shaped payload that adds up and reports high certainty."""
    return {
        "vendor_name": "ACME Supplies LLC",
        "vendor_vat": "US123456789",
        "invoice_date": "2026-07-01",
        "due_date": "2026-07-31",
        "currency": "USD",
        "subtotal": 1350.0,
        "tax_total": 0.0,
        "amount_total": amount_total,
        "lines": [
            {"name": "Server hosting", "quantity": 1.0, "price_unit": 850.0},
            {"name": "Setup fee", "quantity": 1.0, "price_unit": 500.0},
        ],
        "field_confidence": {
            "overall": overall,
            "vendor_name": 0.98,
            "vendor_vat": 0.95,
            "invoice_date": 0.97,
            "due_date": 0.96,
            "currency": 1.0,
            "subtotal": 0.96,
            "tax_total": 0.96,
            "amount_total": 0.97,
            "lines": 0.95,
        },
        "notes": "Clean scan.",
    }


def garbled_payload():
    """A torn totals section: subtotal/tax unreadable, TOTAL garbled to 9999.

    The line items (sum 1350) still parse cleanly, but with both the subtotal
    and the TOTAL unavailable the arithmetic cross-check has no sane target
    and the honest low self-report corroborates — the bill must land in Needs
    Review.
    """
    payload = balanced_payload(amount_total=9999.0, overall=0.55)
    payload["subtotal"] = None
    payload["tax_total"] = None
    payload["notes"] = (
        "OCR garbled the totals section — the line items do not match the "
        "printed 9999.00 TOTAL."
    )
    return payload


BALANCED_OCR_TEXT = (
    "ACME SUPPLIES LLC\nVAT: US123456789\n\n"
    "Server hosting 1 850.00\nSetup fee 1 500.00\n"
    "TOTAL USD 1,350.00"
)


@tagged("post_install", "-at_install")
class TestConfidenceRouting(TransactionCase):
    """Kanban routing by the calibrated blend + runtime threshold."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_chart_of_accounts(cls.env)
        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        if not cls.journal:
            cls.journal = cls.env["account.journal"].create(
                {
                    "name": "Test Purchase Journal",
                    "type": "purchase",
                    "code": "TPC",
                },
            )
        cls.journal.write(
            {
                "ai_agent_enabled": True,
                "ai_min_confidence": 0.80,
            },
        )
        cls.env.flush_all()

    def _make_move(self, payload=None, status="extracted", ocr_text=BALANCED_OCR_TEXT,
                   ocr_confidence=0.9):
        return self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "journal_id": self.journal.id,
                "partner_id": False,
                "ai_extraction_status": status,
                "ai_ocr_text": ocr_text if ocr_text is not None else "",
                "ocr_confidence": ocr_confidence,
                "ai_extracted_json": payload,
                "ai_confidence": 0.0,
            },
        )

    def test_balanced_payload_routes_auto(self):
        """A payload that adds up with high stated certainty rides Auto."""
        move = self._make_move(balanced_payload())
        move._compute_confidence_score()
        self.assertGreaterEqual(move.confidence_score, 0.80)
        self.assertEqual(move.ai_extraction_state, "auto")
        self.assertFalse(move.ai_review_required)

    def test_garbled_total_routes_needs_review(self):
        """A wrong grand total degrades the score below threshold."""
        move = self._make_move(garbled_payload())
        move._compute_confidence_score()
        self.assertLess(move.confidence_score, 0.80)
        self.assertEqual(move.ai_extraction_state, "needs_review")

    def test_validated_bill_is_approved(self):
        """A human-validated bill is Approved regardless of the threshold."""
        move = self._make_move(balanced_payload())
        move.write(
            {
                "ai_confidence": 0.9,
                "ai_extraction_status": "validated",
            },
        )
        move._compute_confidence_score()
        self.assertEqual(move.ai_extraction_state, "approved")

    def test_empty_payload_never_auto(self):
        """An unscored bill must never slip into the Auto column."""
        move = self._make_move(payload=None)
        move._compute_confidence_score()
        self.assertEqual(move.ai_extraction_state, "needs_review")

    def test_failed_pipeline_never_auto(self):
        """A failed extraction routes to Needs Review even with a payload."""
        move = self._make_move(balanced_payload(), status="failed")
        move._compute_confidence_score()
        self.assertEqual(move.ai_extraction_state, "needs_review")

    def test_global_threshold_overrides_and_rolls_back(self):
        """The config parameter beats the journal value, both directions."""
        move = self._make_move(balanced_payload())
        move._compute_confidence_score()
        self.assertEqual(move.ai_extraction_state, "auto")

        # Tighten globally to 0.99 — the same bill must fall to review.
        self.env["ir.config_parameter"].set_param(GLOBAL_THRESHOLD_PARAM, "0.99")
        move._compute_confidence_score()
        self.assertEqual(move.ai_extraction_state, "needs_review")

        # Rollback path: unset the parameter; the journal value applies again.
        self.env["ir.config_parameter"].set_param(GLOBAL_THRESHOLD_PARAM, "")
        move._compute_confidence_score()
        self.assertEqual(move.ai_extraction_state, "auto")

    def test_threshold_accessor_clamps_out_of_range(self):
        """A stored threshold outside 0..1 is clamped, never trusted raw."""
        param = self.env["ir.config_parameter"]
        param.set_param(GLOBAL_THRESHOLD_PARAM, "1.75")
        self.assertEqual(
            self.env["invoice.llm.service"].confidence_threshold(),
            1.0,
        )
        param.set_param(GLOBAL_THRESHOLD_PARAM, "-1")
        self.assertEqual(
            self.env["invoice.llm.service"].confidence_threshold(),
            0.0,
        )
        param.set_param(GLOBAL_THRESHOLD_PARAM, "")


@tagged("post_install", "-at_install")
class TestReviewFlagAndChatter(TransactionCase):
    """Sub-threshold bills stay drafts but are flagged with a visible reason."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_chart_of_accounts(cls.env)

    def test_flag_needs_review_posts_chatter_reason(self):
        move = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": False,
                "ai_extraction_status": "extracted",
                "ai_confidence": 0.42,
                "ai_confidence_notes": "Two conflicting TOTAL lines on the scan.",
            },
        )
        move._flag_needs_review(reason="extracted confidence 42% is below the 80% threshold")

        self.assertTrue(move.ai_review_required)
        messages = move.message_ids
        self.assertTrue(
            any("AI Needs Review" in (msg.subject or "") for msg in messages),
        )
        body = "\n".join(msg.body or "" for msg in messages)
        self.assertIn("below the 80% threshold", body)
        self.assertIn("Two conflicting TOTAL lines", body)


@tagged("post_install", "-at_install")
class TestHighEffortSecondPass(TransactionCase):
    """The week-7 fallback: re-extract with effort='high', re-score, route."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_chart_of_accounts(cls.env)
        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        if not cls.journal:
            cls.journal = cls.env["account.journal"].create(
                {
                    "name": "Test Purchase Journal",
                    "type": "purchase",
                    "code": "TPH",
                },
            )
        cls.journal.write(
            {
                "ai_agent_enabled": True,
                "ai_min_confidence": 0.80,
            },
        )
        cls.env.flush_all()

    def _move_with_low_first_pass(self):
        """First pass scored low (garbled total); the run is re-tried."""
        return self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "journal_id": self.journal.id,
                "partner_id": False,
                "ai_extraction_status": "extracted",
                "ai_ocr_text": BALANCED_OCR_TEXT,
                "ocr_confidence": 0.9,
                "ai_extracted_json": garbled_payload(),
                "ai_confidence": 0.4,
            },
        )

    def test_high_effort_pass_rescores_and_routes_auto(self):
        if not _PYDANTIC_AVAILABLE:
            self.skipTest("pydantic unavailable in this image")
        move = self._move_with_low_first_pass()
        move._compute_confidence_score()
        previous_score = move.confidence_score
        self.assertEqual(move.ai_extraction_state, "needs_review")

        # Second pass: Claude returns a correct extraction with effort='high'.
        improved = InvoiceExtraction.model_validate(balanced_payload())

        def fake_extract(text, effort="normal"):
            self.assertEqual(effort, "high")  # the brief's higher-effort call
            return {
                "parsed": improved,
                "model": "claude-opus-4-8",
                "usage": {
                    "input_tokens": 210,
                    "output_tokens": 142,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
                "stop_reason": "end_turn",
            }

        with patch.object(
            self.env["invoice.llm.service"].__class__,
            "extract_invoice",
            side_effect=fake_extract,
        ):
            improved_flag = move._run_high_effort_pass(0.80)

        self.assertTrue(improved_flag)
        self.assertGreater(move.confidence_score, previous_score)
        self.assertEqual(move.confidence_score, move.ai_confidence)
        self.assertEqual(move.ai_extraction_state, "auto")
        checks = (move.ai_confidence_details or {}).get("checks") or []
        self.assertIn("high_effort", checks)


@tagged("post_install", "-at_install")
class TestDeterministicConfidenceSignals(TransactionCase):
    """The confidence sources that are not log-probs, checked directly."""

    def test_arithmetic_check(self):
        lines = [
            {"name": "A", "quantity": 4.0, "price_unit": 12.5},
            {"name": "B", "quantity": 6.0, "price_unit": 18.0},
        ]
        self.assertEqual(confidence_lib.arithmetic_check(lines, 158.0), 1.0)
        # Rounding-level divergence scores 0.5 (within 1 currency unit).
        self.assertEqual(confidence_lib.arithmetic_check(lines, 158.5), 0.5)
        # Hard mismatch scores 0.
        self.assertEqual(confidence_lib.arithmetic_check(lines, 9999.0), 0.0)
        # Missing grand total scores 0.
        self.assertEqual(confidence_lib.arithmetic_check(lines, None), 0.0)

    def test_taxed_invoice_math_uses_subtotal_not_grand_total(self):
        """Lines add up to the subtotal, never the tax-inclusive total.

        Regression for the week-7 calibration bug: a VAT invoice whose lines
        sum to 500.00 and whose amount_total is 621.60 is perfectly
        consistent. Comparing lines against amount_total would fail every
        taxed bill and send them all to Needs Review.
        """
        taxed = {
            "vendor_name": "NORDIC IT OY",
            "vendor_vat": "FI12345678",
            "invoice_date": "2026-02-14",
            "due_date": "2026-03-14",
            "currency": "EUR",
            "subtotal": 500.0,
            "tax_total": 121.6,
            "amount_total": 621.6,
            "lines": [
                {"name": "Azure VM Hosting", "quantity": 1.0, "price_unit": 420.0},
                {"name": "Managed Backup", "quantity": 1.0, "price_unit": 80.0},
            ],
            "field_confidence": {
                "overall": 0.95,
                "vendor_name": 0.98,
                "vendor_vat": 0.95,
                "invoice_date": 0.97,
                "due_date": 0.96,
                "currency": 1.0,
                "subtotal": 0.96,
                "tax_total": 0.96,
                "amount_total": 0.97,
                "lines": 0.95,
            },
            "notes": None,
        }
        score, details = confidence_lib.combined_confidence(
            taxed,
            ocr_text="NORDIC IT OY\nVAT FI12345678\nAzure 420.00\nBackup 80.00",
            ocr_confidence=0.9,
        )
        # The arithmetic check must pass against the subtotal (500.00), not
        # fail against the grand total (621.60).
        self.assertEqual(details["math_score"], 1.0)
        self.assertGreaterEqual(score, 0.80)

    def test_vat_regex_rescue(self):
        self.assertEqual(confidence_lib.vat_from_text("VAT DE123456789"), "DE123456789")
        self.assertEqual(
            confidence_lib.vat_from_text("UID CHE-123.456.789"),
            "CHE-123.456.789",
        )
        self.assertEqual(
            confidence_lib.vat_from_text("TRN 310123456789014"),
            "310123456789014",
        )
        self.assertIsNone(confidence_lib.vat_from_text("no tax numbers here"))
        self.assertIsNone(confidence_lib.vat_from_text(None))

    def test_iban_regex_rescue(self):
        ocr = "Please pay to\nDE89 3704 0044 0532 0130 00 within 14 days."
        self.assertEqual(
            confidence_lib.iban_from_text(ocr),
            "DE89370400440532013000",
        )
        # A short "DE12" substring is a false positive, not an IBAN.
        self.assertIsNone(confidence_lib.iban_from_text("Postleitzahl DE12 345"))

    def test_apply_rescues_fills_missing_fields_and_logs_checks(self):
        payload = {"vendor_name": "Some Vendor", "vendor_vat": None}
        checks = confidence_lib.apply_rescues(
            payload,
            "VAT FI12345678\nIBAN FI21 1234 5600 0007 85",
        )
        self.assertEqual(payload["vendor_vat"], "FI12345678")
        self.assertEqual(payload["vendor_iban"], "FI2112345600000785")
        self.assertIn("rescue:vat", checks)
        self.assertIn("rescue:iban", checks)
        # An already-extracted VAT is trusted over the regex.
        payload2 = {"vendor_name": "Vendor", "vendor_vat": "US123456789"}
        checks2 = confidence_lib.apply_rescues(payload2, "VAT FI12345678")
        self.assertEqual(payload2["vendor_vat"], "US123456789")
        self.assertNotIn("rescue:vat", checks2)

    def test_combined_confidence_blend_weights_and_ceiling(self):
        payload = balanced_payload()
        score, details = confidence_lib.combined_confidence(
            payload,
            ocr_text=BALANCED_OCR_TEXT,
            ocr_confidence=0.9,
        )
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
        self.assertEqual(details["math_score"], 1.0)
        self.assertEqual(
            details["weights"],
            {
                "self_report": confidence_lib.SELF_REPORT_WEIGHT,
                "ocr": confidence_lib.OCR_WEIGHT,
                "math": confidence_lib.MATH_WEIGHT,
                "rescue": confidence_lib.RESCUE_WEIGHT,
                "verified_bonus": confidence_lib.VERIFIED_BONUS,
            },
        )
        # The score is never the raw self-report — it is a weighted blend.
        self.assertNotEqual(score, payload["field_confidence"]["overall"])
        # A garbled total must blend strictly below a balanced one.
        garbled_score, _ = confidence_lib.combined_confidence(
            garbled_payload(),
            ocr_text=BALANCED_OCR_TEXT,
            ocr_confidence=0.9,
        )
        self.assertLess(garbled_score, score)
