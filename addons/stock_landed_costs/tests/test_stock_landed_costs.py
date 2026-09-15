# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.stock_landed_costs.tests.common import TestStockLandedCostsCommon


@tagged('post_install', '-at_install')
class TestStockLandedCosts(TestStockLandedCostsCommon):

    _test_user_groups = None  # FIXME list needed groups

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
            product=self.landed_cost,
            quantity=1,
            uom=self.landed_cost.uom_id,
            child_field='line_ids',
        )
        self.assertTrue(account_move.invoice_line_ids.is_landed_costs_line, "The landed cost should appear in the move line.")
        account_move._update_order_line_info(
            product=self.product,
            quantity=1,
            uom=self.product.uom_id,
            child_field='line_ids',
        )
        move_line_no_landed = account_move.line_ids.filtered(lambda line: line.product_id == self.product)
        self.assertFalse(move_line_no_landed.is_landed_costs_line, "The landed cost should not be set to True.")

    def test_landed_cost_for_specific_products(self):
        """Ensure that landed costs apply only to the products specified in the "Apply On" field
        of the landed cost lines, and exclude all other products from the related pickings.
        """
        self.product_a.is_storable = True
        self.landed_cost.landed_cost_on_product_ids = self.product_refrigerator
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.in_type_id.id,
            'location_id': self.supplier_location_id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
            'move_ids': [
                Command.create({'product_id': product.id, 'product_uom_qty': qty})
                for product, qty in [(self.product_oven, 1), (self.product_refrigerator, 3), (self.product_a, 5)]
            ],
        })
        picking.action_confirm()
        picking.button_validate()

        lc_form = Form(self.env['stock.landed.cost'])
        lc_form.picking_ids.add(picking)
        with lc_form.cost_lines.new() as cost_line:
            cost_line.product_id = self.landed_cost
            cost_line.price_unit = 100
            cost_line.split_method = 'by_quantity'
        lc = lc_form.save()

        self.assertEqual(lc.cost_lines.apply_on_product_ids, self.product_refrigerator)

        lc.cost_lines.write({'apply_on_product_ids': [Command.link(self.product_oven.id)]})
        lc.compute_landed_cost()

        valuation_lines = lc.valuation_adjustment_lines
        self.assertEqual(len(valuation_lines), 2)

        oven_val_line = valuation_lines.filtered(lambda line: line.product_id == self.product_oven)
        refrigerator_val_line = valuation_lines - oven_val_line

        self.assertEqual(oven_val_line.additional_landed_cost, 25)
        self.assertEqual(refrigerator_val_line.additional_landed_cost, 75)
        self.assertFalse(valuation_lines.filtered(lambda line: line.product_id == self.product_a))
