# -*- coding: utf-8 -*-

import time

from .common import TestPurchase


class TestFifoReturns(TestPurchase):

    def create_purchase_order(self, product, product_qty=0.0, price_unit=0.0):
        vals = {
            'partner_id': self.ref('base.res_partner_3'),
            'order_line': [
                (0, 0, {
                    'name': product.name,
                    'product_id': product.id,
                    'product_qty': product_qty,
                    'product_uom': self.uom_kg_id,
                    'price_unit': price_unit,
                    'date_planned': time.strftime('%Y-%m-%d'),
                })],
        }
        return self.env['purchase.order'].create(vals)

    def test_fifo_returns(self):
        """Test to create product and purchase order to test the FIFO returns of the product"""

        # ---------------------------------------------------------------------
        # FIRST PO : ICE - CREAM ( 10kg * 50€/kg)
        # STANDARD PRICE OF PRODUCT FIFO : 0.0
        # SECOND PO : ICE - CREAM ( 30kg * 80€/kg)
        # PRODUCT PRICE SHOULD NOT CHANGE
        # RETURN THE GOODS OF PURCHASE ORDER 2
        # QTY AVAILABLE SHOULD BE 10.0 :( BASED ON FIFO )
        # STOCK VALUE SHOULD BE 800
        # --------------------------------------------------------------------

        self._load('account', 'test', 'account_minimal_test.xml')
        self._load('stock_account', 'test', 'stock_valuation_account.xml')



        # Set a product price
        product_fiforet_icecream = self._create_product(self.uom_kg_id, cost_method="fifo")

        # Create a draft Purchase Order for first in move for 10kg at 50€/kg
        purchase_order_1 = self.create_purchase_order(product=product_fiforet_icecream,
                                                           product_qty=10.0, price_unit=50.0)

        # Create a draft Purchase Order for second shipment for 30kg at 80€/kg
        purchase_order_2 = self.create_purchase_order(product=product_fiforet_icecream,
                                                           product_qty=30.0, price_unit=80.0)

        # Confirm the first purchase order
        purchase_order_1.button_confirm()
        # Process the reception of purchase order 1
        picking = purchase_order_1.picking_ids[0]
        wiz = self.StockTransfer.create({'pick_id': picking.id})
        wiz.process()

        # Check the standard price of the product (fifo icecream)
        self.assertEqual(product_fiforet_icecream.standard_price,
                         0.0, 'Standard price should not have changed!')

        # Confirm the second purchase order
        purchase_order_2.button_confirm()
        picking = purchase_order_2.picking_ids[0]
        wiz = self.StockTransfer.create({'pick_id': picking.id})
        wiz.process()

        # Return the goods of purchase order 2
        picking = purchase_order_2.picking_ids[0]
        return_pick_wiz = self.env['stock.return.picking'].with_context(
            active_model='stock.picking', active_id=picking.id).create({})
        return_picking_id, dummy = return_pick_wiz.with_context(active_id=picking.id)._create_returns()

        return_picking = self.StockPicking.browse(return_picking_id)
        wiz = self.StockTransfer.create({'pick_id': return_picking.id})
        wiz.process()

        #  After the return only 10 of the second purchase order should still be in stock as it applies fifo on the return too
        self.assertEqual(product_fiforet_icecream.qty_available, 10.0, 'Qty available should be 10.0')
        self.assertEqual(product_fiforet_icecream.stock_value, 800.0, 'Stock value should be 800')
