# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.addons.sale.tests.common import SaleCommon


class TestSaleMargin(SaleCommon):

    def test_sale_margin(self):
        """ Test the sale_margin module in Odoo. """
        self.product.standard_price = 700.0
        order = self.empty_order

        order.order_line = [
            Command.create({
                'price_unit': 1000.0,
                'product_uom_qty': 10.0,
                'product_id': self.product.id,
            }),
        ]
        # Confirm the sales order.
        order.action_confirm()
        # Verify that margin field gets bind with the value.
        self.assertEqual(order.margin, 3000.00, "Sales order profit should be 6000.00")
        self.assertEqual(order.margin_percent, 0.3, "Sales order margin should be 30%")

    def test_negative_margin(self):
        """ Test the margin when sales price is less then cost."""
        order = self.empty_order
        self.service_product.standard_price = 40.0

        order.order_line = [
            Command.create({
                'price_unit': 20.0,
                'product_uom_qty': 1.0,
                'state': 'draft',
                'product_id': self.service_product.id,
            }),
            Command.create({
                'price_unit': -100.0,
                'purchase_price': 0.0,
                'product_uom_qty': 1.0,
                'state': 'draft',
                'product_id': self.product.id,
            }),
        ]
        # Confirm the sales order.
        order.action_confirm()
        # Verify that margin field of Sale Order Lines gets bind with the value.
        self.assertEqual(order.order_line[0].margin, -20.00, "Sales order profit should be -20.00")
        self.assertEqual(order.order_line[0].margin_percent, -1, "Sales order margin percentage should be -100%")
        self.assertEqual(order.order_line[1].margin, -100.00, "Sales order profit should be -100.00")
        self.assertEqual(order.order_line[1].margin_percent, 1.00, "Sales order margin should be 100% when the cost is zero and price defined")
        # Verify that margin field gets bind with the value.
        self.assertEqual(order.margin, -120.00, "Sales order margin should be -120.00")
        self.assertEqual(order.margin_percent, 1.5, "Sales order margin should be 150%")

    def test_margin_no_cost(self):
        """ Test the margin when cost is 0 margin percentage should always be 100%."""
        order = self.empty_order
        order.order_line = [Command.create({
            'product_id': self.product.id,
            'price_unit': 70.0,
            'product_uom_qty': 1.0,
        })]

        # Verify that margin field of Sale Order Lines gets bind with the value.
        self.assertEqual(order.order_line[0].margin, 70.00, "Sales order profit should be 70.00")
        self.assertEqual(order.order_line[0].margin_percent, 1.0, "Sales order margin percentage should be 100.00")
        # Verify that margin field gets bind with the value.
        self.assertEqual(order.margin, 70.00, "Sales order profit should be 70.00")
        self.assertEqual(order.margin_percent, 1.00, "Sales order margin percentage should be 100.00")

    def test_margin_considering_product_qty(self):
        """ Test the margin and margin percentage when product with multiple quantity"""
        order = self.empty_order
        self.service_product.standard_price = 50.0

        order.order_line = [
            Command.create({
                'price_unit': 100.0,
                'product_uom_qty': 3.0,
                'product_id': self.service_product.id,
            }),
            Command.create({
                'price_unit': -50.0,
                'product_uom_qty': 1.0,
                'product_id': self.product.id,
            }),
        ]

        # Confirm the sales order.
        order.action_confirm()
        # Verify that margin field of Sale Order Lines gets bind with the value.
        self.assertEqual(order.order_line[0].margin, 150.00, "Sales order profit should be 150.00")
        self.assertEqual(order.order_line[0].margin_percent, 0.5, "Sales order margin should be 100%")
        self.assertEqual(order.order_line[1].margin, -50.00, "Sales order profit should be -50.00")
        self.assertEqual(order.order_line[1].margin_percent, 1.0, "Sales order margin should be 100%")
        # Verify that margin field gets bind with the value.
        self.assertEqual(order.margin, 100.00, "Sales order profit should be 100.00")
        self.assertEqual(order.margin_percent, 0.4, "Sales order margin should be 40%")

    def test_sale_margin_order_copy(self):
        """When we copy a sales order, its margins should be update to meet the current costs"""
        order = self.empty_order
        self.pricelist.currency_id = self.env.company.currency_id
        # We buy at a specific price today and our margins go according to that
        self.product.standard_price = 500.0
        order.order_line = [
            Command.create({
                'price_unit': 1000.0,
                'product_uom_qty': 10.0,
                'product_id': self.product.id,
            }),
        ]
        self.assertAlmostEqual(500.0, order.order_line.purchase_price)
        self.assertAlmostEqual(5000.0, order.order_line.margin)
        self.assertAlmostEqual(.5, order.order_line.margin_percent)
        # Later on, the cost of our product changes and so will the following sale
        # margins do.
        self.product.standard_price = 750.0
        following_sale = order.copy()
        self.assertAlmostEqual(750.0, following_sale.order_line.purchase_price)
        self.assertAlmostEqual(2500.0, following_sale.order_line.margin)
        self.assertAlmostEqual(.25, following_sale.order_line.margin_percent)
