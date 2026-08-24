# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.project_stock_account.tests.test_analytics import TestAnalytics


class TestAnalyticsReinvoice(TestAnalytics):

    def test_no_analytic_lines_for_reinvoicable_products(self):
        self.product.expense_policy = 'cost'
        picking_out = self._make_out_move(
            self.product, quantity=3, create_picking=True, auto_validate=False
        ).picking_id
        picking_out.project_id = self.project
        picking_out.picking_type_id.analytic_costs = True
        self.inventory_user.company_id.anglo_saxon_accounting = True
        picking_out.action_confirm()
        picking_out.with_user(self.inventory_user).button_validate()

        self.assertFalse(
            picking_out.move_ids.analytic_account_line_ids,
            'There should not be any generated analytic lines as the product is reinvoicable and anglo-saxon accounting is enabled',
        )
