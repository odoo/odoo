# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.addons.stock_dropshipping.tests.common import TestStockDropshippingCommon


class TestLifoPrice(TestStockDropshippingCommon):
    def setUp(self):
        super(TestLifoPrice, self).setUp()

        removal_strategy_id = self.env.ref('stock.removal_lifo').id
        self.stock_location_id = self.env.ref('stock.stock_location_stock').id
        self.stock_picking_type_out_id = self.env.ref('stock.picking_type_out').id
        # Set product category removal strategy as LIFO
        product_category_001 = self.ProductCategory.create({
            'name': 'Lifo Category',
            'removal_strategy_id': removal_strategy_id,
            'property_stock_valuation_account_id': self.o_valuation,
            'property_stock_account_output_categ_id': self.o_expense,
            'property_account_income_categ_id': self.o_income,
            'property_stock_account_input_categ_id': self.default_account,
            'property_stock_journal': self.stock_journal,
            'property_account_expense_categ_id': self.default_account})
        # Set a product as using lifo price
        self.product_lifo_icecream = self.Product.create({
            'default_code': 'LIFO', 'name': 'LIFO Ice Cream', 'type': 'product',
            'categ_id': product_category_001.id, 'list_price': 100.0, 'standard_price': 70.0,
            'uom_id': self.product_uom_kgm_id, 'uom_po_id': self.product_uom_kgm_id,
            'valuation': 'real_time', 'cost_method': 'real',
            'property_stock_account_input': self.o_expense, 'property_stock_account_output': self.o_income,
            'description': 'LIFO Ice Cream can be mass-produced and thus is widely available in developed parts '
                           'of the world. Ice cream can be purchased in large cartons (vats and squrounds) from '
                           'supermarkets and grocery stores, in smaller quantities from ice cream shops, '
                           'convenience stores, and milk bars, and in individual servings from small carts or '
                           'vans at public events.'})
        # Create a draft Purchase Order for first in move for 10 pieces at 60 euro
        self.purchase_order_lifo1 = self.PurchaseOrder.create({
           'partner_id': self.partner_cus_a_id,
           'order_line': [(0, 0, {
              'product_id': self.product_lifo_icecream.id, 'product_qty': 10.0,
              'product_uom': self.product_uom_kgm_id, 'price_unit': 60.0,
              'name': 'LIFO Ice Cream', 'date_planned': fields.Date.today()})]
        })
        # Create a draft Purchase Order for second shipment for 30 pieces at 80 euro
        self.purchase_order_lifo2 = self.PurchaseOrder.create({
           'partner_id': self.partner_cus_a_id,
           'order_line': [(0, 0, {
              'product_id': self.product_lifo_icecream.id, 'product_qty': 30.0,
              'product_uom': self.product_uom_kgm_id, 'price_unit': 80.0,
              'name': 'LIFO Ice Cream', 'date_planned': fields.Date.today()})]
        })
        # Let us send some goods
        self.outgoing_lifo_shipment = self.StockPicking.create({
            'picking_type_id': self.stock_picking_type_out_id,
            'location_id': self.stock_location_id, 'location_dest_id': self.stock_location_customer_id
        })
        # Picking needs movement from stock
        self.StockMove.create({
           'name': self.product_lifo_icecream.name, 'picking_id': self.outgoing_lifo_shipment.id,
           'product_id': self.product_lifo_icecream.id, 'product_uom': self.product_uom_kgm_id,
           'location_id': self.stock_location_id, 'location_dest_id': self.stock_location_customer_id,
           'product_uom_qty': 20.0, 'picking_type_id': self.stock_picking_type_out_id
        })

    def test_00_lifo_price(self):
        # Confirm the first purchase order
        self.purchase_order_lifo1.button_confirm()
        # Check the "purchase" status of purchase order 1
        self.assertEqual(self.purchase_order_lifo1.state, 'purchase', 'Purchase order state should be purchase')
        # Process the receipt of purchase order 1
        self.purchase_order_lifo1.picking_ids.do_transfer()
        # Check the standard price of the product (lifo icecream)
        self.assertEqual(self.product_lifo_icecream.standard_price, 70.0, 'Standard price should not have changed!')
        # Confirm the second purchase order
        self.purchase_order_lifo2.button_confirm()
        # Process the receipt of second purchase order
        self.purchase_order_lifo2.picking_ids.do_transfer()
        # Check the standard price should not have changed
        self.assertEqual(self.product_lifo_icecream.standard_price, 70.0, 'Standard price as lifo price of second receipt incorrect!')
        # Assign outgoing shipment
        self.outgoing_lifo_shipment.action_assign()
        # Process the delivery of the outgoing shipment
        self.outgoing_lifo_shipment.do_transfer()
        # Check standard price became 80 euro
        self.assertEqual(self.product_lifo_icecream.standard_price, 80.0, 'Price should have been 80 euro')
