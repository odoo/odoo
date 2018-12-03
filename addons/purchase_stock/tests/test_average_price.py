# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from .common import TestPurchase


class TestAveragePrice(TestPurchase):

    def test_00_average_price(self):
        """ Testcase for average price computation"""

        self._load('account', 'test', 'account_minimal_test.xml')
        self._load('stock_account', 'test', 'stock_valuation_account.xml')

        # Set a product as using average price.
        product_cable_management_box = self.env['product.product'].create({
            'default_code': 'AVG',
            'name': 'Average Ice Cream',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_1').id,
            'list_price': 100.0,
            'standard_price': 60.0,
            'uom_id': self.env.ref('uom.product_uom_kgm').id,
            'uom_po_id': self.env.ref('uom.product_uom_kgm').id,
            'supplier_taxes_id': [],
            'description': 'FIFO Ice Cream',
        })
        product_cable_management_box.categ_id.property_cost_method = 'average'
        product_cable_management_box.categ_id.property_valuation = 'real_time'
        product_cable_management_box.categ_id.property_stock_account_input_categ_id = self.ref('purchase.o_expense')
        product_cable_management_box.categ_id.property_stock_account_output_categ_id = self.ref('purchase.o_income')

        # I create a draft Purchase Order for first incoming shipment for 10 pieces at 60€
        purchase_order_1 = self.env['purchase.order'].create({
            'partner_id': self.env.ref('base.res_partner_3').id,
            'order_line': [(0, 0, {
                'name': 'Average Ice Cream',
                'product_id': product_cable_management_box.id,
                'product_qty': 10.0,
                'product_uom': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 60.0,
                'date_planned': time.strftime('%Y-%m-%d'),
            })]
        })

        # Confirm the first purchase order
        purchase_order_1.button_confirm()

        # Check the "Approved" status of purchase order 1
        self.assertEqual(purchase_order_1.state, 'purchase', "Wrong state of purchase order!")

        # Process the reception of purchase order 1
        picking = purchase_order_1.picking_ids[0]
        self.env['stock.immediate.transfer'].create({'pick_ids': [(4, picking.id)]}).process()

        # Check the average_price of the product (average icecream).
        self.assertEqual(product_cable_management_box.qty_available, 10.0, 'Wrong quantity in stock after first reception')
        self.assertEqual(product_cable_management_box.standard_price, 60.0, 'Standard price should be the price of the first reception!')

        # I create a draft Purchase Order for second incoming shipment for 30 pieces at 80€
        purchase_order_2 = self.env['purchase.order'].create({
            'partner_id': self.env.ref('base.res_partner_3').id,
            'order_line': [(0, 0, {
                'name': product_cable_management_box.name,
                'product_id': product_cable_management_box.id,
                'product_qty': 30.0,
                'product_uom': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 80.0,
                'date_planned': time.strftime('%Y-%m-%d'),
            })]
        })

        # Confirm the second purchase order
        purchase_order_2.button_confirm()
        # Process the reception of purchase order 2
        picking = purchase_order_2.picking_ids[0]
        self.env['stock.immediate.transfer'].create({'pick_ids': [(4, picking.id)]}).process()

        # Check the standard price
        self.assertEqual(product_cable_management_box.standard_price, 75.0, 'After second reception, we should have an average price of 75.0 on the product')

        # Create picking to send some goods
        outgoing_shipment = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_lines': [(0, 0, {
                'name': 'outgoing_shipment_avg_move',
                'product_id': product_cable_management_box.id,
                'product_uom_qty': 20.0,
                'product_uom': self.env.ref('uom.product_uom_kgm').id,
                'location_id':  self.env.ref('stock.stock_location_stock').id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id})]
            })

        # Assign this outgoing shipment and process the delivery
        outgoing_shipment.action_assign()
        self.env['stock.immediate.transfer'].create({'pick_ids': [(4, outgoing_shipment.id)]}).process()

        # Check the average price (60 * 10 + 30 * 80) / 40 = 75.0€ did not change
        self.assertEqual(product_cable_management_box.standard_price, 75.0, 'Average price should not have changed with outgoing picking!')
        self.assertEqual(product_cable_management_box.qty_available, 20.0, 'Pieces were not picked correctly as the quantity on hand is wrong')

        # Make a new purchase order with 500 g Average Ice Cream at a price of 0.2€/g
        purchase_order_3 = self.env['purchase.order'].create({
            'partner_id': self.env.ref('base.res_partner_3').id,
            'order_line': [(0, 0, {
                'name': product_cable_management_box.name,
                'product_id': product_cable_management_box.id,
                'product_qty': 500.0,
                'product_uom': self.ref('uom.product_uom_gram'),
                'price_unit': 0.2,
                'date_planned': time.strftime('%Y-%m-%d'),
            })]
        })

        # Confirm the first purchase order
        purchase_order_3.button_confirm()
        # Process the reception of purchase order 3 in grams
        picking = purchase_order_3.picking_ids[0]
        self.env['stock.immediate.transfer'].create({'pick_ids': [(4, picking.id)]}).process()

        # Check price is (75.0 * 20 + 200*0.5) / 20.5 = 78.04878€
        self.assertEqual(product_cable_management_box.qty_available, 20.5, 'Reception of purchase order in grams leads to wrong quantity in stock')
        self.assertEqual(round(product_cable_management_box.standard_price, 2), 78.05,
            'Standard price as average price of third reception with other UoM incorrect! Got %s instead of 78.05' % (round(product_cable_management_box.standard_price, 2)))
