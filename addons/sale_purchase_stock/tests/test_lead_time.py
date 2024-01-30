# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields
from odoo.tests import tagged
from odoo.addons.sale_purchase.tests.common import TestCommonSalePurchaseNoChart


@tagged('post_install', '-at_install')
class TestLeadTime(TestCommonSalePurchaseNoChart):

    @classmethod
    def setUpClass(cls):
        super(TestLeadTime, cls).setUpClass()

        cls.buy_route = cls.env.ref('purchase_stock.route_warehouse0_buy')
        cls.mto_route = cls.env.ref('stock.route_warehouse0_mto')
        cls.mto_route.active = True
        cls.vendor = cls.env['res.partner'].create({'name': 'The Emperor'})
        cls.user_salesperson = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Le Grand Horus',
            'login': 'grand.horus',
            'email': 'grand.horus@chansonbelge.dz',
        })


    def test_supplier_lead_time(self):
        """ Basic stock configuration and a supplier with a minimum qty and a lead time """

        self.env.user.company_id.po_lead = 7
        seller = self.env['product.supplierinfo'].create({
            'name': self.vendor.id,
            'min_qty': 1,
            'price': 10,
            'date_start': fields.Date.today() - timedelta(days=1),
        })

        product = self.env['product.product'].create({
            'name': 'corpse starch',
            'type': 'product',
            'seller_ids': [(6, 0, seller.ids)],
            'route_ids': [(6, 0, (self.mto_route + self.buy_route).ids)],
        })

        so = self.env['sale.order'].with_user(self.user_salesperson).create({
            'partner_id': self.partner_a.id,
            'user_id': self.user_salesperson.id,
        })
        self.env['sale.order.line'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 1,
            'product_uom': product.uom_id.id,
            'price_unit': product.list_price,
            'tax_id': False,
            'order_id': so.id,
        })
        so.action_confirm()

        po = self.env['purchase.order'].search([('partner_id', '=', self.vendor.id)])
        self.assertEqual(po.order_line.price_unit, seller.price)
