import base64
from unittest.mock import patch
from lxml import etree

from odoo import fields
from odoo.exceptions import UserError
from .common import PdpTestCommon


class TestPdpValidationAndPayload(PdpTestCommon):
    def test_company_identifier_validation_errors(self):
        """Missing company SIRET/VAT should block payload build with a clear error."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "transaction")[:1]
        self.company.write({"siret": False})
        self.company.partner_id.write({"vat": False})

        with self.assertRaises(UserError) as ctx:
            flow._build_payload()
        message = str(ctx.exception)
        self.assertIn("missing its SIRET", message)
        self.assertIn("missing its VAT number", message)

    def test_invalid_identifier_and_due_code_block_payload(self):
        """Invalid TT-1 identifier and invalid TT-64 code must raise validation errors."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "transaction")[:1]
        flow.name = "Bad  Identifier"  # double space violates TT-1 format

        with patch("odoo.addons.l10n_fr_pdp_reports.models.pdp_flow.PdpFlow._is_valid_due_date_code", return_value=False):
            with self.assertRaises(UserError) as ctx:
                flow._build_payload()
        message = str(ctx.exception)
        self.assertIn("TT-1", message)
        self.assertIn("tax due date type code", message)

    def test_international_invalid_vat_sets_error_moves(self):
        """Buyer VAT invalid on international invoice should be tracked in error_move_ids."""
        bad_partner = self.partner_international.with_context(no_vat_validation=True)
        bad_partner.vat = "BE000"
        inv = self._create_invoice(partner=bad_partner, sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "transaction")[:1]
        self.assertTrue(flow)

        self.assertIn(inv, flow.error_move_ids)
        self.assertIn(inv, flow.slice_ids[:1].invalid_move_ids)
        self.assertEqual(flow.state, "error")

    def test_discount_adds_allowance_and_tax_fallback(self):
        """Discounted lines create allowance charges and 0%% tax breakdown when no tax lines."""
        journal = self.env["account.journal"].search([
            ("type", "=", "sale"),
            ("company_id", "=", self.company.id),
        ], limit=1)
        move = self.env["account.move"].with_company(self.company.id).create({
            "move_type": "out_invoice",
            "partner_id": self.partner_international.id,
            "invoice_date": fields.Date.today(),
            "journal_id": journal.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Discounted line",
                "quantity": 1,
                "price_unit": 100,
                "discount": 10,
                "tax_ids": [],
                "account_id": self.income_account.id,
            })],
        })
        move.action_post()
        move.is_move_sent = True

        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "transaction")[:1]
        payload_xml = etree.fromstring(base64.b64decode(flow.slice_ids[0].payload))

        allowances = payload_xml.findall(".//Invoice/AllowanceCharge")
        self.assertTrue(allowances, "AllowanceCharge node should be present when a discount exists")
        tax_subtotals = payload_xml.findall(".//Invoice/TaxSubTotal")
        percents = {node.find("TaxCategory/Percent").text for node in tax_subtotals}
        self.assertIn("0.0", percents)

    def test_payload_metadata_checksum_and_business_process(self):
        """Payload must include namespace/schema, checksum, business process, and PRD notes."""
        self._create_invoice(partner=self.partner_international, sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "transaction")[:1]
        slice_rec = flow.slice_ids[0]
        payload_xml = etree.fromstring(base64.b64decode(slice_rec.payload))

        self.assertTrue(slice_rec.payload_sha256, "SHA-256 checksum must be stored on the slice")
        self.assertEqual(payload_xml.tag, "Report")
        tax_nodes = payload_xml.findall(".//TaxSubTotal")
        self.assertTrue(tax_nodes, "TaxSubTotal casing should match the schema")

        bp = payload_xml.find(".//Invoice/BusinessProcess")
        self.assertIsNotNone(bp, "BusinessProcess block should be present for invoices")
        self.assertEqual(bp.find("ID").text, "S1")
        self.assertIn("urn.cpro.gouv.fr:1p0:ereporting", bp.find("TypeID").text)

        prd_code = payload_xml.find(".//Invoice/Line/Note/Code")
        self.assertEqual(prd_code.text, "PRD")

    def test_missing_b2c_summary_triggers_validation_error(self):
        """When B2C transactions exist but summaries are empty, validation should fail."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "transaction")[:1]
        with patch("odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._transaction_summaries", return_value=[]):
            with self.assertRaises(UserError) as ctx:
                flow._build_payload()
        self.assertIn("must include aggregated B2C data", str(ctx.exception))

    def test_missing_vat_breakdown_in_summary_is_error(self):
        """B2C summary without VAT breakdown should raise validation error."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "transaction")[:1]
        fake_summary = [{
            "date": flow._format_date(fields.Date.today()),
            "currency": flow.currency_id.name,
            "tax_due_date_type_code": "3",
            "category_code": flow._get_transaction_category_code("b2c"),
            "tax_exclusive_amount": 100,
            "tax_total": 0,
            "transactions_count": 1,
            "vat_breakdown": [],
        }]
        with patch("odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._transaction_summaries", return_value=fake_summary):
            with self.assertRaises(UserError) as ctx:
                flow._build_payload()
        self.assertIn("VAT breakdown", str(ctx.exception))

    def test_unsupported_note_subject_raises_error(self):
        """Notes with unsupported subjects should trigger validation error."""
        self._create_invoice(partner=self.partner_international, sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "transaction")[:1]

        def fake_notes(move):
            return [{"subject": "BAD", "content": "Invalid"}]

        with patch("odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._invoice_notes", lambda self, move: fake_notes(move)):
            with self.assertRaises(UserError) as ctx:
                flow._build_payload()
        self.assertIn("unsupported note subject", str(ctx.exception))

    def test_issue_datetime_format_invalid(self):
        """Invalid issue datetime should raise validation error."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "transaction")[:1]
        with patch("odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._is_valid_issue_datetime", return_value=False):
            with self.assertRaises(UserError) as ctx:
                flow._build_payload()
        self.assertIn("format 204", str(ctx.exception))

    def test_payload_render_failure_raises_user_error(self):
        """XML render failure should raise UserError with details."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "transaction")[:1]
        with patch("odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._validate", return_value=None), \
                patch("odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.etree.fromstring", side_effect=etree.XMLSyntaxError("bad", None, 0, 0)):
            with self.assertRaises(UserError) as ctx:
                flow._build_payload()
        self.assertIn("Failed to render transaction report", str(ctx.exception))

    def test_credit_note_includes_preceding_reference(self):
        """International credit note should include preceding invoice reference when linked."""
        inv = self._create_invoice(partner=self.partner_international, sent=True)
        refund = inv._reverse_moves(default_values_list=[{
            "journal_id": inv.journal_id.id,
            "invoice_date": inv.invoice_date,
        }], cancel=False)
        refund.action_post()
        refund.is_move_sent = True
        refund.reversed_entry_id = inv
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "transaction")[:1]
        refund_slice = flow.slice_ids.filtered(lambda s: any(m.move_type == "out_refund" for m in s.move_ids))[:1]
        self.assertTrue(refund_slice, "Refund slice should be present")
        payload_xml = etree.fromstring(base64.b64decode(refund_slice.payload))
        ref = payload_xml.find(".//Invoice[TypeCode='381']/ReferencedDocument")
        self.assertIsNotNone(ref, "ReferencedDocument should be present on linked credit note")
        self.assertEqual(ref.findtext("ID"), inv.name)

    def test_credit_note_without_origin_has_no_preceding_reference(self):
        """Refund without reversed_entry should not include a preceding reference block."""
        refund = self._create_invoice(partner=self.partner_international, sent=True)
        refund.write({"move_type": "out_refund"})
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "transaction")[:1]
        refund_slice = flow.slice_ids.filtered(lambda s: any(m.move_type == "out_refund" for m in s.move_ids))[:1]
        payload_xml = etree.fromstring(base64.b64decode(refund_slice.payload))
        ref = payload_xml.find(".//Invoice[TypeCode='381']/ReferencedDocument")
        self.assertIsNone(ref, "Refund without origin should not include ReferencedDocument")

    def test_transport_request_profile_and_direction_present(self):
        """Transport request must include flowProfile and flowDirection fields."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "transaction")[:1]
        flow._build_payload()
        request = flow._prepare_transport_request(flow.slice_ids[:1])
        self.assertEqual(request.get("flowProfile"), flow.flow_profile)
        self.assertEqual(request.get("flowDirection"), flow.flow_direction)

    def test_allowance_with_tax_keeps_tax_percent(self):
        """Discount with tax should generate allowance including tax percent."""
        journal = self.env["account.journal"].search([
            ("type", "=", "sale"),
            ("company_id", "=", self.company.id),
        ], limit=1)
        move = self.env["account.move"].with_company(self.company.id).create({
            "move_type": "out_invoice",
            "partner_id": self.partner_international.id,
            "invoice_date": fields.Date.today(),
            "journal_id": journal.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Discounted",
                "quantity": 1,
                "price_unit": 100,
                "discount": 10,
                "tax_ids": [(6, 0, self.tax_20.ids)],
                "account_id": self.income_account.id,
            })],
        })
        move.action_post()
        move.is_move_sent = True

        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "transaction")[:1]
        payload_xml = etree.fromstring(base64.b64decode(flow.slice_ids[0].payload))
        allowances = payload_xml.findall(".//Invoice/AllowanceCharge")
        self.assertTrue(allowances, "AllowanceCharge should exist for discounted line with tax")
        percents = {node.findtext("TaxPercent") for node in allowances}
        self.assertTrue(any(p.startswith("20") for p in percents), "TaxPercent should reflect the tax rate")

    def test_b2c_currency_mismatch_skips_precision_validation(self):
        """B2C summary in foreign currency should not trigger precision error."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "transaction")[:1]
        fake_summary = [{
            "date": flow._format_date(fields.Date.today()),
            "currency": "USD",
            "tax_due_date_type_code": "3",
            "category_code": flow._get_transaction_category_code("b2c"),
            "tax_exclusive_amount": 0.001,
            "tax_total": 0.0,
            "transactions_count": 1,
            "vat_breakdown": [{"vat_rate": 0.0, "amount_untaxed": 0.001, "amount_tax": 0.0}],
        }]
        with patch("odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._transaction_summaries", return_value=fake_summary):
            flow._build_payload()
        self.assertTrue(flow.slice_ids[0].payload, "Payload should build even with foreign currency B2C summary")
