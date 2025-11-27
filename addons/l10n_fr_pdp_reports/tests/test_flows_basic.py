from unittest.mock import patch
from base64 import b64decode

from lxml import etree

from odoo import Command, fields
from odoo.tests.common import tagged

from odoo.addons.l10n_fr_pdp_reports.models.pdp_payload import PdpPayloadBuilder

from .common import PdpTestCommon


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestPdpFlowsBasic(PdpTestCommon):
    def test_no_activity_does_not_create_flow(self):
        """No transaction/payment source move in period -> no flow generated."""
        flows = self._run_aggregation()
        self.assertFalse(flows, 'No flow should be generated when there is no activity in the period')
        stored_flows = self.env['l10n.fr.pdp.flow'].search([('company_id', '=', self.company.id)])
        self.assertFalse(stored_flows, 'Database should not contain PDP flows when there is no activity')

    def test_single_invoice_ready_flow(self):
        """IN transaction flow built and ready for a single sent invoice."""
        self._create_invoice(sent=True)
        flows = self._run_aggregation()
        flow = flows.filtered(lambda f: f.report_kind == 'transaction')
        self.assertGreaterEqual(len(flow), 1, 'Expected at least one transaction flow')
        flow = flow[:1]
        self.assertEqual(flow.state, 'ready', 'Flow should be ready after payload build')
        self.assertEqual(flow.transmission_type, 'IN', 'First flow must be IN')
        self.assertTrue(flow.payload, 'Payload must be generated')

    def test_invoice_not_sent_flags_error_status(self):
        """Posted invoice not sent -> PDP status error."""
        inv = self._create_invoice(sent=False)
        self._run_aggregation()
        inv.invalidate_recordset(['l10n_fr_pdp_status'])
        self.assertEqual(inv.l10n_fr_pdp_status, 'error', 'Unsent posted invoice must be in PDP error')

    def test_b2c_daily_summary_multiple_days(self):
        """B2C invoices on different days generate per-day summaries in payload."""
        day1 = fields.Date.from_string('2025-01-05')
        day2 = fields.Date.from_string('2025-01-06')
        self._create_invoice(date_val=day1, sent=True)
        self._create_invoice(date_val=day2, sent=True)
        flows = self._run_aggregation()
        tx_flows = flows.filtered(lambda f: f.report_kind == 'transaction')
        self.assertTrue(tx_flows, 'Transaction flow should exist')
        for flow in tx_flows:
            dates = {m.invoice_date or m.date for m in flow.move_ids}
            builder = PdpPayloadBuilder(flow)
            report_vals = builder._build_transaction_report_vals(flow.move_ids)
            summaries = report_vals.get('transaction_summaries') or []
            self.assertEqual(
                len(summaries), len(dates),
                'Flow %s expected %s summaries for dates %s, got %s' % (
                    flow.id, len(dates), dates, len(summaries)),
            )

    def test_flow_rebuilds_when_entering_grace(self):
        """A pending flow should be rebuilt when moving from open to grace."""
        inv_date = fields.Date.from_string('2025-02-05')
        self._create_invoice(date_val=inv_date, sent=True)

        open_day = fields.Date.from_string('2025-02-07')   # within period 1-10
        grace_day = fields.Date.from_string('2025-02-15')  # after period end, before due date (20th)

        with patch('odoo.fields.Date.context_today', return_value=open_day):
            flows = self._run_aggregation()
        flow = flows.filtered(lambda f: f.report_kind == 'transaction')[:1]
        with patch('odoo.fields.Date.context_today', return_value=open_day):
            flow.invalidate_recordset(['state', 'period_status'])
            self.assertEqual(flow.period_status, 'open')
            self.assertEqual(flow.state, 'pending')

        with patch('odoo.fields.Date.context_today', return_value=grace_day):
            self._aggregate_company()
        with patch('odoo.fields.Date.context_today', return_value=grace_day):
            flow.invalidate_recordset(['state', 'period_status'])
            self.assertEqual(flow.period_status, 'grace')
            self.assertEqual(flow.state, 'ready')

    def test_build_payload_reuses_single_xml_attachment(self):
        """Repeated payload builds must keep a single visible XML attachment per flow."""
        self._create_invoice(sent=True)
        flows = self._run_aggregation()
        flow = flows.filtered(lambda f: f.report_kind == 'transaction')[:1]
        self.assertTrue(flow, 'Transaction flow should exist')

        attachment_model = self.env['ir.attachment']
        domain = [
            ('res_model', '=', 'l10n.fr.pdp.flow'),
            ('res_id', '=', flow.id),
            ('mimetype', '=', 'application/xml'),
            ('res_field', '=', False),
        ]
        first_attachment = attachment_model.search(domain)
        self.assertEqual(len(first_attachment), 1, 'A single XML attachment should exist after first build')

        flow.action_build_payload_manual()

        second_attachment = attachment_model.search(domain)
        self.assertEqual(len(second_attachment), 1, 'Rebuild should replace the XML attachment, not duplicate it')
        self.assertEqual(second_attachment.id, first_attachment.id, 'Attachment record should be reused on rebuild')

    def test_closed_period_with_only_invalid_moves_keeps_flow_error(self):
        """Closed-period flow with zero valid moves should stay in error for correction/rebuild."""
        self._create_invoice(sent=False)
        flows = self._run_aggregation()
        flow = flows.filtered(lambda f: f.report_kind == 'transaction')[:1]
        self.assertTrue(flow, 'Transaction flow should exist')
        self.assertEqual(flow.period_status, 'closed', 'Default test date should place this flow in closed period')
        self.assertEqual(flow.state, 'error', 'Flow should stay in error when all moves are invalid in closed period')
        self.assertFalse(flow.payload, 'Error flow with no valid moves should not keep a payload')

    def test_tracking_identifier_is_unique_per_company(self):
        """Two flows with identical attributes must not share the same TT-1 identifier."""
        flow_model = self.env['l10n.fr.pdp.flow']
        common_vals = {
            'company_id': self.company.id,
            'reporting_date': self.TEST_INVOICE_DATE,
            'currency_id': self.company.currency_id.id,
            'document_type': 'sale',
            'report_kind': 'transaction',
            'operation_type': 'sale',
            'transaction_type': 'b2c',
            'transmission_type': 'IN',
        }
        flow_a = flow_model.create(common_vals)
        flow_b = flow_model.create(common_vals)

        (flow_a | flow_b)._ensure_tracking_id()

        self.assertTrue(flow_a.tracking_id, 'Flow A should have a tracking identifier')
        self.assertTrue(flow_b.tracking_id, 'Flow B should have a tracking identifier')
        self.assertNotEqual(flow_a.tracking_id, flow_b.tracking_id, 'TT-1 must be unique per flow')
        self.assertLessEqual(len(flow_a.tracking_id), 50, 'TT-1 must respect max length')
        self.assertLessEqual(len(flow_b.tracking_id), 50, 'TT-1 must respect max length')

    def test_service_receipt_generates_transaction_and_payment_flows(self):
        """B2C service receipts (without invoice reconciliation) must feed 10.3 and 10.4."""
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company.id),
        ], limit=1)
        receipt = self.env['account.move'].create({
            'move_type': 'out_receipt',
            'partner_id': self.partner_b2c.id,
            'invoice_date': self.TEST_INVOICE_DATE,
            'journal_id': journal.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.service_product.id,
                'quantity': 1,
                'price_unit': 100,
                'tax_ids': [Command.set(self.tax_20.ids)],
                'account_id': self.income_account.id,
            })],
        })
        receipt.action_post()
        receipt.is_move_sent = True

        flows = self._run_aggregation()
        tx_flow = flows.filtered(lambda f: f.report_kind == 'transaction' and receipt in f.move_ids)[:1]
        pay_flow = flows.filtered(lambda f: f.report_kind == 'payment' and receipt in f.move_ids)[:1]

        self.assertTrue(tx_flow, 'Service receipt should be reported in transaction flow (10.3).')
        self.assertTrue(pay_flow, 'Service receipt should be reported in payment flow (10.4).')

        tx_xml = etree.fromstring(b64decode(tx_flow.payload))
        tx_summary = tx_xml.find(".//TransactionsReport/Transactions[CategoryCode='TPS1']")
        self.assertIsNotNone(tx_summary, '10.3 should contain a TPS1 summary for service receipt.')

        pay_xml = etree.fromstring(b64decode(pay_flow.payload))
        pay_subtotals = pay_xml.findall('.//PaymentsReport//Transactions/Payment/SubTotals')
        self.assertTrue(pay_subtotals, '10.4 should contain payment subtotals for service receipt.')
