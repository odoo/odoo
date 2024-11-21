# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_account.tests.test_lot_valuation import TestLotValuation
from odoo.tests import tagged, Form
from odoo import Command


@tagged('post_install', '-at_install')
class TestStockLandedCostsLots(TestLotValuation):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.productlc1 = cls.env['product.product'].create({
            'name': 'product1',
            'type': 'service',
            'landed_cost_ok': True,
        })

    def test_stock_landed_costs_lots(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        picking_1 = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
            'move_ids': [Command.create({
                'name': 'Picking 1',
                'product_id': self.product1.id,
                'product_uom_qty': 15,
                'product_uom': self.ref('uom.product_uom_unit'),
                'location_id': self.supplier_location.id,
                'location_dest_id': self.env.ref('stock.stock_location_stock').id,
                'price_unit': 10,
            })],
        })
        picking_2 = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
            'move_ids': [Command.create({
                'name': 'Picking 2',
                'product_id': self.product1.id,
                'product_uom_qty': 10,
                'product_uom': self.ref('uom.product_uom_unit'),
                'location_id': self.supplier_location.id,
                'location_dest_id': self.env.ref('stock.stock_location_stock').id,
                'price_unit': 11,
            })],
        })

        # Confirm and assign picking
        (picking_1 | picking_2).action_confirm()
        picking_1.move_ids.move_line_ids = [Command.clear()] + [Command.create({
            'product_id': self.product1.id,
            'lot_name': lot_name,
            'quantity': 5,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.env.ref('stock.stock_location_stock').id,
        }) for lot_name in ['LClot1', 'LClot2', 'LClot3']]
        picking_2.move_ids.move_line_ids = [Command.clear()] + [Command.create({
            'product_id': self.product1.id,
            'lot_name': lot_name,
            'quantity': 5,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.env.ref('stock.stock_location_stock').id,
        }) for lot_name in ['LClot1', 'LClot2']]
        (picking_1 | picking_2).move_ids.picked = True
        (picking_1 | picking_2).button_validate()

        og_layer = picking_2.move_ids.stock_valuation_layer_ids | picking_1.move_ids.stock_valuation_layer_ids
        lc_form = Form(self.env['stock.landed.cost'])
        lc_form.picking_ids = (picking_1 | picking_2)
        with lc_form.cost_lines.new() as cost_line:
            cost_line.product_id = self.productlc1
            cost_line.price_unit = 6
        lc = lc_form.save()
        lc.compute_landed_cost()
        lc.button_validate()
        for valuation in lc.valuation_adjustment_lines:
            if valuation.cost_line_id.name == 'equal split':
                self.assertEqual(valuation.additional_landed_cost, 5)

        # I check that the landed cost is now "Closed" and that it has an accounting entry
        self.assertEqual(lc.state, "done")
        self.assertTrue(lc.account_move_id)
        self.assertEqual(len(lc.account_move_id.line_ids), 4)

        lc_value = sum(lc.account_move_id.line_ids.filtered(lambda aml: aml.account_id.name.startswith('Expenses')).mapped('debit'))
        product_value = abs(self.productlc1.value_svl)
        self.assertEqual(lc_value, product_value)
        lot = self.env['stock.lot'].search([('name', 'ilike', 'LClot')])

        self.assertRecordValues(lc.stock_valuation_layer_ids.sorted('id'), [
            {'lot_id': lot[0].id, 'product_id': self.product1.id, 'stock_valuation_layer_id': og_layer[0].id, 'quantity': 0, 'value': 1.5},
            {'lot_id': lot[1].id, 'product_id': self.product1.id, 'stock_valuation_layer_id': og_layer[1].id, 'quantity': 0, 'value': 1.5},
            {'lot_id': lot[0].id, 'product_id': self.product1.id, 'stock_valuation_layer_id': og_layer[2].id, 'quantity': 0, 'value': 1},
            {'lot_id': lot[1].id, 'product_id': self.product1.id, 'stock_valuation_layer_id': og_layer[3].id, 'quantity': 0, 'value': 1},
            {'lot_id': lot[2].id, 'product_id': self.product1.id, 'stock_valuation_layer_id': og_layer[4].id, 'quantity': 0, 'value': 1},
        ])

        for l, price in zip(lot, [10.75, 10.75, 10.2]):
            self.assertEqual(l.standard_price, price)
        outs = self._make_out_move(self.product1, 9, lot_ids=[lot[0], lot[1], lot[2]])
        self.assertRecordValues(outs.stock_valuation_layer_ids.sorted('id'), [
            {'lot_id': lot[0].id, 'product_id': self.product1.id, 'quantity': -3, 'value': -32.25},
            {'lot_id': lot[1].id, 'product_id': self.product1.id, 'quantity': -3, 'value': -32.25},
            {'lot_id': lot[2].id, 'product_id': self.product1.id, 'quantity': -3, 'value': -30.6},
        ])
