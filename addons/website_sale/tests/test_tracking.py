# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon


class TestTracking(WebsiteSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website.google_analytics_key = "G-XXXXXXXXXXX"

    def test_combination_tracking_requires_analytics(self):
        with MockRequest(self.env, website=self.website) as request:
            product = self.product.with_env(request.env)
            combination_info = product._get_combination_info_variant()
            self.assertIn("product_tracking_info", combination_info)
            self.assertEqual(combination_info["currency_name"], self.website.currency_id.name)

            self.website.sudo().google_analytics_key = False
            combination_info = product._get_combination_info_variant()
            self.assertNotIn("product_tracking_info", combination_info)
            self.assertNotIn("currency_name", combination_info)

    def test_cart_response_tracks_quantity_delta(self):
        with MockRequest(self.env, website=self.website, sale_order_id=self.cart.id) as request:
            values = request.cart._cart_add(self.product.id, 2)
            self.assertEqual(len(values["tracking_info"]), 1)
            self.assertEqual(values["tracking_info"][0]["quantity"], 2)
            self.assertEqual(values["tracking_info"][0]["delta_quantity"], 2)

            self.website.sudo().google_analytics_key = False
            values = request.cart._cart_add(self.product.id, 2)
            self.assertEqual(values["tracking_info"], [])

    def test_removed_line_keeps_tracking_payload(self):
        line = self.cart.order_line.filtered(lambda line: line.product_id == self.product)
        quantity = line.product_uom_qty
        with MockRequest(self.env, website=self.website, sale_order_id=self.cart.id):
            values = self.cart._cart_update_line_quantity(line.id, 0)
        self.assertFalse(line.exists())
        self.assertEqual(len(values["tracking_info"]), 1)
        self.assertEqual(values["tracking_info"][0]["quantity"], quantity)
        self.assertEqual(values["tracking_info"][0]["delta_quantity"], -quantity)

    def test_cart_update_without_analytics(self):
        self.website.sudo().google_analytics_key = False
        line = self.cart.order_line.filtered(lambda line: line.product_id == self.product)
        with MockRequest(self.env, website=self.website, sale_order_id=self.cart.id):
            values = self.cart._cart_update_line_quantity(line.id, 2)
        self.assertEqual(values["quantity"], 2)
        self.assertEqual(values["tracking_info"], [])
