from odoo.addons.account.tests.test_account_move_out_invoice import TestAccountMoveOutInvoiceOnchanges
from odoo.tests import tagged
from odoo import fields, Command


@tagged('post_install', '-at_install')
class TestAccountMoveOutInvoiceOnchangesNoFollowup(TestAccountMoveOutInvoiceOnchanges):

    def test_invoice_no_followup(self):
        """Make sure that excluding an invoice from follow-up excludes all its receivable lines."""
        installments_payment_term = self.env['account.payment.term'].create({
            'name': "3 installments",
            'line_ids': [
                Command.create({'value_amount': 40, 'value': 'percent', 'nb_days': 0}),
                Command.create({'value_amount': 30, 'value': 'percent', 'nb_days': 30}),
                Command.create({'value_amount': 30, 'value': 'percent', 'nb_days': 60}),
            ],
        })
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.from_string('2024-08-01'),
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 1000})],
            'invoice_payment_term_id': installments_payment_term.id,
        })
        invoice_terms = invoice.line_ids.filtered(lambda line: line.display_type == 'payment_term')
        self.assertFalse(invoice.no_followup)
        self.assertEqual(invoice_terms.mapped('no_followup'), [False, False, False])

        invoice.no_followup = True
        self.assertTrue(invoice.no_followup)
        self.assertEqual(invoice_terms.mapped('no_followup'), [True, True, True])

        invoice.no_followup = False
        self.assertFalse(invoice.no_followup)
        self.assertEqual(invoice_terms.mapped('no_followup'), [False, False, False])

    def test_invoice_line_no_followup(self):
        """Make sure that excluding one receivable line from an invoice excludes all the others."""
        installments_payment_term = self.env['account.payment.term'].create({
            'name': "3 installments",
            'line_ids': [
                Command.create({'value_amount': 40, 'value': 'percent', 'nb_days': 0}),
                Command.create({'value_amount': 30, 'value': 'percent', 'nb_days': 30}),
                Command.create({'value_amount': 30, 'value': 'percent', 'nb_days': 60}),
            ],
        })
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.from_string('2024-08-01'),
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 1000})],
            'invoice_payment_term_id': installments_payment_term.id,
        })
        invoice_terms = invoice.line_ids.filtered(lambda line: line.display_type == 'payment_term')
        self.assertFalse(invoice.no_followup)
        self.assertEqual(invoice_terms.mapped('no_followup'), [False, False, False])

        invoice_terms[0].no_followup = True
        self.assertTrue(invoice.no_followup)
        self.assertEqual(invoice_terms.mapped('no_followup'), [True, True, True])

        invoice_terms[1].no_followup = False
        self.assertFalse(invoice.no_followup)
        self.assertEqual(invoice_terms.mapped('no_followup'), [False, False, False])
