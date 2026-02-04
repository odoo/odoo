# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import UserError
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

    def test_res_partner_bank(self):
        partner = self.env['res.partner'].create({'name': 'MyCustomer'})
        account = self.env['res.partner.bank'].create({
            'acc_number': '123456789',
            'partner_id': partner.id,
        })
        account.env.user.groups_id |= self.env.ref('account.group_validate_bank_account')
        account.allow_out_payment = True

        with self.assertRaisesRegex(UserError, "has been trusted"), self.cr.savepoint():
            account.write({'acc_number': '1234567890999'})
        with self.assertRaisesRegex(UserError, "has been trusted"), self.cr.savepoint():
            account.write({'sanitized_acc_number': '1234567890999'})
        with self.assertRaisesRegex(UserError, "has been trusted"), self.cr.savepoint():
            account.write({'partner_id': self.env['res.partner'].create({'name': 'MyCustomer 2'}).id})

        account.allow_out_payment = False
        account.write({'acc_number': '1234567890999000'})

        account.env.user.groups_id -= self.env.ref('account.group_validate_bank_account')
        with self.assertRaisesRegex(UserError, "You do not have the rights to trust"), self.cr.savepoint():
            account.write({'allow_out_payment': True})
