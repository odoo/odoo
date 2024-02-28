# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockReorderFromPortal(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['website'].get_current_website().enabled_portal_reorder_button = True

        cls.available_product = cls.env['product.product'].create({
            'name': 'available_product',
            'type': 'product',
            'allow_out_of_stock_order': False,
            'sale_ok': True,
            'website_published': True,
        })
        cls.unavailable_product = cls.env['product.product'].create({
            'name': 'unavailable_product',
            'type': 'product',
            'allow_out_of_stock_order': False,
            'sale_ok': True,
            'website_published': True,
        })
        cls.partially_available_product = cls.env['product.product'].create({
            'name': 'partially_available_product',
            'type': 'product',
            'allow_out_of_stock_order': False,
            'sale_ok': True,
            'website_published': True,
        })
        user_admin = cls.env.ref('base.user_admin')
        order = cls.env['sale.order'].create({
            'partner_id': user_admin.partner_id.id,
            'state': 'sale',
            'order_line': [
                (0, 0, {
                    'product_id': cls.available_product.id,
                    'product_uom_qty': 1,
                }),
                (0, 0, {
                    'product_id': cls.unavailable_product.id,
                    'product_uom_qty': 1,
                }),
                (0, 0, {
                    'product_id': cls.partially_available_product.id,
                    'product_uom_qty': 2,
                })
            ]
        })
        order.message_subscribe(user_admin.partner_id.ids)

        cls.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': cls.available_product.id,
            'inventory_quantity': 10.0,
            'location_id': 8,
        }).action_apply_inventory()
        cls.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': cls.partially_available_product.id,
            'inventory_quantity': 1.0,
            'location_id': 8,
        }).action_apply_inventory()

    def test_website_sale_stock_reorder_from_portal_stock(self):
        self.start_tour("/", 'website_sale_stock_reorder_from_portal', login='admin')
