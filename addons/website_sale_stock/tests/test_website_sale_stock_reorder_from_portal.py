# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from uuid import uuid4

from odoo import Command
from odoo.http import root
from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserPortal


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockReorderFromPortal(HttpCaseWithUserPortal):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env['website'].get_current_website()
        cls.website.enabled_portal_reorder_button = True

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
        cls.order = cls.env['sale.order'].create({
            'partner_id': cls.partner_portal.id,
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
        cls.order.message_subscribe(cls.partner_portal.ids)

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
        self.start_tour(
            "/", 'website_sale_stock_reorder_from_portal', login=self.user_portal.login,
        )

    def test_website_sale_stock_reorder_cart_change(self):
        """Ensure cart remains unchanged when attempting a reorder."""
        cart = self.env['sale.order'].create({
            'partner_id': self.partner_portal.id,
            'website_id': self.website.id,
            'order_line': [Command.create({
                'product_id': self.unavailable_product.id,
                'product_uom_qty': 5.0,
            })],
        })
        session = self.authenticate(self.user_portal.login, self.user_portal.login)
        session['sale_order_id'] = cart.id
        root.session_store.save(session)
        rpc_request = {'jsonrpc': '2.0', 'method': 'call', 'id': str(uuid4()), 'params': {
            'order_id': self.order.id,
            'access_token': self.order._portal_ensure_token(),
        }}
        res = self.url_open(
            '/my/orders/reorder_modal_content',
            data=json.dumps(rpc_request).encode(),
            headers={'Content-Type': 'application/json'},
            timeout=None,
        ).json().get('result', {})
        combination_info = next(
            product_info['combinationInfo'] for product_info in res['products']
            if product_info['combinationInfo']['product_id'] == self.unavailable_product.id
        )
        self.assertEqual(
            combination_info['cart_qty'], 5.0,
            "Combination info retrieved via RPC should be correct.",
        )
        self.assertEqual(
            cart.partner_id, self.partner_portal,
            "Customer should remain unchanged on cart.",
        )
