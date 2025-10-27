# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.http import root
from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockReorderFromPortal(HttpCaseWithUserPortal, WebsiteSaleStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env['website'].get_current_website()
        cls.website.enabled_portal_reorder_button = True

        cls.available_product = cls._create_product(name='available_product')
        cls.unavailable_product = cls._create_product(name='unavailable_product')
        cls.partially_available_product = cls._create_product(
            name='partially_available_product'
        )
        cls.order = cls.env['sale.order'].create({
            'partner_id': cls.partner_portal.id,
            'state': 'sale',
            'order_line': [
                Command.create({
                    'product_id': cls.available_product.id,
                    'product_uom_qty': 1,
                }),
                Command.create({
                    'product_id': cls.unavailable_product.id,
                    'product_uom_qty': 1,
                }),
                Command.create({
                    'product_id': cls.partially_available_product.id,
                    'product_uom_qty': 2,
                })
            ]
        })
        cls.order.message_subscribe(cls.partner_portal.ids)

        cls._add_product_qty_to_wh(cls.available_product.id, 10, 8)
        cls._add_product_qty_to_wh(cls.partially_available_product.id, 1.0, 8)

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
        res = self.make_jsonrpc_request('/my/orders/reorder_modal_content', {
            'order_id': self.order.id,
            'access_token': self.order._portal_ensure_token(),
        })
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
