# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import tools
from odoo.modules.module import get_module_resource
from odoo.tests import common


class TestLifoPrice(common.TransactionCase):

    def _load(self, module, *args):
        tools.convert_file(
            self.cr, 'stock_dropshipping', get_module_resource(module, *args), {}, 'init', False, 'test', self.registry._assertion_report)

    def test_lifoprice(self):

        self._load('account', 'test', 'account_minimal_test.xml')
        self._load('stock_account', 'test', 'stock_valuation_account.xml')

        # Set the company currency as EURO for the sake of repeatibility
        self.env.ref('base.main_company').write({'currency_id': self.env.ref('base.EUR').id})

        # Set product category removal strategy as LIFO
        product_category_001 = self.env['product.category'].create({
            'name': 'Lifo Category',
            'removal_strategy_id': self.env.ref('stock.removal_lifo').id,
        })

        # Set a product as using lifo price
        product_lifo_icecream = self.env['product.product'].create({
            'default_code': 'LIFO',
            'name': 'LIFO Ice Cream',
            'type': 'product',
            'categ_id': product_category_001.id,
            'list_price': 100.0,
            'standard_price': 70.0,
            'uom_id': self.env.ref('product.product_uom_kgm').id,
            'uom_po_id': self.env.ref('product.product_uom_kgm').id,
            'valuation': 'real_time',
            'cost_method': 'fifo',
            'property_stock_account_input': self.env.ref('stock_dropshipping.o_expense').id,
            'property_stock_account_output': self.env.ref('stock_dropshipping.o_income').id,
        })

        # I create a draft Purchase Order for first in move for 10 pieces at 60 euro
        purchase_order_lifo1 = self.env['purchase.order'].create({
            'partner_id': self.env.ref('base.res_partner_3').id,
            'order_line': [(0, 0, {
                'product_id': product_lifo_icecream.id,
                'product_qty': 10.0,
                'product_uom': self.env.ref('product.product_uom_kgm').id,
                'price_unit': 60.0,
                'name': 'LIFO Ice Cream',
                'date_planned': time.strftime('%Y-%m-%d'),
            })]
        })

        # I create a draft Purchase Order for second shipment for 30 pieces at 80 euro
        purchase_order_lifo2 = self.env['purchase.order'].create({
            'partner_id': self.env.ref('base.res_partner_3').id,
            'order_line': [(0, 0, {
                'product_id': product_lifo_icecream.id,
                'product_qty': 30.0,
                'product_uom': self.env.ref('product.product_uom_kgm').id,
                'price_unit': 80.0,
                'name': 'LIFO Ice Cream',
                'date_planned': time.strftime('%Y-%m-%d'),
            })]
        })

        # I confirm the first purchase order
        purchase_order_lifo1.button_confirm()

        # I check the "Approved" status of purchase order 1
        self.assertEqual(purchase_order_lifo1.state, 'purchase')

        # Process the receipt of purchase order 1
        purchase_order_lifo1.picking_ids[0].move_lines.quantity_done = purchase_order_lifo1.picking_ids[0].move_lines.product_qty
        purchase_order_lifo1.picking_ids[0].button_validate()

        # I confirm the second purchase order
        purchase_order_lifo2.button_confirm()

        # Process the receipt of purchase order 2
        purchase_order_lifo2.picking_ids[0].move_lines.quantity_done = purchase_order_lifo2.picking_ids[0].move_lines.product_qty
        purchase_order_lifo2.picking_ids[0].button_validate()

        # Let us send some goods
        outgoing_lifo_shipment = self.env['stock.picking'].new({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        outgoing_lifo_shipment.onchange_picking_type()
        vals = outgoing_lifo_shipment._convert_to_write(outgoing_lifo_shipment._cache)
        outgoing_lifo_shipment = self.env['stock.picking'].create(vals)

        # Picking needs movement from stock, outgoing_shipment_lifo_icecream
        self.env['stock.move'].create({
            'name': product_lifo_icecream.name,
            'product_id': product_lifo_icecream.id,
            'picking_id': outgoing_lifo_shipment.id,
            'product_uom': self.env.ref('product.product_uom_kgm').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'product_uom_qty': 20.0,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })

        # I assign this outgoing shipment
        outgoing_lifo_shipment.action_assign()
        outgoing_lifo_shipment.move_lines.quantity_done = outgoing_lifo_shipment.move_lines.product_qty

        # Process the delivery of the outgoing shipment
        outgoing_lifo_shipment.button_validate()

        # Check if the move value correctly reflects the fifo costing method
        self.assertEqual(outgoing_lifo_shipment.move_lines.value, -1400.0, 'Stock move value should have been 1400 euro')
