# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
import odoo.tests
import unittest

class BaseTestUi(odoo.tests.HttpCase):

    def main_flow_tour(self):
        # Enable Make to Order
        self.env.ref('stock.route_warehouse0_mto').active = True

        # Define minimal accounting data to run without CoA
        a_expense = self.env['account.account'].create({
            'code': 'X2120',
            'name': 'Expenses - (test)',
            'user_type_id': self.env.ref('account.data_account_type_expenses').id,
        })
        a_recv = self.env['account.account'].create({
            'code': 'X1012',
            'name': 'Debtors - (test)',
            'reconcile': True,
            'user_type_id': self.env.ref('account.data_account_type_receivable').id,
        })
        a_pay = self.env['account.account'].create({
            'code': 'X1111',
            'name': 'Creditors - (test)',
            'user_type_id': self.env.ref('account.data_account_type_payable').id,
            'reconcile': True,
        })
        a_sale = self.env['account.account'].create({
            'code': 'X2020',
            'name': 'Product Sales - (test)',
            'user_type_id': self.env.ref('account.data_account_type_revenue').id,
        })
        bnk = self.env['account.account'].create({
            'code': 'X1014',
            'name': 'Bank Current Account - (test)',
            'user_type_id': self.env.ref('account.data_account_type_liquidity').id,
        })

        Property = self.env['ir.property']
        Property._set_default('property_account_receivable_id', 'res.partner', a_recv, self.env.company)
        Property._set_default('property_account_payable_id', 'res.partner', a_pay, self.env.company)
        Property._set_default('property_account_position_id', 'res.partner', False, self.env.company)
        Property._set_default('property_account_expense_categ_id', 'product.category', a_expense, self.env.company)
        Property._set_default('property_account_income_categ_id', 'product.category', a_sale, self.env.company)

        self.expenses_journal = self.env['account.journal'].create({
            'name': 'Vendor Bills - Test',
            'code': 'TEXJ',
            'type': 'purchase',
            'refund_sequence': True,
        })
        self.bank_journal = self.env['account.journal'].create({
            'name': 'Bank - Test',
            'code': 'TBNK',
            'type': 'bank',
            'default_account_id': bnk.id,
        })
        self.sales_journal = self.env['account.journal'].create({
            'name': 'Customer Invoices - Test',
            'code': 'TINV',
            'type': 'sale',
            'default_account_id': a_sale.id,
            'refund_sequence': True,
        })

        self.start_tour("/web", 'main_flow_tour', login="admin", timeout=180)

@odoo.tests.tagged('post_install', '-at_install')
class TestUi(BaseTestUi):

    def test_01_main_flow_tour(self):
        import unittest; raise unittest.SkipTest("skipWOWL")
        self.main_flow_tour()

@odoo.tests.tagged('post_install', '-at_install')
class TestUiMobile(BaseTestUi):

    browser_size = '375x667'

    def test_01_main_flow_tour_mobile(self):
        import unittest; raise unittest.SkipTest("skipWOWL")

        if odoo.release.version_info[-1] == 'e':
            self.main_flow_tour()
        else:
            raise unittest.SkipTest("Mobile testing not needed in community")
