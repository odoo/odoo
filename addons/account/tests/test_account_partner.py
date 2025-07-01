# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install', '-at_install')
class TestAccountPartner(AccountTestInvoicingCommon):

    @freeze_time("2023-05-31")
    def test_days_sales_outstanding(self):
        partner = self.env['res.partner'].create({'name': 'MyCustomer'})
        self.assertEqual(partner.days_sales_outstanding, 0.0)
        move_1 = self.init_invoice("out_invoice", partner, invoice_date="2023-01-01", amounts=[3000], taxes=self.tax_sale_a)
        self.assertEqual(partner.days_sales_outstanding, 0.0)
        move_1.action_post()
        self.env.invalidate_all() #needed to force the update of partner.credit
        self.assertEqual(partner.days_sales_outstanding, 150) #DSO = number of days since move_1
        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=move_1.ids).create({
            'amount': move_1.amount_total,
            'partner_id': partner.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
        })._create_payments()
        self.env.invalidate_all()
        self.assertEqual(partner.days_sales_outstanding, 0.0)
        self.init_invoice("out_invoice", partner, "2023-05-15", amounts=[1500], taxes=self.tax_sale_a, post=True)
        self.env.invalidate_all()
        self.assertEqual(partner.days_sales_outstanding, 50)

    def test_account_move_count(self):
        self.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'date': '2017-01-01',
                'invoice_date': '2017-01-01',
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [(0, 0, {'name': 'aaaa', 'price_unit': 100.0})],
            },
            {
                'move_type': 'in_invoice',
                'date': '2017-01-01',
                'invoice_date': '2017-01-01',
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [(0, 0, {'name': 'aaaa', 'price_unit': 100.0})],
            },
        ]).action_post()

        self.assertEqual(self.partner_a.supplier_rank, 1)
        self.assertEqual(self.partner_a.customer_rank, 1)

    def test_manually_write_partner_id(self):
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2025-04-29',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 500.0,
                'tax_ids': [],
            })],
        })
        move.action_post()
        reversal = move._reverse_moves(cancel=True)

        receivable_lines = (move + reversal).line_ids.filtered(lambda l: l.display_type == 'payment_term')

        # Changing the partner should be possible despite being in locked periods as long as the VAT is the same
        move.company_id.fiscalyear_lock_date = move.date

        # Initially, move's commercial partner should be partner_a
        self.assertEqual(move.commercial_partner_id, self.partner_a)
        self.assertEqual(receivable_lines.mapped('reconciled'), [True, True])

        self.partner_a.parent_id = self.partner_b

        # Assert accounting move and move lines now use new commercial partner
        self.assertEqual(move.commercial_partner_id, self.partner_b)
        self.assertTrue(
            all(line.partner_id == self.partner_b for line in move.line_ids),
            "All move lines should be reassigned to the new commercial partner."
        )
        self.assertEqual(receivable_lines.mapped('reconciled'), [True, True])

    def test_manually_write_partner_id_different_vat(self):
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2025-04-29',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 500.0,
            })],
        })
        move.action_post()
        self.partner_a.vat = 'SOMETHING'
        self.partner_b.vat = 'DIFFERENT'
        with self.assertRaisesRegex(UserError, "different Tax ID"):
            self.partner_a.parent_id = self.partner_b
