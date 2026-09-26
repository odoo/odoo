# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.project_stock_account.tests.test_analytics import TestAnalytics


class TestAnalyticsReinvoice(TestAnalytics):

    def test_no_analytic_lines_for_reinvoicable_products(self):
        self.product.expense_policy = 'cost'
        self.user_stock_user = self._create_new_internal_user(
            name='Basic Stock User',
            login='basic_stock_user',
            groups='stock.group_stock_user',
        )

        picking_out = self._make_out_move(self.product, quantity=3, create_picking=True, auto_validate=False).picking_id
        picking_out.project_id = self.project
        picking_out.picking_type_id.analytic_costs = True
        self.user_stock_user.company_id.anglo_saxon_accounting = True
        picking_out.action_confirm()
        picking_out.with_user(self.user_stock_user).button_validate()

        self.assertFalse(
            picking_out.move_ids.analytic_account_line_ids,
            'There should not be any generated analytic lines as the product is reinvoicable and anglo-saxon accounting is enabled',
        )
