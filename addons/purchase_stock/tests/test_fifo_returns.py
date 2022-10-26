# -*- coding: utf-8 -*-

import time

from odoo.tests import tagged, Form
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon


@tagged('-at_install', 'post_install')
class TestFifoReturns(ValuationReconciliationTestCommon):

    def test_fifo_returns(self):
        """Test to create product and purchase order to test the FIFO returns of the product"""
        res_partner_3 = self.env['res.partner'].create({
            'name': 'Gemini Partner',
        })

        # Set a product as using fifo price
        product_fiforet_icecream = self.env['product.product'].create({
            'default_code': 'FIFORET',
            'name': 'FIFO Ice Cream',
            'type': 'product',
            'categ_id': self.stock_account_product_categ.id,
            'standard_price': 0.0,
            'uom_id': self.env.ref('uom.product_uom_kgm').id,
            'uom_po_id': self.env.ref('uom.product_uom_kgm').id,
            'description': 'FIFO Ice Cream',
        })

        # I create a draft Purchase Order for first in move for 10 kg at 50 euro
        purchase_order_1 = self.env['purchase.order'].create({
            'partner_id': res_partner_3.id,
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
            'partner_id': res_partner_3.id,
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
        res = picking.button_validate()
        Form(self.env[res['res_model']].with_context(res['context'])).save().process()

        # Check the standard price of the product (fifo icecream)
        self.assertAlmostEqual(product_fiforet_icecream.standard_price, 50)

        # Confirm the second purchase order
        purchase_order_2.button_confirm()
        picking = purchase_order_2.picking_ids[0]
        res = picking.button_validate()
        Form(self.env[res['res_model']].with_context(res['context'])).save().process()

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
        return_picking.move_ids[0].quantity_done = return_picking.move_ids[0].product_uom_qty
        return_picking._action_done()

        #  After the return only 10 of the second purchase order should still be in stock as it applies fifo on the return too
        self.assertEqual(product_fiforet_icecream.qty_available, 10.0, 'Qty available should be 10.0')
        self.assertEqual(product_fiforet_icecream.value_svl, 800.0, 'Stock value should be 800')
