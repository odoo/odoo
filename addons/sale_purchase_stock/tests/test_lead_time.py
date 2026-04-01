# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import Command, fields
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
            'group_ids': cls.env.ref('sales_team.group_sale_salesman'),
        })
        cls.product = cls.env['product.product'].create({
            'name': 'corpse starch',
            'is_storable': True,
            'seller_ids': [Command.create({
                'partner_id': cls.vendor.id,
                'min_qty': 1,
                'price': 10,
                'date_start': fields.Date.today() - timedelta(days=1),
            })],
            'route_ids': [Command.set((cls.mto_route + cls.buy_route).ids)],
        })

    def test_supplier_lead_time(self):
        """ Basic stock configuration and a supplier with a minimum qty and a lead time """

        so = self.env['sale.order'].with_user(self.user_salesperson).create({
            'partner_id': self.partner_a.id,
            'user_id': self.user_salesperson.id,
        })
        self.env['sale.order.line'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'price_unit': self.product.list_price,
            'tax_ids': False,
            'order_id': so.id,
        })
        so.action_confirm()

        po = self.env['purchase.order'].search([('partner_id', '=', self.vendor.id)])
        self.assertEqual(po.order_line.price_unit, self.product.seller_ids.price)

    def test_merge_procurement(self):
        """create 2 sale order for the same supplier with grouping option and check that only one PO is created"""

        self.vendor.group_rfq = 'day'

        sale_order = self.env["sale.order"].create([{
            "partner_id": self.partner_a.id,
            "order_line": [Command.create(
                {
                    "name": self.product.name,
                    "product_id": self.product.id,
                    "product_uom_qty": 2,
                    "price_unit": self.product.list_price,
                    "tax_ids": False,
                })],
        }])
        sale_order.action_confirm()

        pol = self.env['purchase.order.line'].search([('product_id', '=', self.product.id)])
        self.assertRecordValues(pol, [{'product_qty': 2}])
        # create another SO, it should increate the existing PO line
        so = self.env["sale.order"].create({
            "partner_id": self.partner_a.id,
            "order_line": [Command.create(
                {
                    "name": self.product.name,
                    "product_id": self.product.id,
                    "product_uom_qty": 1,
                    "price_unit": self.product.list_price,
                    "tax_ids": False,
                })],
        })
        so.action_confirm()
        self.assertEqual(pol.product_qty, 3)

        # Edit a SOL, it should update the PO line
        sale_order.order_line.product_uom_qty += 1
        self.assertEqual(pol.product_qty, 4)

    def test_dynamic_lead_time_delay(self):
        self.env.company.horizon_days = 0
        self.product_a.write({
            'seller_ids': [(0, 0, {
                'partner_id': self.partner_a.id,
                'price': 800.0,
                'delay': 7,
                'product_id': self.product_a.id,
            })],
        })
        product = self.product_a
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_b.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 10,
            })],
            'commitment_date': fields.Date.today() + timedelta(days=10),
        })
        sale_order.action_confirm()
        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'product_id': product.id,
            'route_id': self.env.ref('purchase_stock.route_warehouse0_buy').id,
        })
        self.assertEqual(orderpoint.qty_to_order, 0)
        product.seller_ids[0].delay = 17
        self.assertEqual(orderpoint.qty_to_order, 10)
