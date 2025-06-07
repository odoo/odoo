# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.project_stock_account.tests.test_analytics import TestAnalytics


class TestAnalyticsReinvoice(TestAnalytics):

    def test_no_analytic_lines_for_reinvoicable_products(self):
        reinvoicable_product = self.env['product.product'].create({
            'name': 'product_order_cost',
            'standard_price': 100.0,
            'expense_policy': 'cost',
        })
        picking_out = self.PickingObj.create({
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'project_id': self.project.id,
        })
        picking_out.picking_type_id.analytic_costs = True
        self.MoveObj.create({
            'name': 'Move',
            'product_uom': self.uom_unit.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'product_id': reinvoicable_product.id,
            'product_uom_qty': 3,
        })
        self.user_stock_user.company_id.anglo_saxon_accounting = True
        picking_out.action_confirm()
        picking_out.with_user(self.user_stock_user).button_validate()

        self.assertFalse(
            picking_out.move_ids.analytic_account_line_ids,
            'There should not be any generated analytic lines as the product is reinvoicable and anglo-saxon accounting is enabled',
        )
