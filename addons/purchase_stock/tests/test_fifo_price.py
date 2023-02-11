# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.tests import tagged, Form

import time


@tagged('-at_install', 'post_install')
class TestFifoPrice(ValuationReconciliationTestCommon):

    def test_00_test_fifo(self):
        """ Test product cost price with fifo removal strategy."""

        res_partner_3 = self.env['res.partner'].create({
            'name': 'Gemini Partner',
        })

        # Set a product as using fifo price
        product_cable_management_box = self.env['product.product'].create({
            'default_code': 'FIFO',
            'name': 'FIFO Ice Cream',
            'type': 'product',
            'categ_id': self.stock_account_product_categ.id,
            'list_price': 100.0,
            'standard_price': 70.0,
            'uom_id': self.env.ref('uom.product_uom_kgm').id,
            'uom_po_id': self.env.ref('uom.product_uom_kgm').id,
            'supplier_taxes_id': [],
            'description': 'FIFO Ice Cream',
        })

        # I create a draft Purchase Order for first in move for 10 kg at 50 euro
        purchase_order_1 = self.env['purchase.order'].create({
            'partner_id': res_partner_3.id,
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
        self.assertEqual(purchase_order_1.state, 'purchase')

        # Process the reception of purchase order 1 and set date
        picking = purchase_order_1.picking_ids[0]
        res = picking.button_validate()
        Form(self.env[res['res_model']].with_context(res['context'])).save().process()

        # Check the standard price of the product (fifo icecream), that should have changed
        # because the unit cost of the purchase order is 50
        self.assertAlmostEqual(product_cable_management_box.standard_price, 50.0)
        self.assertEqual(product_cable_management_box.value_svl, 500.0, 'Wrong stock value')

        # I create a draft Purchase Order for second shipment for 30 kg at 80 euro
        purchase_order_2 = self.env['purchase.order'].create({
            'partner_id': res_partner_3.id,
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
        res = picking.button_validate()
        Form(self.env[res['res_model']].with_context(res['context'])).save().process()

        # Check the standard price of the product, that should have not changed because we
        # still have icecream in stock
        self.assertEqual(product_cable_management_box.standard_price, 50.0, 'Standard price as fifo price of second reception incorrect!')
        self.assertEqual(product_cable_management_box.value_svl, 2900.0, 'Stock valuation should be 2900')

        # Let us send some goods
        outgoing_shipment = self.env['stock.picking'].create({
            'picking_type_id': self.company_data['default_warehouse'].out_type_id.id,
            'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_lines': [(0, 0, {
                'name': product_cable_management_box.name,
                'product_id': product_cable_management_box.id,
                'product_uom_qty': 20.0,
                'product_uom': self.env.ref('uom.product_uom_kgm').id,
                'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'picking_type_id': self.company_data['default_warehouse'].out_type_id.id})]
            })

        # I assign this outgoing shipment
        outgoing_shipment.action_assign()

        # Process the delivery of the outgoing shipment
        res = outgoing_shipment.button_validate()
        Form(self.env[res['res_model']].with_context(res['context'])).save().process()

        # Check stock value became 1600 .
        self.assertEqual(product_cable_management_box.value_svl, 1600.0, 'Stock valuation should be 1600')

        # Do a delivery of an extra 500 g (delivery order)
        outgoing_shipment_uom = self.env['stock.picking'].create({
            'picking_type_id': self.company_data['default_warehouse'].out_type_id.id,
            'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_lines': [(0, 0, {
                'name': product_cable_management_box.name,
                'product_id': product_cable_management_box.id,
                'product_uom_qty': 500.0,
                'product_uom': self.env.ref('uom.product_uom_gram').id,
                'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'picking_type_id': self.company_data['default_warehouse'].out_type_id.id})]
            })

        # I assign this outgoing shipment
        outgoing_shipment_uom.action_assign()

        # Process the delivery of the outgoing shipment
        res = outgoing_shipment_uom.button_validate()
        Form(self.env[res['res_model']].with_context(res['context'])).save().process()

        # Check stock valuation and qty in stock
        self.assertEqual(product_cable_management_box.value_svl, 1560.0, 'Stock valuation should be 1560')
        self.assertEqual(product_cable_management_box.qty_available, 19.5, 'Should still have 19.5 in stock')

        # We will temporarily change the currency rate on the sixth of June to have the same results all year
        NewUSD = self.env['res.currency'].create({
            'name': 'new_usd',
            'symbol': '$²',
            'rate_ids': [(0, 0, {'rate': 1.2834, 'name': time.strftime('%Y-%m-%d')})],
        })

        # Create PO for 30000 g at 0.150$/g and 10 kg at 150$/kg
        purchase_order_usd = self.env['purchase.order'].create({
            'partner_id': res_partner_3.id,
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
        res = picking.button_validate()
        Form(self.env[res['res_model']].with_context(res['context'])).save().process()

        # Create delivery order of 49.5 kg
        outgoing_shipment_cur = self.env['stock.picking'].create({
            'picking_type_id': self.company_data['default_warehouse'].out_type_id.id,
            'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_lines': [(0, 0, {
                'name': product_cable_management_box.name,
                'product_id': product_cable_management_box.id,
                'product_uom_qty': 49.5,
                'product_uom': self.env.ref('uom.product_uom_kgm').id,
                'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'picking_type_id': self.company_data['default_warehouse'].out_type_id.id})]
        })

        # I assign this outgoing shipment
        outgoing_shipment_cur.action_assign()

        # Process the delivery of the outgoing shipment
        res = outgoing_shipment_cur.button_validate()
        Form(self.env[res['res_model']].with_context(res['context'])).save().process()

        # Do a delivery of an extra 10 kg
        outgoing_shipment_ret = self.env['stock.picking'].create({
            'picking_type_id': self.company_data['default_warehouse'].out_type_id.id,
            'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_lines': [(0, 0, {
                'name': product_cable_management_box.name,
                'product_id': product_cable_management_box.id,
                'product_uom_qty': 10,
                'product_uom': self.env.ref('uom.product_uom_kgm').id,
                'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'picking_type_id': self.company_data['default_warehouse'].out_type_id.id})]
            })

        # I assign this outgoing shipment
        outgoing_shipment_ret.action_assign()
        res = outgoing_shipment_ret.button_validate()
        Form(self.env[res['res_model']].with_context(res['context'])).save().process()

        # Check rounded price is 150.0 / 1.2834
        self.assertEqual(round(product_cable_management_box.qty_available), 0.0, 'Wrong quantity in stock after first reception.')

        # Let us create some outs to get negative stock for a new product using the same config
        product_fifo_negative = self.env['product.product'].create({
            'default_code': 'NEG',
            'name': 'FIFO Negative',
            'type': 'product',
            'categ_id': self.stock_account_product_categ.id,
            'list_price': 100.0,
            'standard_price': 70.0,
            'uom_id': self.env.ref('uom.product_uom_kgm').id,
            'uom_po_id': self.env.ref('uom.product_uom_kgm').id,
            'supplier_taxes_id': [],
            'description': 'FIFO Ice Cream',
        })

        # Create outpicking.create delivery order of 100 kg.
        outgoing_shipment_neg = self.env['stock.picking'].create({
            'picking_type_id': self.company_data['default_warehouse'].out_type_id.id,
            'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_lines': [(0, 0, {
                'name': product_fifo_negative.name,
                'product_id': product_fifo_negative.id,
                'product_uom_qty': 100,
                'product_uom': self.env.ref('uom.product_uom_kgm').id,
                'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'picking_type_id': self.company_data['default_warehouse'].out_type_id.id})]
        })

        # Process the delivery of the first outgoing shipment
        outgoing_shipment_neg.action_confirm()
        outgoing_shipment_neg.move_lines[0].quantity_done = 100.0
        outgoing_shipment_neg._action_done()

        # Check qty available = -100
        self.assertEqual(product_fifo_negative.qty_available, -100, 'Stock qty should be -100')

        # The behavior of fifo/lifo is not garantee if the quants are created at the same second, so just wait one second
        time.sleep(1)

        # Let create another out shipment of 400 kg
        outgoing_shipment_neg2 = self.env['stock.picking'].create({
            'picking_type_id': self.company_data['default_warehouse'].out_type_id.id,
            'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_lines': [(0, 0, {
                'name': product_fifo_negative.name,
                'product_id': product_fifo_negative.id,
                'product_uom_qty': 400,
                'product_uom': self.env.ref('uom.product_uom_kgm').id,
                'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'picking_type_id': self.company_data['default_warehouse'].out_type_id.id})]
        })

        # Process the delivery of the outgoing shipments
        outgoing_shipment_neg2.action_confirm()
        outgoing_shipment_neg2.move_lines[0].quantity_done = 400.0
        outgoing_shipment_neg2._action_done()

        # Check qty available = -500
        self.assertEqual(product_fifo_negative.qty_available, -500, 'Stock qty should be -500')

        # Receive purchase order with 50 kg Ice Cream at 50€/kg
        purchase_order_neg = self.env['purchase.order'].create({
            'partner_id': res_partner_3.id,
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
        res = picking.button_validate()
        Form(self.env[res['res_model']].with_context(res['context'])).save().process()

        # Receive purchase order with 600 kg FIFO Ice Cream at 80 euro/kg
        purchase_order_neg2 = self.env['purchase.order'].create({
            'partner_id': res_partner_3.id,
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
        res = picking.button_validate()
        Form(self.env[res['res_model']].with_context(res['context'])).save().process()

        original_out_move = outgoing_shipment_neg.move_lines[0]
        self.assertEqual(original_out_move.product_id.value_svl,  12000.0, 'Value of the move should be 12000')
        self.assertEqual(original_out_move.product_id.qty_available, 150.0, 'Qty available should be 150')

    def test_01_test_fifo(self):
        """" This test ensures that unit price keeps its decimal precision """

        unit_price_precision = self.env.ref('product.decimal_price')
        unit_price_precision.digits = 3

        tax = self.env["account.tax"].create({
            "name": "Dummy Tax",
            "amount": "0.00",
            "type_tax_use": "purchase",
        })

        super_product = self.env['product.product'].create({
            'name': 'Super Product',
            'type': 'product',
            'categ_id': self.stock_account_product_categ.id,
            'standard_price': 0.035,
        })
        self.assertEqual(super_product.cost_method, 'fifo')
        self.assertEqual(super_product.valuation, 'real_time')

        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.env.ref('base.res_partner_3').id,
            'order_line': [(0, 0, {
                'name': super_product.name,
                'product_id': super_product.id,
                'product_qty': 1000,
                'product_uom': super_product.uom_id.id,
                'price_unit': super_product.standard_price,
                'date_planned': time.strftime('%Y-%m-%d'),
                'taxes_id': [(4, tax.id)],
            })],
        })

        purchase_order.button_confirm()
        self.assertEqual(purchase_order.state, 'purchase')

        picking = purchase_order.picking_ids[0]
        res = picking.button_validate()
        Form(self.env[res['res_model']].with_context(res['context'])).save().process()

        self.assertEqual(super_product.standard_price, 0.035)
        self.assertEqual(super_product.value_svl, 35.0)
        self.assertEqual(picking.move_lines.price_unit, 0.035)
