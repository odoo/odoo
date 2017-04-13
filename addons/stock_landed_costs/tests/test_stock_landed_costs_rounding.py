# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_landed_costs.tests.common import TestStockLandedCostsCommon


class TestLandedCostsRounding(TestStockLandedCostsCommon):

    def _create_landed_cost(self, price_unit, pickings):
        return self.LandedCost.create({
            'picking_ids': [(6, 0, pickings.ids)],
            'account_journal_id': self.expenses_journal.id,
            'cost_lines': [
                (0, 0, {
                    'name': 'equal split',
                    'split_method': 'equal',
                    'price_unit': price_unit,
                    'product_id': self.landed_cost.id})]
                })

    def test_00_landed_cost_rounding(self):
        """ Test the rounding in landed costs """

        product_rounding = self._create_product('Product Rounding', uom_id=self.product_uom_unit_round_1.id)
        incoming_shipment_1 = self._create_shipment(product_rounding, self.product_uom_unit_round_1.id, self.picking_type_in_id, self.supplier_location_id, self.stock_location_id, 13, 1)

        # I receive picking and check how many quants are created
        incoming_shipment_1.action_confirm()
        incoming_shipment_1.action_assign()
        incoming_shipment_1.action_done()

        # Create landed cost for first incoming shipment.
        landed_cost = self._create_landed_cost(15, incoming_shipment_1)
        # Compute landed costs
        landed_cost.compute_landed_cost()
        # Check valuation adjustment line recognized or not
        self._validate_additional_landed_cost_lines(landed_cost, {'equal': 15.0})
        # I confirm the landed cost
        landed_cost.button_validate()
        # I check that the landed cost is now "Closed" and that it has an accounting entry
        self.assertEqual(landed_cost.state, 'done', 'Landed cost should be in done state')
        self.assertTrue(landed_cost.account_move_id, 'Account move should be generated.')

        # ---------------------------------------------------
        # Lets perform all the tests for rounding with dozen.
        # ---------------------------------------------------

        price = 17.00 / 12.00
        cooler = self._create_product('Cooler Bajaj', self.product_uom_unit_round_1.id)
        incoming_shipment_2 = self._create_shipment(cooler, self.uom_dozen_id, self.picking_type_in_id, self.customer_location_id, self.stock_location_id, 1, price)
        # I receive picking Bajaj cooler, and check how many quants are created.
        incoming_shipment_2.action_confirm()
        incoming_shipment_2.action_assign()
        incoming_shipment_2.action_done()

        # Create landed cost for second incoming shipment.
        landed_cost = self._create_landed_cost(11, incoming_shipment_2)
        # Compute landed costs
        landed_cost.compute_landed_cost()
        # Check valuation adjustment line recognized or not
        self._validate_additional_landed_cost_lines(landed_cost, {'equal': 11.0})
        # Confirm the landed cost
        landed_cost.button_validate()
        # Check that the landed cost is now "Closed" and that it has an accounting entry
        self.assertEqual(landed_cost.state, 'done', 'Landed cost should be in done state')
        self.assertTrue(landed_cost.account_move_id, 'Account move should be linked to landed cost.')

    def _validate_additional_landed_cost_lines(self, landed_cost,  valid_vals):
        for valuation in landed_cost.valuation_adjustment_lines:
            if valuation.cost_line_id.split_method == 'equal':
                self.assertEqual(valuation.additional_landed_cost, valid_vals['equal'], self._error_message(valid_vals['equal'], valuation.additional_landed_cost))
