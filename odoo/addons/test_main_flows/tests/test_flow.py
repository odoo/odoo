# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.tools import mute_logger

import odoo.tests

class BaseTestUi(odoo.tests.HttpCase):

    def main_flow_tour(self):
        # Enable Make to Order
        self.env.ref('stock.route_warehouse0_mto').active = True

        # Define minimal accounting data to run without CoA
        a_expense = self.env['account.account'].create({
            'code': 'X2120',
            'name': 'Expenses - (test)',
            'account_type': 'expense',
        })
        a_recv = self.env['account.account'].create({
            'code': 'X1012',
            'name': 'Debtors - (test)',
            'reconcile': True,
            'account_type': 'asset_receivable',
        })
        a_pay = self.env['account.account'].create({
            'code': 'X1111',
            'name': 'Creditors - (test)',
            'account_type': 'liability_payable',
            'reconcile': True,
        })
        a_sale = self.env['account.account'].create({
            'code': 'X2020',
            'name': 'Product Sales - (test)',
            'account_type': 'income',
        })
        bnk = self.env['account.account'].create({
            'code': 'X1014',
            'name': 'Bank Current Account - (test)',
            'account_type': 'asset_cash',
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
        self.main_flow_tour()

    def test_company_switch_access_error(self):
        company1 = self.env.company
        company2 = self.env["res.company"].create({"name":"second company"})
        self.env["res.users"].browse(2).write({
            "company_ids": [Command.clear(), Command.link(company1.id), Command.link(company2.id)]
        })

        self.env["ir.rule"].create({
            "name": "multiCompany rule",
            "domain_force": '["|", ("company_id", "=", False), ("company_id", "in", company_ids)]',
            "model_id": self.env["ir.model"]._get("test.model_multicompany").id
        })

        self.env["test.model_multicompany"].create({"name": "p1"})
        self.env["test.model_multicompany"].create({"name": "p2", "company_id": company2.id})

        act_window = self.env["ir.actions.act_window"].create({
            "name": "model_multicompany_action",
            "res_model": "test.model_multicompany",
            "view_ids": [Command.create({"view_mode": "tree"}), Command.create({"view_mode": "form"})]
        })

        self.env["ir.ui.menu"].create({
            "name": "model_multicompany_menu",
            "action": f"ir.actions.act_window,{act_window.id}",
        })

        current_companies = "%s-%s" % (company1.id, company2.id)
        with mute_logger("odoo.http"):
            self.start_tour(f"/web#action={act_window.id}&cids={current_companies}", "test_company_switch_access_error", login="admin")


@odoo.tests.tagged('post_install', '-at_install')
class TestUiMobile(BaseTestUi):

    browser_size = '375x667'
    touch_enabled = True

    def test_01_main_flow_tour_mobile(self):
        self.main_flow_tour()
