# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from .common import TestPurchase


class TestFifoPrice(TestPurchase):

    def test_00_test_fifo(self):
        """ Test product cost price with fifo removal strategy."""

        self._load('account', 'test', 'account_minimal_test.xml')
        self._load('stock_account', 'test', 'stock_valuation_account.xml')

        # Set a product as using fifo price
        product_cable_management_box = self.env['product.product'].create({
            'default_code': 'FIFO',
            'name': 'FIFO Ice Cream',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_1').id,
            'list_price': 100.0,
            'standard_price': 70.0,
            'uom_id': self.env.ref('uom.product_uom_kgm').id,
            'uom_po_id': self.env.ref('uom.product_uom_kgm').id,
            'supplier_taxes_id': '[]',
            'description': 'FIFO Ice Cream',
        })
        product_cable_management_box.categ_id.property_cost_method = 'fifo'
        product_cable_management_box.categ_id.property_valuation = 'real_time'
        product_cable_management_box.categ_id.property_stock_account_input_categ_id = self.ref('purchase.o_expense')
        product_cable_management_box.categ_id.property_stock_account_output_categ_id = self.ref('purchase.o_income')

        # I create a draft Purchase Order for first in move for 10 kg at 50 euro
        purchase_order_1 = self.env['purchase.order'].create({
            'partner_id': self.env.ref('base.res_partner_3').id,
            'order_line': [(0, 0, {
                'name': 'FIFO Ice Cream',
                'product_id': product_cable_management_box.id,
                'product_qty': 10.0,
                'product_uom': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 50.0,
                'date_planned': time.strftime('%Y-%m-%d')})],
        })

        # Confirm the first purchase order
        purchase_order_1.button_confirm()

        # Check the "Purchase" status of purchase order 1
        self.assertEquals(purchase_order_1.state, 'purchase')

        # Process the reception of purchase order 1 and set date
        picking = purchase_order_1.picking_ids[0]
        self.env['stock.immediate.transfer'].create({'pick_ids': [(4, picking.id)]}).process()

        # Check the standard price of the product (fifo icecream), that should have not changed
        # because the standard price is supposed to be updated only when goods are going out of the stock
        self.assertEquals(product_cable_management_box.standard_price, 70.0, 'Standard price should not have changed')
        self.assertEquals(product_cable_management_box.stock_value, 500.0, 'Wrong stock value')

        # I create a draft Purchase Order for second shipment for 30 kg at 80 euro
        purchase_order_2 = self.env['purchase.order'].create({
            'partner_id': self.env.ref('base.res_partner_3').id,
            'order_line': [(0, 0, {
                'name': 'FIFO Ice Cream',
                'product_id': product_cable_management_box.id,
                'product_qty': 30.0,
                'product_uom': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 80.0,
                'date_planned': time.strftime('%Y-%m-%d')})],
            })

        # Confirm the second purchase order
        purchase_order_2.button_confirm()

        # Process the reception of purchase order 2
        picking = purchase_order_2.picking_ids[0]
        self.env['stock.immediate.transfer'].create({'pick_ids': [(4, picking.id)]}).process()

        # Check the standard price of the product, that should have not changed because the
        # standard price is supposed to be updated only when goods are going out of the stock
        self.assertEquals(product_cable_management_box.standard_price, 70.0, 'Standard price as fifo price of second reception incorrect!')
        self.assertEquals(product_cable_management_box.stock_value, 2900.0, 'Stock valuation should be 2900')

        # Let us send some goods
        outgoing_shipment = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_lines': [(0, 0, {
                'name': product_cable_management_box.name,
                'product_id': product_cable_management_box.id,
                'product_uom_qty': 20.0,
                'product_uom': self.env.ref('uom.product_uom_kgm').id,
                'location_id': self.env.ref('stock.stock_location_stock').id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'picking_type_id': self.env.ref('stock.picking_type_out').id})]
            })

        # I assign this outgoing shipment
        outgoing_shipment.action_assign()

        # Process the delivery of the outgoing shipment
        self.env['stock.immediate.transfer'].create({'pick_ids': [(4, outgoing_shipment.id)]}).process()

        # Check stock value became 1600 .
        self.assertEqual(product_cable_management_box.stock_value, 1600.0, 'Stock valuation should be 1600')

        # Do a delivery of an extra 500 g (delivery order)
        outgoing_shipment_uom = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_lines': [(0, 0, {
                'name': product_cable_management_box.name,
                'product_id': product_cable_management_box.id,
                'product_uom_qty': 500.0,
                'product_uom': self.env.ref('uom.product_uom_gram').id,
                'location_id': self.env.ref('stock.stock_location_stock').id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'picking_type_id': self.env.ref('stock.picking_type_out').id})]
            })

        # I assign this outgoing shipment
        outgoing_shipment_uom.action_assign()

        # Process the delivery of the outgoing shipment
        self.env['stock.immediate.transfer'].create({'pick_ids': [(4, outgoing_shipment_uom.id)]}).process()

        # Check stock valuation and qty in stock
        self.assertEqual(product_cable_management_box.stock_value, 1560.0, 'Stock valuation should be 1560')
        self.assertEqual(product_cable_management_box.qty_available, 19.5, 'Should still have 19.5 in stock')

        # We will temporarily change the currency rate on the sixth of June to have the same results all year
        NewUSD = self.env['res.currency'].create({
            'name': 'new_usd',
            'symbol': '$²',
            'rate_ids': [(0, 0, {'rate': 1.2834, 'name': time.strftime('%Y-%m-%d')})],
        })

        # Create PO for 30000 g at 0.150$/g and 10 kg at 150$/kg
        purchase_order_usd = self.env['purchase.order'].create({
            'partner_id': self.env.ref('base.res_partner_3').id,
            'currency_id': NewUSD.id,
            'order_line': [(0, 0, {
                    'name': 'FIFO Ice Cream',
                    'product_id': product_cable_management_box.id,
                    'product_qty': 30,
                    'product_uom': self.env.ref('uom.product_uom_kgm').id,
                    'price_unit': 0.150,
                    'date_planned': time.strftime('%Y-%m-%d')}),
                (0, 0, {
                    'name': product_cable_management_box.name,
                    'product_id': product_cable_management_box.id,
                    'product_qty': 10.0,
                    'product_uom': self.env.ref('uom.product_uom_kgm').id,
                    'price_unit': 150.0,
                    'date_planned': time.strftime('%Y-%m-%d')})]
                })

        # Confirm the purchase order in USD
        purchase_order_usd.button_confirm()
        # Process the reception of purchase order with USD
        picking = purchase_order_usd.picking_ids[0]
        self.env['stock.immediate.transfer'].create({'pick_ids': [(4, picking.id)]}).process()

        # Create delivery order of 49.5 kg
        outgoing_shipment_cur = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_lines': [(0, 0, {
                'name': product_cable_management_box.name,
                'product_id': product_cable_management_box.id,
                'product_uom_qty': 49.5,
                'product_uom': self.env.ref('uom.product_uom_kgm').id,
                'location_id': self.env.ref('stock.stock_location_stock').id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'picking_type_id': self.env.ref('stock.picking_type_out').id})]
        })

        # I assign this outgoing shipment
        outgoing_shipment_cur.action_assign()

        # Process the delivery of the outgoing shipment
        self.env['stock.immediate.transfer'].create({'pick_ids': [(4, outgoing_shipment_cur.id)]}).process()

        # Do a delivery of an extra 10 kg
        outgoing_shipment_ret = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_lines': [(0, 0, {
                'name': product_cable_management_box.name,
                'product_id': product_cable_management_box.id,
                'product_uom_qty': 10,
                'product_uom': self.env.ref('uom.product_uom_kgm').id,
                'location_id': self.env.ref('stock.stock_location_stock').id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'picking_type_id': self.env.ref('stock.picking_type_out').id})]
            })

        # I assign this outgoing shipment
        outgoing_shipment_ret.action_assign()
        self.env['stock.immediate.transfer'].create({'pick_ids': [(4, outgoing_shipment_ret.id)]}).process()

        # Check rounded price is 150.0 / 1.2834
        self.assertEqual(round(product_cable_management_box.qty_available), 0.0, 'Wrong quantity in stock after first reception.')

        # Let us create some outs to get negative stock for a new product using the same config
        product_fifo_negative = self.env['product.product'].create({
            'default_code': 'NEG',
            'name': 'FIFO Negative',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_1').id,
            'list_price': 100.0,
            'standard_price': 70.0,
            'uom_id': self.env.ref('uom.product_uom_kgm').id,
            'uom_po_id': self.env.ref('uom.product_uom_kgm').id,
            'supplier_taxes_id': '[]',
            'description': 'FIFO Ice Cream',
        })
        product_fifo_negative.categ_id.property_cost_method = 'fifo'
        product_fifo_negative.categ_id.property_valuation = 'real_time'
        product_fifo_negative.categ_id.property_stock_account_input_categ_id = self.ref('purchase.o_expense')
        product_fifo_negative.categ_id.property_stock_account_output_categ_id = self.ref('purchase.o_income')

        # Create outpicking.create delivery order of 100 kg.
        outgoing_shipment_neg = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_lines': [(0, 0, {
                'name': product_fifo_negative.name,
                'product_id': product_fifo_negative.id,
                'product_uom_qty': 100,
                'product_uom': self.env.ref('uom.product_uom_kgm').id,
                'location_id': self.env.ref('stock.stock_location_stock').id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'picking_type_id': self.env.ref('stock.picking_type_out').id})]
        })

        # Process the delivery of the first outgoing shipment
        outgoing_shipment_neg.action_confirm()
        outgoing_shipment_neg.move_lines[0].quantity_done = 100.0
        outgoing_shipment_neg.action_done()

        # Check qty available = -100
        self.assertEqual(product_fifo_negative.qty_available, -100, 'Stock qty should be -100')

        # The behavior of fifo/lifo is not garantee if the quants are created at the same second, so just wait one second
        time.sleep(1)

        # Let create another out shipment of 400 kg
        outgoing_shipment_neg2 = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_lines': [(0, 0, {
                'name': product_fifo_negative.name,
                'product_id': product_fifo_negative.id,
                'product_uom_qty': 400,
                'product_uom': self.env.ref('uom.product_uom_kgm').id,
                'location_id': self.env.ref('stock.stock_location_stock').id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'picking_type_id': self.env.ref('stock.picking_type_out').id})]
        })

        # Process the delivery of the outgoing shipments
        outgoing_shipment_neg2.action_confirm()
        outgoing_shipment_neg2.move_lines[0].quantity_done = 400.0
        outgoing_shipment_neg2.action_done()

        # Check qty available = -500
        self.assertEqual(product_fifo_negative.qty_available, -500, 'Stock qty should be -500')

        # Receive purchase order with 50 kg Ice Cream at 50€/kg
        purchase_order_neg = self.env['purchase.order'].create({
            'partner_id': self.env.ref('base.res_partner_3').id,
            'order_line': [(0, 0, {
                'name': 'FIFO Ice Cream',
                'product_id': product_fifo_negative.id,
                'product_qty': 50.0,
                'product_uom': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 50.0,
                'date_planned': time.strftime('%Y-%m-%d')})],
        })

        # I confirm the first purchase order
        purchase_order_neg.button_confirm()

        # Process the reception of purchase order neg
        picking = purchase_order_neg.picking_ids[0]
        self.env['stock.immediate.transfer'].create({'pick_ids': [(4, picking.id)]}).process()

        # Receive purchase order with 600 kg FIFO Ice Cream at 80 euro/kg
        purchase_order_neg2 = self.env['purchase.order'].create({
            'partner_id': self.env.ref('base.res_partner_3').id,
            'order_line': [(0, 0, {
                'name': product_cable_management_box.name,
                'product_id': product_fifo_negative.id,
                'product_qty': 600.0,
                'product_uom': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 80.0,
                'date_planned': time.strftime('%Y-%m-%d')})],
        })

        # I confirm the second negative purchase order
        purchase_order_neg2.button_confirm()

        # Process the reception of purchase order neg2
        picking = purchase_order_neg2.picking_ids[0]
        self.env['stock.immediate.transfer'].create({'pick_ids': [(4, picking.id)]}).process()

        original_out_move = outgoing_shipment_neg.move_lines[0]
        outgoing_shipment_fifo_icecream_neg2 = outgoing_shipment_neg2.move_lines[0]
        original_out_move._fifo_vacuum()
        outgoing_shipment_fifo_icecream_neg2._fifo_vacuum()
        self.assertEquals(original_out_move.product_id.stock_value,  12000.0, 'Value of the move should be 2500')
        self.assertEquals(original_out_move.product_id.qty_available, 150.0, 'Qty available should be 150')
