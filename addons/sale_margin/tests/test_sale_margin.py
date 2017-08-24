# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
from datetime import datetime


class TestSaleMargin(common.TransactionCase):

    def setUp(self):
        super(TestSaleMargin, self).setUp()
        self.SaleOrder = self.env['sale.order']

        self.product_uom_id = self.ref('product.product_uom_unit')
        self.product_id = self.ref('product.product_product_24')
        self.partner_id = self.ref('base.res_partner_4')
        self.partner_invoice_address_id = self.ref('base.res_partner_address_7')
        self.pricelist_id = self.ref('product.list0')

    def test_sale_margin(self):
        """ Test the sale_margin module in Odoo. """
        # Create a sale order for product Graphics Card.
        sale_order_so11 = self.SaleOrder.create({
            'date_order': datetime.today(),
            'name': 'Test_SO011',
            'order_line': [
                (0, 0, {
                    'name': '[CARD] Graphics Card',
                    'purchase_price': 700.0,
                    'price_unit': 1000.0,
                    'product_uom': self.product_uom_id,
                    'product_uom_qty': 10.0,
                    'state': 'draft',
                    'product_id': self.product_id}),
                (0, 0, {
                    'name': 'Line without product_uom',
                    'price_unit': 1000.0,
                    'purchase_price': 700.0,
                    'product_uom_qty': 10.0,
                    'state': 'draft',
                    'product_id': self.product_id})],
            'partner_id': self.partner_id,
            'partner_invoice_id': self.partner_invoice_address_id,
            'partner_shipping_id': self.partner_invoice_address_id,
            'pricelist_id': self.pricelist_id})
        # Confirm the sale order.
        sale_order_so11.action_confirm()
        # Verify that margin field gets bind with the value.
        self.assertEqual(sale_order_so11.margin, 6000.00, "Sale order margin should be 6000.00")
