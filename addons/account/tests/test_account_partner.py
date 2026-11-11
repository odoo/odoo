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
        self.env.user.groups_id = (
            self.env.ref('base.group_partner_manager')
            + self.env.ref('account.group_account_user')
            + self.env.ref('account.group_validate_bank_account')
        )
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

    def test_res_partner_bank_from_branch(self):
        branch = self.env['res.company'].create({
            'name': 'branch',
            'parent_id': self.env.company.id,
        })

        partner = self.env['res.partner'].create({
            'name': 'partner test',
            'company_id': self.env.company.id,
        })

        bank_account = self.env['res.partner.bank'].create({
            'acc_number': '123456789',
            'partner_id': partner.id,
        })

        # Should be able to create a move in the branch with the bank account
        self.env['account.move'].with_company(branch).create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'partner_bank_id': bank_account.id,
        })

    def test_invoice_partner_display_name_unchanged_data_reload(self):
        partner = self._load_partner_data({'name': 'Walk-in Customer', 'email': 'walk-in@example.com'})
        invoice = self.init_invoice('out_invoice', partner, amounts=[100])
        self._mark_invoice_partner_display_name_stale(invoice)

        self._load_partner_data({'name': 'Walk-in Customer', 'email': 'walk-in@example.com'}, update=True)
        self.assertEqual(invoice.invoice_partner_display_name, 'stale',
                         "Reloading unchanged partner data must not recompute the partner's moves")

    def test_invoice_partner_display_name_changed_data_reload(self):
        partner = self._load_partner_data({'name': 'Walk-in Customer', 'email': 'walk-in@example.com'})
        invoice = self.init_invoice('out_invoice', partner, amounts=[100])
        self._mark_invoice_partner_display_name_stale(invoice)

        self._load_partner_data({'name': 'Final Consumer', 'email': 'walk-in@example.com'}, update=True)
        self.assertEqual(invoice.invoice_partner_display_name, 'Final Consumer',
                         "Reloading a renamed partner must recompute the partner's moves")

    def test_invoice_partner_display_name_partner_edit_without_rename(self):
        partner = self.env['res.partner'].create({'name': 'Walk-in Customer'})
        invoice = self.init_invoice('out_invoice', partner, amounts=[100])
        self._mark_invoice_partner_display_name_stale(invoice)

        partner.write({
            'email': 'walk-in@example.com',
            'country_id': self.env.ref('base.us').id,
            'state_id': self.env.ref('base.state_us_5').id,
        })
        self.assertEqual(invoice.invoice_partner_display_name, 'stale',
                         "Editing partner fields that do not change its name must not recompute its moves")

    def test_invoice_partner_display_name_parent_rename(self):
        company = self.env['res.partner'].create({'name': 'Customer Company', 'is_company': True})
        invoice_address = self.env['res.partner'].create({
            'name': 'Invoice Address',
            'type': 'invoice',
            'parent_id': company.id,
        })
        invoice = self.init_invoice('out_invoice', invoice_address, amounts=[100])

        company.name = 'Renamed Company'
        self.assertEqual(invoice.invoice_partner_display_name, 'Renamed Company, Invoice Address',
                         "Renaming the parent company must recompute the moves of its contacts")

    def _load_partner_data(self, values, update=False):
        return self.env['res.partner']._load_records(
            [{'xml_id': 'account.test_walk_in_customer', 'values': values}],
            update=update,
        )

    def _mark_invoice_partner_display_name_stale(self, invoice):
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE account_move SET invoice_partner_display_name = 'stale' WHERE id = %s",
            [invoice.id],
        )
        invoice.invalidate_recordset(['invoice_partner_display_name'])
