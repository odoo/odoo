# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_landed_costs.tests.common import TestStockLandedCostsCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestStockLandedCosts(TestStockLandedCostsCommon):

    def test_landed_cost_in_move_line(self):
        """
        Tests that a move line created through the catalog gives the right landed cost
        """
        self.landed_cost.landed_cost_ok = True
        account_move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id
        })
        account_move._update_order_line_info(
            product_id=self.landed_cost.id,
            quantity=1
        )
        self.assertTrue(account_move.invoice_line_ids.is_landed_costs_line, "The landed cost should appear in the move line.")
        account_move._update_order_line_info(
            product_id=self.product.id,
            quantity=1
        )
        move_line_no_landed = account_move.line_ids.filtered(lambda line: line.product_id == self.product)
        self.assertFalse(move_line_no_landed.is_landed_costs_line, "The landed cost should not be set to True.")
