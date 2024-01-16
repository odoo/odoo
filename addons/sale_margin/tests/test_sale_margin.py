# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
from odoo.fields import Command
from datetime import datetime


class TestSaleMargin(common.TransactionCase):

    def setUp(self):
        super(TestSaleMargin, self).setUp()
        self.SaleOrder = self.env['sale.order']

        self.product_uom_id = self.ref('uom.product_uom_unit')
        self.product = self.env['product.product'].create({'name': 'Individual Workplace'})
        self.product_id = self.product.id
        self.partner_id = self.env['res.partner'].create({'name': 'A test partner'}).id
        self.partner_invoice_address_id = self.env['res.partner'].create({
            'name': 'A test partner address',
            'parent_id': self.partner_id,
        }).id
        self.pricelist_id = self.ref('product.list0')
        self.pricelist = self.env.ref('product.list0')

    def test_sale_margin(self):
        """ Test the sale_margin module in Odoo. """
        self.pricelist.currency_id = self.env.company.currency_id
        self.product.standard_price = 700.0
        sale_order_so11 = self.SaleOrder.create({
            'date_order': datetime.today(),
            'name': 'Test_SO011',
            'order_line': [
                (0, 0, {
                    'name': '[CARD] Individual Workplace',
                    'price_unit': 1000.0,
                    'product_uom': self.product_uom_id,
                    'product_uom_qty': 10.0,
                    'state': 'draft',
                    'product_id': self.product_id}),
                (0, 0, {
                    'name': 'Line without product_uom',
                    'price_unit': 1000.0,
                    'product_uom_qty': 10.0,
                    'state': 'draft',
                    'product_id': self.product_id})],
            'partner_id': self.partner_id,
            'partner_invoice_id': self.partner_invoice_address_id,
            'partner_shipping_id': self.partner_invoice_address_id,
            'pricelist_id': self.pricelist_id})
        # Confirm the sales order.
        sale_order_so11.action_confirm()
        # Verify that margin field gets bind with the value.
        self.assertEqual(sale_order_so11.margin, 6000.00, "Sales order profit should be 6000.00")
        self.assertEqual(sale_order_so11.margin_percent, 0.3, "Sales order margin should be 30%")
        sale_order_so11.order_line[1].purchase_price = 800
        self.assertEqual(sale_order_so11.margin, 5000.00, "Sales order margin should be 5000.00")

    def test_sale_margin1(self):
        """ Test the margin when sales price is less then cost."""
        sale_order_so12 = self.SaleOrder.create({
            'date_order': datetime.today(),
            'name': 'Test_SO012',
            'order_line': [
                (0, 0, {
                    'name': '[CARD] Individual Workplace',
                    'purchase_price': 40.0,
                    'price_unit': 20.0,
                    'product_uom': self.product_uom_id,
                    'product_uom_qty': 1.0,
                    'state': 'draft',
                    'product_id': self.product_id}),
                (0, 0, {
                    'name': 'Line without product_uom',
                    'price_unit': -100.0,
                    'purchase_price': 0.0,
                    'product_uom_qty': 1.0,
                    'state': 'draft',
                    'product_id': self.product_id})],
            'partner_id': self.partner_id,
            'partner_invoice_id': self.partner_invoice_address_id,
            'partner_shipping_id': self.partner_invoice_address_id,
            'pricelist_id': self.pricelist_id})
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
        sale_order_so13 = self.SaleOrder.create({
            'date_order': datetime.today(),
            'name': 'Test_SO013',
            'order_line': [
                (0, 0, {
                    'name': '[CARD] Individual Workplace',
                    'purchase_price': 0.0,
                    'price_unit': 70.0,
                    'product_uom': self.product_uom_id,
                    'product_uom_qty': 1.0,
                    'state': 'draft',
                    'product_id': self.product_id})],
            'partner_id': self.partner_id,
            'partner_invoice_id': self.partner_invoice_address_id,
            'partner_shipping_id': self.partner_invoice_address_id,
            'pricelist_id': self.pricelist_id})
        # Verify that margin field of Sale Order Lines gets bind with the value.
        self.assertEqual(sale_order_so13.order_line[0].margin, 70.00, "Sales order profit should be 70.00")
        self.assertEqual(sale_order_so13.order_line[0].margin_percent, 1.0, "Sales order margin percentage should be 100.00")
        # Verify that margin field gets bind with the value.
        self.assertEqual(sale_order_so13.margin, 70.00, "Sales order profit should be 70.00")
        self.assertEqual(sale_order_so13.margin_percent, 1.00, "Sales order margin percentage should be 100.00")

    def test_sale_margin3(self):
        """ Test the margin and margin percentage when product with multiple quantity"""
        sale_order_so14 = self.SaleOrder.create({
            'date_order': datetime.today(),
            'name': 'Test_SO014',
            'order_line': [
                (0, 0, {
                    'name': '[CARD] Individual Workplace',
                    'purchase_price': 50.0,
                    'price_unit': 100.0,
                    'product_uom': self.product_uom_id,
                    'product_uom_qty': 3.0,
                    'state': 'draft',
                    'product_id': self.product_id}),
                (0, 0, {
                    'name': 'Line without product_uom',
                    'price_unit': -50.0,
                    'purchase_price': 0.0,
                    'product_uom_qty': 1.0,
                    'state': 'draft',
                    'product_id': self.product_id})],
            'partner_id': self.partner_id,
            'partner_invoice_id': self.partner_invoice_address_id,
            'partner_shipping_id': self.partner_invoice_address_id,
            'pricelist_id': self.pricelist_id})
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

    def test_sale_margin_order_copy(self):
        """When we copy a sales order, its margins should be update to meet the current costs"""
        self.pricelist.currency_id = self.env.company.currency_id
        # We buy at a specific price today and our margins go according to that
        self.product.standard_price = 500.0
        original_sale = self.SaleOrder.create({
            'partner_id': self.partner_id,
            'partner_invoice_id': self.partner_invoice_address_id,
            'partner_shipping_id': self.partner_invoice_address_id,
            'pricelist_id': self.pricelist_id,
            'order_line': [
                Command.create({
                    'price_unit': 1000.0,
                    'product_uom': self.product_uom_id,
                    'product_uom_qty': 10.0,
                    'product_id': self.product.id,
                }),
            ],
        })
        self.assertAlmostEqual(500.0, original_sale.order_line.purchase_price)
        self.assertAlmostEqual(5000.0, original_sale.order_line.margin)
        self.assertAlmostEqual(.5, original_sale.order_line.margin_percent)
        # Later on, the cost of our product changes and so will the following sale
        # margins do.
        self.product.standard_price = 750.0
        following_sale = original_sale.copy()
        self.assertAlmostEqual(750.0, following_sale.order_line.purchase_price)
        self.assertAlmostEqual(2500.0, following_sale.order_line.margin)
        self.assertAlmostEqual(.25, following_sale.order_line.margin_percent)
