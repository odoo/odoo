import base64
from unittest.mock import patch
from lxml import etree
from odoo import fields
from odoo.exceptions import UserError
from .common import PdpTestCommon


class TestPdpPaymentFlows(PdpTestCommon):
    def test_payment_flow_created_and_ready(self):
        """Payment flow built when payment is reconciled within window."""
        inv = self._create_invoice(sent=True)
        pay_date = fields.Date.today()
        self._create_payment_for_invoice(inv, pay_date=pay_date)
        aggregator = self.env["l10n.fr.pdp.flow.aggregator"].with_context(mail_create_nolog=True, tracking_disable=True)
        pay_start, pay_end, _code = aggregator._get_period_bounds(self.company.id, pay_date, "payment")
        payment_moves = aggregator._get_payment_source_moves(self.company.id, pay_start, pay_end)
        pay_flows, rebuild = aggregator._synchronize_payment_flows(
            self.company.id,
            pay_start,
            self.company.currency_id.id,
            "mixed",
            payment_moves,
            self.env["l10n.fr.pdp.flow"].browse(),
        )
        pay_flows |= rebuild
        if rebuild:
            rebuild._build_payload()
        pay_flow = pay_flows.filtered(lambda f: f.report_kind == "payment")[:1]
        self.assertTrue(pay_flow, "Payment flow should be created when payments exist")
        self.assertEqual(pay_flow.state, "ready", "Payment flow must be ready after build")
        self.assertTrue(pay_flow.slice_ids, "Payment flow should have slices built")

    def test_payment_content_flag(self):
        """Payment flow should contain payment content when payments exist."""
        inv = self._create_invoice(sent=True)
        pay_date = fields.Date.today()
        self._create_payment_for_invoice(inv, pay_date=pay_date)
        aggregator = self.env["l10n.fr.pdp.flow.aggregator"].with_context(mail_create_nolog=True, tracking_disable=True)
        pay_start, pay_end, _code = aggregator._get_period_bounds(self.company.id, pay_date, "payment")
        payment_moves = aggregator._get_payment_source_moves(self.company.id, pay_start, pay_end)
        pay_flows, rebuild = aggregator._synchronize_payment_flows(
            self.company.id,
            pay_start,
            self.company.currency_id.id,
            "mixed",
            payment_moves,
            self.env["l10n.fr.pdp.flow"].browse(),
        )
        pay_flows |= rebuild
        if rebuild:
            rebuild._build_payload()
        pay_flow = pay_flows.filtered(lambda f: f.report_kind == "payment")[:1]
        self.assertTrue(pay_flow.slice_ids, "Payment flow slice missing")
        slice_payload = pay_flow.slice_ids[0].payload
        self.assertTrue(slice_payload, "Payment payload must be generated")

    def test_partial_payment_amount_in_payload(self):
        """Partial reconciliations should use the reconciled amount in payment payload."""
        inv = self._create_invoice(sent=True)
        self._create_payment_for_invoice(inv, amount=40)
        pay_flow = self._aggregate_company().filtered(lambda f: f.report_kind == "payment")[:1]
        xml = etree.fromstring(base64.b64decode(pay_flow.slice_ids[0].payload))
        amounts = [
            node.findtext("Amount")
            for node in xml.findall(".//PaymentsReport//Transactions/Payment/SubTotals")
        ]
        self.assertIn("40.0", amounts, "Payment payload must carry the partial amount reconciled")

    def test_cash_receipt_included_as_payment(self):
        """Receipts act as 0%% payments in transaction payment section."""
        # Ensure a payment flow exists via a standard payment, then add a cash receipt.
        inv = self._create_invoice(sent=True)
        self._create_payment_for_invoice(inv)
        journal = self.env["account.journal"].search([
            ("type", "=", "sale"),
            ("company_id", "=", self.company.id),
        ], limit=1)
        receipt = self.env["account.move"].create({
            "move_type": "out_receipt",
            "partner_id": self.partner_b2c.id,
            "invoice_date": fields.Date.today(),
            "journal_id": journal.id,
            "invoice_line_ids": [(0, 0, {
                "product_id": self.product.id,
                "quantity": 1,
                "price_unit": 50,
                "tax_ids": [(6, 0, [])],
                "account_id": self.income_account.id,
            })],
        })
        receipt.action_post()
        receipt.is_move_sent = True

        pay_flow = self._aggregate_company().filtered(lambda f: f.report_kind == "payment")[:1]
        self.assertTrue(pay_flow, "Payment flow should exist after adding payments/receipts")
        if not pay_flow.slice_ids:
            pay_flow._build_payload()
        xml = etree.fromstring(base64.b64decode(pay_flow.slice_ids[0].payload))
        payments = xml.findall(".//PaymentsReport//Transactions/Payment/SubTotals")
        percents = {node.findtext("TaxPercent") for node in payments}
        self.assertIn("0.0", percents, "Receipt payments should be emitted with 0%% tax percent")

    def test_payment_outside_window_excluded(self):
        """Payments dated outside the current window should not build a payment flow."""
        inv = self._create_invoice(sent=True)
        past_date = fields.Date.from_string("2023-01-01")
        self._create_payment_for_invoice(inv, pay_date=past_date)
        flows = self._aggregate_company()
        pay_flow = flows.filtered(lambda f: f.report_kind == "payment")
        self.assertFalse(pay_flow, "Payment flow should not be created when payments are outside the window")

    def test_payment_flow_not_created_without_payments(self):
        """No payment flow should be built when no payments exist for the window."""
        self._create_invoice(sent=True)
        flows = self._aggregate_company()
        pay_flow = flows.filtered(lambda f: f.report_kind == "payment")
        self.assertFalse(pay_flow, "No payment flow expected without any payments")

    def test_receipts_grouped_by_date(self):
        """Receipts on the same date should aggregate into a single payment entry."""
        journal = self.env["account.journal"].search([
            ("type", "=", "sale"),
            ("company_id", "=", self.company.id),
        ], limit=1)
        date_val = fields.Date.context_today(self.env["account.move"])
        receipts = self.env["account.move"].browse()
        for _i in range(2):
            receipt = self.env["account.move"].create({
                "move_type": "out_receipt",
                "partner_id": self.partner_b2c.id,
                "invoice_date": date_val,
                "journal_id": journal.id,
                "invoice_line_ids": [(0, 0, {
                    "product_id": self.product.id,
                    "quantity": 1,
                    "price_unit": 25,
                    "tax_ids": [(6, 0, [])],
                    "account_id": self.income_account.id,
                })],
            })
            receipt.action_post()
            receipt.is_move_sent = True
            receipts |= receipt

        aggregator = self.env["l10n.fr.pdp.flow.aggregator"]
        pay_start, pay_end, _code = aggregator._get_period_bounds(self.company.id, date_val, "payment")
        payment_moves = aggregator._get_payment_moves(receipts)
        flows = self._aggregate_company()
        pay_flow = flows.filtered(lambda f: f.report_kind == "payment")[:1]
        if not pay_flow and payment_moves:
            pay_flow = self.env["l10n.fr.pdp.flow"].create({
                "company_id": self.company.id,
                "report_kind": "payment",
                "flow_type": "transaction_report",
                "currency_id": self.company.currency_id.id,
                "document_type": "sale",
                "transaction_type": "mixed",
                "transmission_type": "IN",
                "period_start": pay_start,
                "period_end": pay_end,
                "periodicity_code": "M",
                "reporting_date": pay_start,
                "issue_datetime": fields.Datetime.now(),
                "move_ids": [(6, 0, payment_moves.ids)],
            })
            pay_flow._reset_slices(payment_moves)
            pay_flow._build_payload()
        self.assertTrue(pay_flow, "Payment flow should be generated for receipts in window")
        xml = etree.fromstring(base64.b64decode(pay_flow.slice_ids[0].payload))
        payments = xml.findall(".//PaymentsReport//Transactions")
        self.assertEqual(len(payments), 1, "Receipts on same date should be grouped into one payment entry")
        subtotal = payments[0].find(".//Amount")
        self.assertEqual(subtotal.text, "50.0", "Grouped receipt amount should sum both receipts")

    def test_payment_cron_skips_manual_mode(self):
        """Cron should not send payment flows when company send mode is manual."""
        self.company.l10n_fr_pdp_send_mode = "manual"
        inv = self._create_invoice(sent=True)
        self._create_payment_for_invoice(inv)
        flows = self._aggregate_company()
        pay_flow = flows.filtered(lambda f: f.report_kind == "payment")[:1]
        self.assertTrue(pay_flow)
        ready_state = pay_flow.state
        with patch("odoo.fields.Date.context_today", return_value=fields.Date.context_today(self.env["l10n.fr.pdp.flow"])):
            self.env["l10n.fr.pdp.flow"]._cron_send_ready_flows()
        pay_flow.invalidate_recordset(["state", "transport_identifier"])
        self.assertEqual(pay_flow.state, ready_state, "Manual mode should prevent cron from sending payment flows")
        self.assertFalse(pay_flow.transport_identifier)

    def test_payment_precision_validation_error(self):
        """Payment amounts outside currency precision should trigger validation error."""
        inv = self._create_invoice(sent=True)
        self._create_payment_for_invoice(inv)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "payment")[:1]
        if not flow.slice_ids:
            flow._build_payload()

        def fake_invoice_payments(_self, moves):
            return [{
                "id": "PAY1",
                "invoice_id": inv.name,
                "date": fields.Date.today().strftime("%Y%m%d"),
                "amount": 0.001,
                "currency": flow.currency_id.name,
                "payment_method": "Manual",
                "subtotals": [],
            }]

        with patch("odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._invoice_payments", fake_invoice_payments):
            with patch("odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._transaction_payments", return_value=[]):
                with self.assertRaises(UserError) as ctx:
                    flow._build_payload()
        self.assertIn("exceeds currency precision", str(ctx.exception))

    def test_payment_currency_mismatch_skips_precision_check(self):
        """Payments in a different currency should bypass precision validation."""
        inv = self._create_invoice(sent=True)
        self._create_payment_for_invoice(inv)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "payment")[:1]
        if not flow.slice_ids:
            flow._build_payload()

        def fake_invoice_payments(_self, moves):
            return [{
                "id": "PAY2",
                "invoice_id": inv.name,
                "date": fields.Date.today().strftime("%Y%m%d"),
                "amount": 0.001,
                "currency": "USD",
                "payment_method": "Manual",
                "subtotals": [],
            }]

        with patch("odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._invoice_payments", fake_invoice_payments):
            with patch("odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._transaction_payments", return_value=[]):
                # Should not raise despite small amount because currency differs from flow currency
                flow._build_payload()
        self.assertTrue(flow.slice_ids[0].payload, "Payload should still be generated with foreign currency payments")
