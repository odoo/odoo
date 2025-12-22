# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.addons.account.tests.common import AccountTestMockOnlineSyncCommon
from odoo.tools import mute_logger

import logging
import odoo.tests

_logger = logging.getLogger(__name__)


class BaseTestUi(AccountTestMockOnlineSyncCommon):

    def main_flow_tour(self):
        # Disable all onboarding tours
        self.env.ref('base.user_admin').tour_enabled = False
        # Enable Make to Order
        self.env.ref('stock.route_warehouse0_mto').active = True

        # Define minimal accounting data to run without CoA
        a_suspense = self.env['account.account'].create({
            'code': 'X2220',
            'name': 'Suspense - Test',
            'account_type': 'asset_current'
        })
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

        IrDefault = self.env['ir.default']
        IrDefault.set('res.partner', 'property_account_receivable_id', a_recv.id, company_id=self.env.company.id)
        IrDefault.set('res.partner', 'property_account_payable_id', a_pay.id, company_id=self.env.company.id)
        IrDefault.set('res.partner', 'property_account_position_id', False, company_id=self.env.company.id)
        IrDefault.set('product.category', 'property_account_expense_categ_id', a_expense.id, company_id=self.env.company.id)
        IrDefault.set('product.category', 'property_account_income_categ_id', a_sale.id, company_id=self.env.company.id)

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
            'suspense_account_id': a_suspense.id,
            'default_account_id': bnk.id,
        })
        self.bank_journal.outbound_payment_method_line_ids.payment_account_id = a_expense
        self.bank_journal.inbound_payment_method_line_ids.payment_account_id = a_sale

        self.sales_journal = self.env['account.journal'].create({
            'name': 'Customer Invoices - Test',
            'code': 'TINV',
            'type': 'sale',
            'default_account_id': a_sale.id,
            'refund_sequence': True,
        })
        self.general_journal = self.env['account.journal'].create({
            'name': 'General - Test',
            'code': 'GNRL',
            'type': 'general',
            'default_account_id': bnk.id,
        })

        self.start_tour("/odoo", 'main_flow_tour', login="admin", timeout=180)


@odoo.tests.tagged('post_install', '-at_install', 'is_tour')
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
            "view_ids": [Command.create({"view_mode": "list"}), Command.create({"view_mode": "form"})]
        })

        self.env["ir.ui.menu"].create({
            "name": "model_multicompany_menu",
            "action": f"ir.actions.act_window,{act_window.id}",
        })

        with mute_logger("odoo.http"):
            self.start_tour(f"/odoo/action-{act_window.id}", "test_company_switch_access_error", login="admin", cookies={"cids": f"{company1.id}-{company2.id}"})

    def test_company_access_error_redirect(self):
        company1 = self.env.company
        company2 = self.env["res.company"].create({"name": "second company"})
        self.env["res.users"].browse(2).write({
            "company_ids": [Command.clear(), Command.link(company1.id), Command.link(company2.id)]
        })

        self.env["ir.rule"].create({
            "name": "multiCompany rule",
            "domain_force": '["|", ("company_id", "=", False), ("company_id", "in", company_ids)]',
            "model_id": self.env["ir.model"]._get("test.model_multicompany").id
        })

        self.env["test.model_multicompany"].create({"name": "p1"})
        record_p2 = self.env["test.model_multicompany"].create({"name": "p2", "company_id": company2.id})

        act_window = self.env["ir.actions.act_window"].create({
            "name": "model_multicompany_action",
            "res_model": "test.model_multicompany",
            "view_ids": [Command.create({"view_mode": "list"}), Command.create({"view_mode": "form"})]
        })

        self.env["ir.ui.menu"].create({
            "name": "model_multicompany_menu",
            "action": f"ir.actions.act_window,{act_window.id}",
        })

        with mute_logger("odoo.http"):
            self.start_tour(f"/odoo/action-{act_window.id}/{record_p2.id}", "test_company_access_error_redirect", login="admin", cookies={"cids": f"{company1.id}"})

    def test_company_switch_access_error_debug(self):
        # This test is identical to test_company_switch_access_error, but with debug mode enabled
        company1 = self.env.company
        company2 = self.env["res.company"].create({"name": "second company"})
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
            "view_ids": [Command.create({"view_mode": "list"}), Command.create({"view_mode": "form"})]
        })

        self.env["ir.ui.menu"].create({
            "name": "model_multicompany_menu",
            "action": f"ir.actions.act_window,{act_window.id}",
        })

        current_companies = "%s-%s" % (company1.id, company2.id)
        with mute_logger("odoo.http"):
            self.start_tour(f"/odoo/action-{act_window.id}?debug=assets&cids={current_companies}", "test_company_switch_access_error", login="admin")


@odoo.tests.tagged('post_install', '-at_install', 'is_tour')
class TestUiMobile(BaseTestUi):

    browser_size = '375x667'
    touch_enabled = True

    def test_01_main_flow_tour_mobile(self):
        self.main_flow_tour()
