# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo.modules.module import get_resource_path
from odoo.tests import common, Form
import time


class TestAccountVoucher(common.TransactionCase):

    def _load(self, module, *args):
        tools.convert_file(self.cr, 'account_voucher',
                           get_resource_path(module, *args),
                           {}, 'init', False, 'test', self.registry._assertion_report)

    def test_00_account_voucher_flow(self):
        """ Create Account Voucher for Customer and Vendor """
        self._load('account', 'test', 'account_minimal_test.xml')

        # User-groups and References
        partner_id = self.env.ref('base.res_partner_12')
        cash_journal_id = self.env.ref('account_voucher.cash_journal')
        sales_journal_id = self.env.ref('account_voucher.sales_journal')
        account_receivable_id = self.env.ref('account_voucher.a_recv')

        # Create a Account Voucher User
        voucher_user = self.env['res.users'].create({
            'name': 'Voucher Accountant',
            'login': 'vacc',
            'email': 'accountant@yourcompany.com',
            'company_id': self.env.ref('base.main_company').id,
            'groups_id': [(6, 0, [
                self.ref('base.group_partner_manager'),
                self.ref('account.group_account_user'),
                self.ref('account.group_account_invoice'),
            ])]
        })
        Voucher = self.env['account.voucher'].sudo(voucher_user)

        # Create Customer Voucher
        c = Form(Voucher.with_context(default_voucher_type="sale", voucher_type="sale"),
                 view='account_voucher.view_sale_receipt_form')
        c.partner_id = partner_id
        c.journal_id = sales_journal_id
        with c.line_ids.new() as line:
            line.name = "Voucher for Axelor"
            line.account_id = account_receivable_id
            line.price_unit = 1000.0
        account_voucher_customer = c.save()

        # Check Customer Voucher status.
        self.assertEquals(account_voucher_customer.state, 'draft', 'Initially customer voucher should be in the "Draft" state')

        # Validate Customer voucher
        account_voucher_customer.proforma_voucher()
        # Check for Journal Entry of customer voucher
        self.assertTrue(account_voucher_customer.move_id, 'No journal entry created !.')
        # Find related account move line for Customer Voucher.
        customer_voucher_move = account_voucher_customer.move_id

        # Check state of Account move line.
        self.assertEquals(customer_voucher_move.state, 'posted', 'Account move state is incorrect.')
        # Check partner of Account move line.
        self.assertEquals(customer_voucher_move.partner_id, partner_id, 'Partner is incorrect on account move.')
        # Check journal in Account move line.
        self.assertEquals(customer_voucher_move.journal_id, sales_journal_id, 'Journal is incorrect on account move.')
        # Check amount in Account move line.
        self.assertEquals(customer_voucher_move.amount, 1000.0, 'Amount is incorrect in account move.')

        # Create Vendor Voucher
        v = Form(Voucher.with_context(default_voucher_type="purchase", voucher_type="purchase"))
        v.partner_id = partner_id
        v.journal_id = cash_journal_id
        with v.line_ids.new() as line:
            line.name = "Voucher Axelor"
            line.account_id = account_receivable_id
            line.price_unit = 1000.0
        account_voucher_vendor = v.save()

        # Check Vendor Voucher status.
        self.assertEquals(account_voucher_vendor.state, 'draft', 'Initially vendor voucher should be in the "Draft" state')

        # Validate Vendor voucher
        account_voucher_vendor.proforma_voucher()
        # Check for Journal Entry of vendor voucher
        self.assertTrue(account_voucher_vendor.move_id, 'No journal entry created !.')
        # Find related account move line for Vendor Voucher.
        vendor_voucher_move = account_voucher_vendor.move_id

        # Check state of Account move line.
        self.assertEquals(vendor_voucher_move.state, 'posted', 'Account move state is incorrect.')
        # Check partner of Account move line.
        self.assertEquals(vendor_voucher_move.partner_id, partner_id, 'Partner is incorrect on account move.')
        # Check journal in Account move line.
        self.assertEquals(vendor_voucher_move.journal_id, cash_journal_id, 'Journal is incorrect on account move.')
        # Check amount in Account move line.
        self.assertEquals(vendor_voucher_move.amount, 1000.0, 'Amount is incorrect in acccount move.')
