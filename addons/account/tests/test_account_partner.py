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

        # rank updates are updated in the post-commit phase
        with self.enter_registry_test_mode():
            self.env.cr.postcommit.run()
        self.assertEqual(self.partner_a.supplier_rank, 1)
        self.assertEqual(self.partner_a.customer_rank, 1)

        # a second move is updated in postcommit
        self.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'date': '2017-01-02',
                'invoice_date': '2017-01-02',
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [(0, 0, {'name': 'aaaa', 'price_unit': 100.0})],
            },
        ]).action_post()
        # rank updates are updated in the post-commit phase
        with self.enter_registry_test_mode():
            self.env.cr.postcommit.run()
        self.assertEqual(self.partner_a.customer_rank, 2)

    def test_manually_write_partner_id(self):
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2025-04-29',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 500.0,
                'tax_ids': [Command.link(self.tax_sale_a.id)],
            })],
        })
        move.action_post()
        reversal = move._reverse_moves(cancel=True)

        receivable_lines = (move + reversal).line_ids.filtered(lambda l: l.display_type == 'payment_term')

        # Changing the partner should be possible despite being in locked periods as long as the VAT is the same
        move.company_id.fiscalyear_lock_date = '9999-12-31'
        move.company_id.tax_lock_date = '9999-12-31'

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

    def test_manually_write_partner_id_empty_string_vs_False(self):
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
        self.partner_a.vat = ''
        self.partner_b.vat = False

        self.partner_a.parent_id = self.partner_b

    def test_res_partner_bank(self):
        self.env.user.group_ids -= self.env.ref('base.group_system')  # it is implying the group below
        self.env.user.group_ids += self.env.ref('base.group_partner_manager')
        self.env.user.group_ids += self.env.ref('account.group_validate_bank_account')
        partner = self.env['res.partner'].create({'name': 'MyCustomer'})
        account = self.env['res.partner.bank'].create({
            'acc_number': '123456789',
            'partner_id': partner.id,
        })
        account.allow_out_payment = True

        with self.assertRaisesRegex(UserError, "has been trusted"), self.cr.savepoint():
            account.write({'acc_number': '1234567890999'})
        with self.assertRaisesRegex(UserError, "has been trusted"), self.cr.savepoint():
            account.write({'sanitized_acc_number': '1234567890999'})
        with self.assertRaisesRegex(UserError, "has been trusted"), self.cr.savepoint():
            account.write({'partner_id': self.env['res.partner'].create({'name': 'MyCustomer 2'}).id})

        account.allow_out_payment = False
        account.write({'acc_number': '1234567890999000'})

        self.env.user.group_ids -= self.env.ref('account.group_validate_bank_account')
        with self.assertRaisesRegex(UserError, "You do not have the rights to trust"), self.cr.savepoint():
            account.write({'allow_out_payment': True})
