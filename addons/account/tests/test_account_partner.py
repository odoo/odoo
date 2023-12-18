# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
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
