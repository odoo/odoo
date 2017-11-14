# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_landed_costs.tests.common import TestStockLandedCostsCommon
from odoo.exceptions import ValidationError


class TestStockLandedCosts(TestStockLandedCostsCommon):

    def test_StockLandedCosts(self):
        """ Test stock landed cost """

        # Service...
        product_product_2 = self.env.ref('product.product_product_2')
        # Create two new product with different volume and weight.
        lcd_monitor = self._create_product('LCD Monitor', self.uom_unit_id, weight=10, volume=1)
        ac_bluestar = self._create_product('Bluestar AC', self.uom_unit_id, weight=20, volume=1.5)

        # I create two picking to move those products
        picking_landed_cost_1 = self._create_shipment(lcd_monitor, self.uom_unit_id, self.picking_type_out_id, self.stock_location_id, self.customer_location_id, 5, 1)
        picking_landed_cost_2 = self._create_shipment(ac_bluestar, self.uom_unit_id, self.picking_type_out_id, self.stock_location_id, self.customer_location_id, 10, 1)

        # Confirm and assign picking
        picking_landed_cost_1.action_confirm()
        picking_landed_cost_1.action_assign()
        picking_landed_cost_1.move_lines.quantity_done = 5
        picking_landed_cost_1.button_validate()

        picking_landed_cost_2.action_confirm()
        picking_landed_cost_2.action_assign()
        picking_landed_cost_2.move_lines.quantity_done = 10
        picking_landed_cost_2.button_validate()

        # I create a landed cost for those 2 pickings
        landed_cost = self.LandedCost.create({
            'picking_ids': [(6, 0, [picking_landed_cost_1.id, picking_landed_cost_2.id])],
            'account_journal_id': self.expenses_journal.id,
            'cost_lines': [
                (0, 0, {
                    'name': 'equal split',
                    'split_method': 'equal',
                    'price_unit': 10,
                    'product_id': product_product_2.id}),
                (0, 0, {
                    'name': 'split by quantity',
                    'split_method': 'by_quantity',
                    'price_unit': 150,
                    'product_id': product_product_2.id}),
                (0, 0, {
                    'name': 'split by weight',
                    'split_method': 'by_weight',
                    'price_unit': 250,
                    'product_id': product_product_2.id}),
                (0, 0, {
                    'name': 'split by volume',
                    'split_method': 'by_volume',
                    'price_unit': 20,
                    'product_id': product_product_2.id
                })],
            'valuation_adjustment_lines': []
        })

        # I compute the landed cost  using Compute button
        landed_cost.compute_landed_cost()

        # I check the valuation adjustment lines
        for valuation in landed_cost.valuation_adjustment_lines:
            if valuation.cost_line_id.name == 'equal split':
                self.assertEqual(valuation.additional_landed_cost, 5, self._error_message(5, valuation.additional_landed_cost))
            elif valuation.cost_line_id.name == 'split by quantity' and valuation.move_id.product_id.name == lcd_monitor.name:
                self.assertEqual(valuation.additional_landed_cost, 50, self._error_message(50, valuation.additional_landed_cost))
            elif valuation.cost_line_id.name == 'split by quantity' and valuation.move_id.product_id.name == ac_bluestar.name:
                self.assertEqual(valuation.additional_landed_cost, 100, self._error_message(100, valuation.additional_landed_cost))
            elif valuation.cost_line_id.name == 'split by weight' and valuation.move_id.product_id.name == lcd_monitor.name:
                self.assertEqual(valuation.additional_landed_cost, 50, self._error_message(50, valuation.additional_landed_cost))
            elif valuation.cost_line_id.name == 'split by weight' and valuation.move_id.product_id.name == ac_bluestar.name:
                self.assertEqual(valuation.additional_landed_cost, 200, self._error_message(200, valuation.additional_landed_cost))
            elif valuation.cost_line_id.name == 'split by volume' and valuation.move_id.product_id.name == lcd_monitor.name:
                self.assertEqual(valuation.additional_landed_cost, 5, self._error_message(5, valuation.additional_landed_cost))
            elif valuation.cost_line_id.name == 'split by volume' and valuation.move_id.product_id.name == ac_bluestar.name:
                self.assertEqual(valuation.additional_landed_cost, 15, self._error_message(15, valuation.additional_landed_cost))
            else:
                self.assertRaises(ValidationError('unrecognized valuation adjustment line'))

        # I confirm the landed cost
        landed_cost.button_validate()

        # I check that the landed cost is now "Closed" and that it has an accounting entry
        self.assertEqual(landed_cost.state, 'done', "Wrong state on landed cost.")
        self.assertTrue(landed_cost.account_move_id, "No account move !")
        self.assertEqual(len(landed_cost.account_move_id.line_ids), 48, "Wrong move lines in account move.")
