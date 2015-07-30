# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.tests import common
from datetime import datetime


class TestSaleMargin(common.TransactionCase):

    def setUp(self):
        super(TestSaleMargin, self).setUp()
        self.SaleOrder = self.env['sale.order']

        self.product_uom = self.env.ref('product.product_uom_unit')
        self.product = self.env.ref('product.product_product_24')
        self.partner = self.env.ref('base.res_partner_4')
        self.partner_invoice_address = self.env.ref('base.res_partner_address_7')
        self.pricelist = self.env.ref('product.list0')

    def test_00_sale_margin(self):
        """ Test the sale_margin module in Odoo. """
        # Create a sale order for product Graphics Card, quantity 100.
        order = self.SaleOrder.create({
            'date_order': datetime.today(),
            'name': 'Test_SO011',
            'order_line': [(0, 0, {
                'name': '[CARD] Graphics Card',
                'price_unit': 7.0,
                'product_uom': self.product_uom.id,
                'product_uom_qty': 100.0,
                'state': 'draft',
                'product_id': self.product.id,
                'product_uos_qty': 100.0,
                'th_weight': 0.0})],
            'order_policy': 'manual',
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner_invoice_address.id,
            'partner_shipping_id': self.partner_invoice_address.id,
            'pricelist_id': self.pricelist.id})
        # Confirm the sale order.
        order.signal_workflow('order_confirm')
        # Verify that margin field gets bind with the value.
        self.assertTrue(order.margin, "No margin !")