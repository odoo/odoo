from odoo.addons.account_reports.tests.test_partner_ledger_report import TestPartnerLedgerReport

from odoo import Command, fields
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestNoFollowupPartnerLedgerReport(TestPartnerLedgerReport):

    def test_partner_ledger_toggle_followup(self):
        """Make sure that toggling the followup also (and only) toggles other lines of the same invoice."""
        installments_payment_term = self.env['account.payment.term'].create({
            'name': "3 installments",
            'line_ids': [
                Command.create({'value_amount': 40, 'value': 'percent', 'nb_days': 0}),
                Command.create({'value_amount': 30, 'value': 'percent', 'nb_days': 30}),
                Command.create({'value_amount': 30, 'value': 'percent', 'nb_days': 60}),
            ],
        })
        invoices = self.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'invoice_date': fields.Date.from_string('2024-08-01'),
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 1000})],
                'invoice_payment_term_id': installments_payment_term.id,
            },
            {
                'move_type': 'out_invoice',
                'invoice_date': fields.Date.from_string('2024-08-10'),
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 500})],
                'invoice_payment_term_id': installments_payment_term.id,
            },
        ])
        invoices.action_post()
        invoice_name = invoices[0].name
        options = self._generate_options(self.report, '2024-01-01', '2024-12-31', default_options={'unfold_all': True})
        lines = self.report._get_lines(options)
        line_ids = [line['id'] for line in lines]
        invoice_1_line_ids = [line['id'] for line in lines if invoice_name in line['name']]
        self.assertEqual(
            self.env['account.partner.ledger.report.handler'].action_toggle_no_followup(invoice_1_line_ids[0], line_ids)['updated_line_ids'],
            invoice_1_line_ids,
        )
