"""Tests for the OCR pipeline: service guards, state machine, batch cron.

What is mocked vs real:

* ``invoice.ocr.service._extract_text`` is PATCHED in the cron tests — the
  batch-claim + per-record-commit behaviour is what we test there, not
  Tesseract itself.
* The service guard tests (no data / oversize / wrong mimetype / corrupt
  PDF) run the REAL guard code: every failure happens BEFORE any OCR
  toolchain is invoked, so the tests pass even on a stale image without
  tesseract or poppler.
* One end-to-end test renders a real image PDF with PIL and runs real
  Tesseract — it is skipped when the tesseract binary is missing from the
  image, so the suite stays green on CI workers before the rebuild.
"""

import base64
import io
import shutil
import unittest
from unittest.mock import patch

from odoo.addons.invoice_agent.models import ocr_service as ocr_module
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOcrServiceGuards(TransactionCase):
    """Guard failures must raise accountant-readable errors."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.service = cls.env["invoice.ocr.service"]
        cls.partner = cls.env.ref("base.main_partner")
        company = cls.env.company
        if not company.chart_template:
            cls.env["account.chart.template"].try_loading(
                "generic_coa",
                company=company,
                install_demo=False,
            )
        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", company.id)],
            limit=1,
        )
        if not cls.journal:
            cls.journal = cls.env["account.journal"].create(
                {
                    "name": "OCR Test Purchase Journal",
                    "type": "purchase",
                    "code": "OTP",
                },
            )

    def _attachment(
        self,
        name="scan.pdf",
        mimetype="application/pdf",
        data=b"%PDF-1.4 fake minimal pdf",
    ):
        return self.env["ir.attachment"].create(
            {
                "name": name,
                "datas": base64.b64encode(data).decode("ascii"),
                "mimetype": mimetype,
                "res_model": "account.move",
                "res_id": 0,
            },
        )

    def test_no_attachment_raises(self):
        with self.assertRaises(Exception):
            self.service._extract_text(self.env["ir.attachment"])

    def test_empty_datas_raises(self):
        attachment = self._attachment()
        attachment.write({"datas": False})
        with self.assertRaises(Exception) as ctx:
            self.service._extract_text(attachment)
        self.assertIn("no data", str(ctx.exception).lower())

    def test_oversize_attachment_raises(self):
        big = b"x" * (ocr_module.MAX_OCR_ATTACHMENT_BYTES + 1)
        attachment = self._attachment(data=big)
        with self.assertRaises(Exception) as ctx:
            self.service._extract_text(attachment)
        self.assertIn("20 MB", str(ctx.exception))

    def test_wrong_mimetype_raises(self):
        attachment = self._attachment(
            name="scan.txt",
            mimetype="text/plain",
            data=b"hello",
        )
        with self.assertRaises(Exception) as ctx:
            self.service._extract_text(attachment)
        self.assertIn("text/plain", str(ctx.exception))

    def test_corrupt_pdf_raises(self):
        # application/pdf mimetype but garbage bytes: pdf2image (poppler)
        # fails before any OCR pass — no real PDF tooling needed here.
        # Patch _check_toolchain away: the point is the poppler guard, and the
        # toolchain preflight would otherwise short-circuit on a machine
        # without the tesseract binary (e.g. the CI runner or this Windows host).
        attachment = self._attachment(data=b"this is not a pdf at all")
        with patch.object(
            self.service.__class__,
            "_check_toolchain",
            return_value=None,
        ):
            with self.assertRaises(Exception) as ctx:
                self.service._extract_text(attachment)
            self.assertIn("scan.pdf", str(ctx.exception))

    def test_empty_ocr_result_raises(self):
        """A blank page must surface as a failure, never empty 'success'."""
        attachment = self._attachment()
        # The blank-text guard lives INSIDE _ocr_images, so patching
        # _extract_pdf or _ocr_images bypasses it entirely. Run the real code
        # path instead: mock the poppler rasterizer to return one fake page,
        # and make tesseract return an empty page; the real guard must raise.
        from PIL import Image

        fake_page = Image.new("RGB", (10, 10), "white")
        with (
            patch.object(
                self.service.__class__,
                "_check_toolchain",
                return_value=None,
            ),
            patch(
                "pdf2image.convert_from_bytes",
                return_value=[fake_page],
            ),
            patch(
                "pytesseract.image_to_data",
                return_value={"text": [" ", "", "  "], "conf": [-1, -1, -1]},
            ),
        ):
            with self.assertRaises(Exception) as ctx:
                self.service._extract_text(attachment)
            self.assertIn("no text", str(ctx.exception).lower())


@tagged("post_install", "-at_install")
class TestOcrPipeline(TransactionCase):
    """State machine + batch cron with a mocked OCR service."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.service = cls.env["invoice.ocr.service"]
        cls.partner = cls.env.ref("base.main_partner")
        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "purchase")],
            limit=1,
        )
        cls.result = {"text": "INVOICE INV-1 total 100.00", "confidence": 0.92}

        # _cron_ocr_pending_bills commits/rolls back per record — Odoo forbids
        # that inside TransactionCase (its setUpClass patches commit/rollback
        # to raise). The tests here exercise the state machine (which records
        # are claimed, batch limits, poison isolation), not DB durability, so
        # no-op commit/rollback. Our patchers replace Odoo's "forbidden" ones
        # and are restored in reverse order at class cleanup.
        cls.startClassPatcher(patch.object(cls.cr, "commit", lambda: None))
        cls.startClassPatcher(patch.object(cls.cr, "rollback", lambda: None))

    def _attachment(self):
        return self.env["ir.attachment"].create(
            {
                "name": "scan.pdf",
                "datas": base64.b64encode(b"%PDF-1.4 minimal").decode("ascii"),
                "mimetype": "application/pdf",
            },
        )

    def _move(self, ocr_state="pending"):
        return self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner.id,
                "journal_id": self.journal.id,
                "ai_source_attachment_id": self._attachment().id,
                "ocr_state": ocr_state,
            },
        )

    def test_process_one_goes_pending_running_done(self):
        move = self._move()
        with patch.object(
            self.service.__class__,
            "_extract_text",
            return_value=self.result,
        ):
            self.env["account.move"]._ocr_process_one(move.id)
        move.invalidate_recordset()
        self.assertEqual(move.ocr_state, "done")
        self.assertEqual(move.ocr_confidence, 0.92)
        self.assertEqual(move.ocr_text, self.result["text"])
        # Mirrored into the legacy AI pipeline field.
        self.assertEqual(move.ai_ocr_text, self.result["text"])

    def test_process_one_failure_marks_failed(self):
        move = self._move()
        with patch.object(
            self.service.__class__,
            "_extract_text",
            side_effect=Exception("scan too dark"),
        ):
            self.env["account.move"]._ocr_process_one(move.id)
        move.invalidate_recordset()
        self.assertEqual(move.ocr_state, "failed")
        self.assertIn("scan too dark", move.ocr_error_message)

    def test_cron_processes_only_pending(self):
        done_move = self._move(ocr_state="done")
        failed_move = self._move(ocr_state="failed")
        pending_move = self._move()
        with patch.object(
            self.service.__class__,
            "_extract_text",
            return_value=self.result,
        ) as mock_extract:
            self.env["account.move"]._cron_ocr_pending_bills(batch_size=10)
        pending_move.invalidate_recordset()
        self.assertEqual(pending_move.ocr_state, "done")
        self.assertEqual(mock_extract.call_count, 1)
        self.assertEqual(done_move.ocr_state, "done")
        self.assertEqual(failed_move.ocr_state, "failed")

    def test_cron_ignores_moves_without_attachment(self):
        move = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner.id,
                "journal_id": self.journal.id,
                "ocr_state": "pending",
            },
        )
        with patch.object(
            self.service.__class__,
            "_extract_text",
            return_value=self.result,
        ) as mock_extract:
            self.env["account.move"]._cron_ocr_pending_bills(batch_size=10)
        move.invalidate_recordset()
        self.assertEqual(move.ocr_state, "pending")
        self.assertEqual(mock_extract.call_count, 0)

    def test_cron_batch_size_limits_claim(self):
        moves = [self._move() for _ in range(5)]
        with patch.object(
            self.service.__class__,
            "_extract_text",
            return_value=self.result,
        ) as mock_extract:
            self.env["account.move"]._cron_ocr_pending_bills(batch_size=2)
        self.assertEqual(mock_extract.call_count, 2)
        done_count = self.env["account.move"].search_count(
            [("id", "in", [m.id for m in moves]), ("ocr_state", "=", "done")],
        )
        self.assertEqual(done_count, 2)

    def test_one_bad_scan_does_not_poison_batch(self):
        good_1 = self._move()
        bad = self._move()
        good_2 = self._move()

        def _side_effect(attachment):
            if attachment == bad.ai_source_attachment_id:
                msg = "corrupt pdf"
                raise Exception(msg)
            return self.result

        with patch.object(
            self.service.__class__,
            "_extract_text",
            side_effect=_side_effect,
        ):
            self.env["account.move"]._cron_ocr_pending_bills(batch_size=10)

        good_1.invalidate_recordset()
        bad.invalidate_recordset()
        good_2.invalidate_recordset()
        self.assertEqual(good_1.ocr_state, "done")
        self.assertEqual(bad.ocr_state, "failed")
        self.assertEqual(good_2.ocr_state, "done")

    def test_retry_cron_recycles_stuck_running(self):
        move = self._move(ocr_state="running")
        # Age the record past the 1h threshold.
        self.env.cr.execute(
            "UPDATE account_move SET write_date = write_date - interval '2 hours' "
            "WHERE id = %s",
            (move.id,),
        )
        self.env["account.move"]._cron_retry_stuck_extractions()
        move.invalidate_recordset()
        self.assertEqual(move.ocr_state, "pending")


@tagged("post_install", "-at_install")
class TestOcrEndToEnd(TransactionCase):
    """Real PIL-rendered PDF through real Tesseract (skipped without binary)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if shutil.which("tesseract") is None:
            msg = "tesseract binary not installed in this image"
            raise unittest.SkipTest(msg)

    def test_real_pdf_end_to_end(self):
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            self.skipTest("PIL unavailable")

        image = Image.new("RGB", (1000, 300), "white")
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                36,
            )
        except OSError:
            font = ImageFont.load_default()
        draw.text((50, 100), "INVOICE 101 TOTAL 99.50", fill="black", font=font)

        buffer = io.BytesIO()
        image.save(buffer, format="PDF", resolution=300.0)
        pdf_bytes = buffer.getvalue()

        attachment = self.env["ir.attachment"].create(
            {
                "name": "real-scan.pdf",
                "datas": base64.b64encode(pdf_bytes).decode("ascii"),
                "mimetype": "application/pdf",
            },
        )
        result = self.env["invoice.ocr.service"]._extract_text(attachment)
        self.assertIn("INVOICE", result["text"].upper())
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)
