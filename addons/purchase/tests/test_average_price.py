# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from .common import TestPurchase


class TestAveragePrice(TestPurchase):

    def _create_purchase(self, product, uom_id, product_qty=0.0, price_unit=0.0):
        return self.env['purchase.order'].create({
             'partner_id': self.partner_id,
             'order_line': [(0, 0, {
                 'name': product.name,
                 'product_id': product.id,
                 'product_qty': product_qty,
                 'product_uom': uom_id,
                 'price_unit': price_unit,
                 'date_planned': time.strftime('%Y-%m-%d'),
                 })]
             })

    def test_00_average_price(self):
        """ Testcase for average price computation"""

        # ---------------------------------------------------------------------
        # FIRST PO : ICE - CREAM ( 10kg * 60€ = 600€ )
        # SECOND PO : ICE - CREAM ( 30kg * 80€ = 2400€ )
        # AVERAGE PRICE OF PRODUCT : 60€
        # DELIVER GOODS : 20 KG ICE CREAM ( PRODUCT PRICE SHOULD NOT CHANGE )
        # THIRD PO :  ICE - CREAM ( 500g * 0.2€ = 100€ )
        # STANDARD PRICE OF PRODUCT : 78.05€ ( 20kg * 75€ + 0.5kg * 200€)/ 20.5
        # --------------------------------------------------------------------

        self._load('account', 'test', 'account_minimal_test.xml')
        self._load('purchase', 'test', 'stock_valuation_account.xml')

        # Set a product as using average price.
        product_icecream = self._create_product(self.uom_kg_id, cost_method="average", price=60)

        # -----------------------------------------------------------------------------------
        # Create a draft Purchase Order for first incoming shipment for 10kg icecream at 60€/kg
        # -----------------------------------------------------------------------------------

        purchase_order_1 = self._create_purchase(product=product_icecream, uom_id=self.uom_kg_id, product_qty=10.0, price_unit=60.0)
        # Confirm the first purchase order
        purchase_order_1.button_confirm()

        # Check the "Approved" status of purchase order 1
        self.assertEqual(purchase_order_1.state, 'purchase', "Wrong state of purchase order!")

        # Process the reception of purchase order 1
        picking = purchase_order_1.picking_ids[0]
        wiz = self.StockTransfer.create({'pick_id': picking.id})
        wiz.process()

        # Check the average_price of the product (average icecream).
        self.assertEqual(product_icecream.qty_available, 10.0, 'Wrong quantity in stock after first reception')
        self.assertEqual(product_icecream.average_price, 60.0, 'Average price should not have changed!')

        # ------------------------------------------------------------------------------------
        # Create a draft Purchase Order for second incoming shipment for 30kg icecream at 80€/kg
        # ------------------------------------------------------------------------------------

        purchase_order_2 = self._create_purchase(product=product_icecream, uom_id=self.uom_kg_id, product_qty=30.0, price_unit=80.0)
        # Confirm the second purchase order
        purchase_order_2.button_confirm()
        # Process the reception of purchase order 2
        picking = purchase_order_2.picking_ids[0]
        wiz = self.StockTransfer.create({'pick_id': picking.id})
        wiz.process()

        # Check the average price
        self.assertEqual(product_icecream.average_price, 75.0, 'After second reception, we should have an average price of 75.0 on the product')

        # Create picking to send some goods
        outgoing_shipment = self.StockPicking.create({
            'picking_type_id': self.pick_type_out_id,
            'location_id': self.stock_location_id,
            'location_dest_id': self.customer_location_id,
            'move_lines': [(0, 0, {
                'name': 'outgoing_shipment_avg_move',
                'product_id': product_icecream.id,
                'product_uom_qty': 20.0,
                'product_uom': self.uom_kg_id,
                'location_id':  self.stock_location_id,
                'location_dest_id': self.customer_location_id})]
            })

        # Assign this outgoing shipment and process the delivery
        outgoing_shipment.action_assign()
        Wiz = self.StockTransfer.create({'pick_id': outgoing_shipment.id})
        Wiz.process()

        # Check the average price (60 * 10 + 30 * 80) / 40 = 75.0€ did not change
        self.assertEqual(product_icecream.average_price, 75.0, 'Average price should not have changed with outgoing picking!')
        self.assertEqual(product_icecream.qty_available, 20.0, 'Pieces were not picked correctly as the quantity on hand is wrong')

        # Make a new purchase order with 500 g Average Ice Cream at a price of 0.2€/g
        purchase_order_3 = self._create_purchase(product=product_icecream, uom_id=self.ref('product.product_uom_gram'), product_qty=500.0, price_unit=0.2)
        # Confirm the first purchase order
        purchase_order_3.button_confirm()
        # Process the reception of purchase order 3 in grams
        picking = purchase_order_3.picking_ids[0]
        wiz = self.StockTransfer.create({'pick_id': picking.id})
        wiz.process()

        # Check price is (75.0 * 20 + 200*0.5) / 20.5 = 78.04878€
        self.assertEqual(product_icecream.qty_available, 20.5, 'Reception of purchase order in grams leads to wrong quantity in stock')
        self.assertEqual(round(product_icecream.average_price, 2), 78.05, 'Standard price as average price of third reception with other UoM incorrect! Got %s instead of 78.05' % (round(product_icecream.standard_price, 2)))
