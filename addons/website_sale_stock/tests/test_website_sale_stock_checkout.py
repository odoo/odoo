# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged

from odoo.addons.website_sale.controllers.main import WebsiteSale as CheckoutController
from odoo.addons.website_sale.tests.common import MockRequest
from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockCheckout(WebsiteSaleStockCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product.write({'allow_out_of_stock_order': False, 'is_storable': True})
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.partner.write(cls.dummy_partner_address_values)
        cls.CheckoutController = CheckoutController()

    def test_checkout_impossible_if_a_product_is_sold_out(self):
        self._add_product_qty_to_wh(self.product.id, 0, self.stock_location.id)

        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env, website=website, path='/shop/checkout', sale_order_id=self.cart.id
        ):
            response = self.CheckoutController.shop_checkout()

        self.assertEqual(response.status_code, 303, 'SEE OTHER')
        self.assertURLEqual(response.location, '/shop/cart')  # Redirected back to the cart

    def test_checkout_possible_if_at_least_one_warehouse_can_fulfill_the_order(self):
        wh2 = self._create_warehouse()
        self._add_product_qty_to_wh(self.product.id, 0, self.stock_location.id)
        self._add_product_qty_to_wh(self.product.id, 10, wh2.lot_stock_id.id)

        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env, website=website, path='/shop/checkout', sale_order_id=self.cart.id
        ):
            response = self.CheckoutController.shop_checkout()

        self.assertEqual(response.status_code, 200)  # Success without redirection
