# -*- coding: utf-8 -*-

import time

from .common import TestPurchase
from odoo.tests.common import Form

class TestFifoReturns(TestPurchase):

    def test_fifo_returns(self):
        """Test to create product and purchase order to test the FIFO returns of the product"""

        self._load('account', 'test', 'account_minimal_test.xml')
        self._load('stock_account', 'test', 'stock_valuation_account.xml')

        # Set a product as using fifo price
        product_fiforet_icecream = self.env['product.product'].create({
            'default_code': 'FIFORET',
            'name': 'FIFO Ice Cream',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_1').id,
            'standard_price': 0.0,
            'uom_id': self.env.ref('uom.product_uom_kgm').id,
            'uom_po_id': self.env.ref('uom.product_uom_kgm').id,
            'description': 'FIFO Ice Cream',
        })
        product_fiforet_icecream.categ_id.property_cost_method = 'fifo'
        product_fiforet_icecream.categ_id.property_valuation = 'real_time'
        product_fiforet_icecream.categ_id.property_stock_account_input_categ_id = self.ref('purchase.o_expense')
        product_fiforet_icecream.categ_id.property_stock_account_output_categ_id = self.ref('purchase.o_income')

        # I create a draft Purchase Order for first in move for 10 kg at 50 euro
        purchase_order_1 = self.env['purchase.order'].create({
            'partner_id': self.ref('base.res_partner_3'),
            'order_line': [(0, 0, {
                'name': 'FIFO Ice Cream',
                'product_id': product_fiforet_icecream.id,
                'product_qty': 10.0,
                'product_uom': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 50.0,
                'date_planned': time.strftime('%Y-%m-%d'),
            })],
        })

        # Create a draft Purchase Order for second shipment for 30kg at 80€/kg
        purchase_order_2 = self.env['purchase.order'].create({
            'partner_id': self.ref('base.res_partner_3'),
            'order_line': [(0, 0, {
                'name': 'FIFO Ice Cream',
                'product_id': product_fiforet_icecream.id,
                'product_qty': 30.0,
                'product_uom': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 80.0,
                'date_planned': time.strftime('%Y-%m-%d'),
            })],
        })

        # Confirm the first purchase order
        purchase_order_1.button_confirm()

        # Process the reception of purchase order 1
        picking = purchase_order_1.picking_ids[0]
        self.env['stock.immediate.transfer'].create({'pick_ids': [(4, picking.id)]}).process()

        # Check the standard price of the product (fifo icecream)
        self.assertEqual(product_fiforet_icecream.standard_price, 0.0, 'Standard price should not have changed!')

        # Confirm the second purchase order
        purchase_order_2.button_confirm()
        picking = purchase_order_2.picking_ids[0]
        self.env['stock.immediate.transfer'].create({'pick_ids': [(4, picking.id)]}).process()

        # Return the goods of purchase order 2
        picking = purchase_order_2.picking_ids[0]
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking.ids, active_id=picking.ids[0],
            active_model='stock.picking'))
        return_pick_wiz = stock_return_picking_form.save()
        return_picking_id, dummy = return_pick_wiz.with_context(active_id=picking.id)._create_returns()

        # Important to pass through confirmation and assignation
        return_picking = self.env['stock.picking'].browse(return_picking_id)
        return_picking.action_confirm()
        return_picking.move_lines[0].quantity_done = return_picking.move_lines[0].product_uom_qty
        return_picking.action_done()

        #  After the return only 10 of the second purchase order should still be in stock as it applies fifo on the return too
        self.assertEqual(product_fiforet_icecream.qty_available, 10.0, 'Qty available should be 10.0')
        self.assertEqual(product_fiforet_icecream.value_svl, 800.0, 'Stock value should be 800')
