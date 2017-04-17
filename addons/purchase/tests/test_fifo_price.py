# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from .common import TestPurchase


class TestFifoPrice(TestPurchase):

    def test_00_test_fifo(self):
        """ Test product cost price with fifo removal strategy."""

        #  ------------------------------------------------------------------
        #   Create product icecream with standard price 70€
        #   Create a draft purchase Order
        #       First purchase order = 10kg with price 50€/kg
        #   Confirm & receive goods for first purchase order.
        #   Check the status of purchase order ( will be 'purchase')
        #   Check the stock_value of the product ( will be 500.0).
        #       Second purchase order = 30kg with price 80€/kg
        #   Confirm & receive goods for second purchase order.
        #   Check the status of purchase order ( will be 'purchase')
        #   Check the stock_value of the product ( will be 2900.0).
        #   Deliver some goods to customer ( 20kg ).
        #   Check stock_value of product after delivered goods ( will be 1600.0).
        #   Deliver some goods to customer ( 500g ).
        #   Check stock_value of product after delivered goods ( will be 1560.0).
        #   Check qty_available of product ( will be 19.5)
        #  -------------------------------------------------------------------

        self._load('account', 'test', 'account_minimal_test.xml')
        self._load('stock_account', 'test', 'stock_valuation_account.xml')
        self.env.ref('base.main_company').currency_id = self.env.ref('base.EUR')
        product_icecream = self._create_product(self.uom_gram_id,cost_method="fifo",price=70.0)

        # Create draft Purchase Order for first in move for 10kg at 50€/kg
        purchase_order_1 = self.PurchaseOrder.create({
            'partner_id': self.partner_id,
            'order_line': [(0, 0, {
                'name': product_icecream.name,
                'product_id': product_icecream.id,
                'product_qty': 10.0,
                'product_uom': self.uom_kg_id,
                'price_unit': 50,
                'date_planned': time.strftime('%Y-%m-%d')})],
            })

        # Confirm the first purchase order
        purchase_order_1.button_confirm()

        # Check the "Purchase" status of purchase order 1
        self.assertEquals(purchase_order_1.state, 'purchase', 'True')

        # Process the reception of purchase order 1 and set date
        picking = purchase_order_1.picking_ids[0]
        wiz = self.StockTransfer.create({'pick_id': picking.id})
        wiz.process()

        # Check the stock_value  of the product (fifo icecream)
        self.assertEquals(product_icecream.stock_value ,500.0, 'Wrong stock value')

        # Create draft Purchase Order second shipment for 30kg at 80€/kg
        purchase_order_2 = self.PurchaseOrder.create({
            'partner_id': self.partner_id,
            'order_line': [(0, 0, {
                'name': product_icecream.name,
                'product_id': product_icecream.id,
                'product_qty': 30.0,
                'product_uom': self.uom_kg_id,
                'price_unit': 80.0,
                'date_planned': time.strftime('%Y-%m-%d')})],
            })

        # Confirm the second purchase order
        purchase_order_2.button_confirm()
        self.assertEquals(purchase_order_2.state, 'purchase', 'True')

        # Process the reception of purchase order 2
        picking = purchase_order_2.picking_ids[0]
        wiz = self.StockTransfer.create({'pick_id': picking.id})
        wiz.process()

        # Check the stock_value of the product
        self.assertEquals(product_icecream.standard_price ,70.0 , 'Standard price should not have changed!')
        self.assertEquals(product_icecream.stock_value ,2900.0, 'Wrong stock value')


        # Let us send some goods
        outgoing_shipment = self.StockPicking.create({
            'picking_type_id': self.pick_type_out_id,
            'location_id': self.stock_location_id,
            'location_dest_id': self.customer_location_id,
            'move_lines': [(0, 0, {
                'name': product_icecream.name,
                'product_id': product_icecream.id,
                'product_uom_qty': 20.0,
                'product_uom': self.uom_kg_id,
                'location_id': self.stock_location_id,
                'location_dest_id': self.customer_location_id,
                'picking_type_id': self.pick_type_out_id})]
            })
        outgoing_shipment.action_assign()
        Wiz = self.StockTransfer.create({'pick_id': outgoing_shipment.id})
        Wiz.process()

        # Check stock value became 1600 .
        self.assertEqual(product_icecream.stock_value, 1600.0, 'Stock valuation should be 1600')

        # Do a delivery of an extra 500 g (delivery order)
        outgoing_shipment_uom = self.StockPicking.create({
            'picking_type_id': self.pick_type_out_id,
            'location_id': self.stock_location_id,
            'location_dest_id': self.customer_location_id,
            'move_lines': [(0, 0, {
                'name': product_icecream.name,
                'product_id': product_icecream.id,
                'product_uom_qty': 500.0,
                'product_uom': self.uom_gram_id,
                'location_id': self.stock_location_id,
                'location_dest_id': self.customer_location_id,
                'picking_type_id': self.pick_type_out_id})]
            })
        outgoing_shipment_uom.action_assign()
        Wiz = self.StockTransfer.create({'pick_id': outgoing_shipment_uom.id})
        Wiz.process()

        # Check stock valuation and qty in stock
        self.assertEqual(product_icecream.stock_value, 1560.0, 'Stock valuation should be 1560')
        self.assertEqual(product_icecream.qty_available, 19.5, 'Should still have 19.5 in stock')


        # Purchase order in USD
        # 19.5 * 80 = 1600$ available stock
        # -------------------------------------------------------------------------------------------------------------------
        #   Purchase order in USD
        #   Create PO for 30000 g at 0.150$/g and 10 kg at 150$/kg
        #   Confirm & receive the purchase order in $
        #   We create delivery order of ( 49.5 kg )
        #   Assign and Process the delivery of the outgoing shipment
        #   Do a delivery of an extra ( 10 kg )
        #   Assign and Process the delivery of the outgoing shipment
        #   Check rounded price is 150.0 / 1.2834
        # ---------------------------------------------------------------------------------------------------------------------

        NewUSD = self.env['res.currency'].create({
            'name': 'new_usd',
            'symbol': '$²',
            'rate_ids': [(0, 0, { 'rate': 1.2834, 'name': time.strftime('%Y-%m-%d')})],
        })
        # Create PO for 30000 g at 0.150$/g and 10 kg at 150$/kg
        purchase_order_usd = self.PurchaseOrder.create({
            'partner_id': self.partner_id,
            'currency_id': NewUSD.id,
            'order_line': [(0, 0, {
                    'name': product_icecream.name,
                    'product_id': product_icecream.id,
                    'product_qty': 30000,
                    'product_uom': self.uom_gram_id,
                    'price_unit': 0.150,
                    'date_planned': time.strftime('%Y-%m-%d')}),

                (0, 0, {
                    'name': product_icecream.name,
                    'product_id': product_icecream.id,
                    'product_qty': 10.0,
                    'product_uom': self.uom_kg_id,
                    'price_unit': 150.0,
                    'date_planned': time.strftime('%Y-%m-%d')})]
                })

        # Confirm the purchase order in USD
        purchase_order_usd.button_confirm()
        # Process the reception of purchase order with USD
        picking = purchase_order_usd.picking_ids[0]
        wiz = self.StockTransfer.create({'pick_id': picking.id})
        wiz.process()

        # Create delivery order of 49.5 kg
        outgoing_shipment_cur = self.StockPicking.create({
            'picking_type_id': self.pick_type_out_id,
            'location_id': self.stock_location_id,
            'location_dest_id': self.customer_location_id,
            'move_lines': [(0, 0, {
                'name': product_icecream.name,
                'product_id': product_icecream.id,
                'product_uom_qty': 49.5,
                'product_uom': self.uom_kg_id,
                'location_id': self.stock_location_id,
                'location_dest_id': self.customer_location_id,
                'picking_type_id': self.pick_type_out_id})]
            })
        outgoing_shipment_cur.action_assign()
        Wiz = self.StockTransfer.create({'pick_id': outgoing_shipment_cur.id})
        Wiz.process()
        # Do a delivery of an extra 10 kg
        outgoing_shipment_ret = self.StockPicking.create({
            'picking_type_id': self.pick_type_out_id,
            'location_id': self.stock_location_id,
            'location_dest_id': self.customer_location_id,
            'move_lines': [(0, 0, {
                'name': product_icecream.name,
                'product_id': product_icecream.id,
                'product_uom_qty': 10,
                'product_uom': self.uom_kg_id,
                'location_id': self.stock_location_id,
                'location_dest_id': self.customer_location_id,
                'picking_type_id': self.pick_type_out_id})]
            })
        outgoing_shipment_ret.action_assign()
        Wiz = self.StockTransfer.create({'pick_id': outgoing_shipment_ret.id})
        Wiz.process()

        # Check rounded price is 150.0 / 1.2834
        self.assertEqual(round(product_icecream.qty_available), 0.0, 'Wrong quantity in stock after first reception.')

        # -------------------------------------------------------------------------------
        # Create product FIFO Negative with standard price 70€ stock for a new product
        # First delivery order of ( 100 kg )
        # Check stock Qty should be ( -100 )
        # Second delivery order of ( 400 kg )
        # Check stock Qty should be ( -500 )
        # Process the delivery of the first outgoing shipment
        # Receive purchase order with 50 kg FIFO Ice Cream at 50€/kg
        # Check remaining_qty of the move ( 50.0 )
        # Check value of the move ( 2500 )
        # Receive purchase order with 60 kg FIFO Ice Cream at 80€/kg
        # Check qty_available of the product ( 150.0 )
        # Check value of the move ( 6500.0 )
        # Check stock_value of the product ( 12000.0 )
        # -------------------------------------------------------------------------------
        # Let us create some outs to get negative stock for a new product using the same config
        product_fifo_negative = self._create_product(self.uom_kg_id, cost_method="fifo", price=70.0)

        # Create outpicking.create delivery order of 100 kg.
        outgoing_shipment_neg = self.StockPicking.create({
            'picking_type_id': self.pick_type_out_id,
            'location_id': self.stock_location_id,
            'location_dest_id': self.customer_location_id,
            'move_lines': [(0, 0, {
                'name': product_fifo_negative.name,
                'product_id': product_fifo_negative.id,
                'product_uom_qty': 100,
                'product_uom': self.uom_kg_id,
                'location_id': self.stock_location_id,
                'location_dest_id': self.customer_location_id,
                'picking_type_id': self.pick_type_out_id})]
            })
        outgoing_shipment_neg.action_assign()
        Wiz = self.StockTransfer.create({'pick_id': outgoing_shipment_neg.id})
        Wiz.process()

        # Check qty available = -100
        self.assertEqual(product_fifo_negative.qty_available, -100, 'Stock qty should be -100')

        # The behavior of fifo/lifo is not garantee if the quants are created at the same second, so just wait one second
        time.sleep(1)
        # Let create another out shipment of 400 kg
        outgoing_shipment_neg2 = self.StockPicking.create({
            'picking_type_id': self.pick_type_out_id,
            'location_id': self.stock_location_id,
            'location_dest_id': self.customer_location_id,
            'move_lines': [(0, 0, {
                'name': product_fifo_negative.name,
                'product_id': product_fifo_negative.id,
                'product_uom_qty': 400,
                'product_uom': self.uom_kg_id,
                'location_id': self.stock_location_id,
                'location_dest_id': self.customer_location_id,
                'picking_type_id': self.pick_type_out_id})]
            })
        outgoing_shipment_neg2.action_assign()
        Wiz = self.StockTransfer.create({'pick_id': outgoing_shipment_neg2.id})
        Wiz.process()

        # Check qty available = -500
        self.assertEqual(product_fifo_negative.qty_available, -500, 'Stock qty should be -500')

        # Receive purchase order with 50 kg Ice Cream at 50€/kg
        purchase_order_neg = self.PurchaseOrder.create({
            'partner_id': self.partner_id,
            'order_line': [(0, 0, {
                'name': 'FIFO Ice Cream',
                'product_id': product_fifo_negative.id,
                'product_qty': 50.0,
                'product_uom': self.uom_kg_id,
                'price_unit': 50.0,
                'date_planned': time.strftime('%Y-%m-%d')})],
            })
        # I confirm the first purchase order
        purchase_order_neg.button_confirm()
        # Process the reception of purchase order neg
        picking = purchase_order_neg.picking_ids[0]
        wiz = self.StockTransfer.create({'pick_id': picking.id})
        wiz.process()

        original_out_move = outgoing_shipment_neg.move_lines

        self.assertEquals(original_out_move.remaining_qty, 50.0,'On the out move of 100, 50 still needs to be matched')
        self.assertEquals(original_out_move.value, 2500, 'Value of the move should be 2500')

        # Receive purchase order with 600 kg FIFO Ice Cream at 80 euro/kg
        purchase_order_neg2 = self.PurchaseOrder.create({
            'partner_id': self.partner_id,
            'order_line': [(0, 0, {
                'name': product_icecream.name,
                'product_id': product_fifo_negative.id,
                'product_qty': 600.0,
                'product_uom': self.uom_kg_id,
                'price_unit': 80.0,
                'date_planned': time.strftime('%Y-%m-%d')})],
            })
        # I confirm the second negative purchase order
        purchase_order_neg2.button_confirm()
        # Process the reception of purchase order neg2
        picking = purchase_order_neg2.picking_ids[0]
        wiz = self.StockTransfer.create({'pick_id': picking.id})
        wiz.process()
        original_out_move = outgoing_shipment_neg.move_lines

        self.assertEquals(original_out_move.value, 6500.0, 'First original out move should have 6500 as value')
        self.assertEquals(original_out_move.product_id.stock_value,  12000.0, 'Value of the move should be 2500')
        self.assertEquals(original_out_move.product_id.qty_available, 150.0, 'Qty available should be 150')
