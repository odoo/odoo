# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.website_sale.tests.common_checkout import CheckoutCommon
from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockCheckout(CheckoutCommon, WebsiteSaleStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product.write({'allow_out_of_stock_order': False, 'is_storable': True})
        cls.stock_location = cls.warehouse.lot_stock_id

    def test_checkout_impossible_if_a_product_is_sold_out(self):
        self.authenticate_with_cart(None, None)
        self.partner.write(self.default_address_values)
        self._add_product_qty_to_wh(self.product.id, 0, self.stock_location.id)

        response = self.url_open('/shop/checkout')

        self.assertURLEqual(response.url, '/shop/cart')  # Redirected back to the cart

    def test_checkout_possible_if_at_least_one_warehouse_can_fulfill_the_order(self):
        self.authenticate_with_cart(None, None)
        self.partner.write(self.default_address_values)
        wh2 = self._create_warehouse()
        self._add_product_qty_to_wh(self.product.id, 0, self.stock_location.id)
        self._add_product_qty_to_wh(self.product.id, 10, wh2.lot_stock_id.id)

        response = self.url_open('/shop/checkout')

        self.assertEqual(response.status_code, 200)
        self.assertURLEqual(response.url, '/shop/checkout')  # Success without redirection
