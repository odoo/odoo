# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
from datetime import datetime


class TestSaleMargin(common.TransactionCase):

    def setUp(self):
        super(TestSaleMargin, self).setUp()
        self.SaleOrder = self.env['sale.order']

        self.product = self.env['product.product'].create({'name': 'Individual Workplace'})
        self.product_id = self.product.id
        self.product2 = self.env['product.product'].create({'name': 'P2'})
        self.product2_id = self.product2.id
        self.partner = self.env['res.partner'].create({'name': 'A test partner'})
        self.partner_id = self.partner.id
        self.pricelist = self.env.ref('product.list0')
        self.pricelist_id = self.pricelist.id
        self.pricelist.currency_id = self.env.company.currency_id
        self.partner.property_product_pricelist = self.pricelist_id

    def test_sale_margin(self):
        """ Test the sale_margin module in Odoo. """
        self.product.standard_price = 700.0
        self.product.lst_price = 1000.0
        sale_order_so11 = self.SaleOrder.create({
            'date_order': datetime.today(),
            'name': 'Test_SO011',
            'order_line': [
                (0, 0, {
                    'product_uom_qty': 10.0,
                    'product_id': self.product_id,
                }),
                (0, 0, {
                    'product_uom_qty': 10.0,
                    'product_id': self.product_id,
                }),
            ],
            'partner_id': self.partner_id,
        })
        # Confirm the sales order.
        sale_order_so11.action_confirm()
        # Verify that margin field gets bind with the value.
        self.assertEqual(sale_order_so11.pricelist_id, self.pricelist)
        self.assertEqual(sale_order_so11.margin, 6000.00, "Sales order profit should be 6000.00")
        self.assertEqual(sale_order_so11.margin_percent, 0.3, "Sales order margin should be 30%")
        sale_order_so11.order_line[1].purchase_price = 800
        self.assertEqual(sale_order_so11.margin, 5000.00, "Sales order margin should be 5000.00")

    def test_sale_margin1(self):
        """ Test the margin when sales price is less then cost."""
        self.product.lst_price = 20.0
        self.product.standard_price = 40.0
        self.product2.lst_price = -100
        sale_order_so12 = self.SaleOrder.create({
            'date_order': datetime.today(),
            'name': 'Test_SO012',
            'order_line': [
                (0, 0, {
                    'product_uom_qty': 1.0,
                    'product_id': self.product_id,
                }),
                (0, 0, {
                    'product_uom_qty': 1.0,
                    'product_id': self.product2_id,
                }),
            ],
            'partner_id': self.partner_id,
        })
        # Confirm the sales order.
        sale_order_so12.action_confirm()
        # Verify that margin field of Sale Order Lines gets bind with the value.
        self.assertEqual(sale_order_so12.order_line[0].margin, -20.00, "Sales order profit should be -20.00")
        self.assertEqual(sale_order_so12.order_line[0].margin_percent, -1, "Sales order margin percentage should be -100%")
        self.assertEqual(sale_order_so12.order_line[1].margin, -100.00, "Sales order profit should be -100.00")
        self.assertEqual(sale_order_so12.order_line[1].margin_percent, 1.00, "Sales order margin should be 100% when the cost is zero and price defined")
        # Verify that margin field gets bind with the value.
        self.assertEqual(sale_order_so12.margin, -120.00, "Sales order margin should be -120.00")
        self.assertEqual(sale_order_so12.margin_percent, 1.5, "Sales order margin should be 150%")

    def test_sale_margin2(self):
        """ Test the margin when cost is 0 margin percentage should always be 100%."""
        self.product.lst_price = 70.0
        sale_order_so13 = self.SaleOrder.create({
            'date_order': datetime.today(),
            'name': 'Test_SO013',
            'order_line': [
                (0, 0, {
                    'product_uom_qty': 1.0,
                    'product_id': self.product_id,
                }),
            ],
            'partner_id': self.partner_id,
        })
        # Verify that margin field of Sale Order Lines gets bind with the value.
        self.assertEqual(sale_order_so13.order_line[0].margin, 70.00, "Sales order profit should be 70.00")
        self.assertEqual(sale_order_so13.order_line[0].margin_percent, 1.0, "Sales order margin percentage should be 100.00")
        # Verify that margin field gets bind with the value.
        self.assertEqual(sale_order_so13.margin, 70.00, "Sales order profit should be 70.00")
        self.assertEqual(sale_order_so13.margin_percent, 1.00, "Sales order margin percentage should be 100.00")

    def test_sale_margin3(self):
        """ Test the margin and margin percentage when product with multiple quantity"""
        self.product.lst_price = 100.0
        self.product.standard_price = 50.0
        self.product2.lst_price = -50.0
        self.product2.standard_price = 0.0
        sale_order_so14 = self.SaleOrder.create({
            'date_order': datetime.today(),
            'name': 'Test_SO014',
            'order_line': [
                (0, 0, {
                    'product_uom_qty': 3.0,
                    'product_id': self.product_id,
                }),
                (0, 0, {
                    'product_uom_qty': 1.0,
                    'product_id': self.product2_id,
                }),
            ],
            'partner_id': self.partner_id,
        })
        # Confirm the sales order.
        sale_order_so14.action_confirm()
        # Verify that margin field of Sale Order Lines gets bind with the value.
        self.assertEqual(sale_order_so14.order_line[0].margin, 150.00, "Sales order profit should be 150.00")
        self.assertEqual(sale_order_so14.order_line[0].margin_percent, 0.5, "Sales order margin should be 100%")
        self.assertEqual(sale_order_so14.order_line[1].margin, -50.00, "Sales order profit should be -50.00")
        self.assertEqual(sale_order_so14.order_line[1].margin_percent, 1.0, "Sales order margin should be 100%")
        # Verify that margin field gets bind with the value.
        self.assertEqual(sale_order_so14.margin, 100.00, "Sales order profit should be 100.00")
        self.assertEqual(sale_order_so14.margin_percent, 0.4, "Sales order margin should be 40%")
