# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged

from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged("post_install", "-at_install")
class TestWebsiteSaleStockShopFilters(HttpCase, WebsiteSaleStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref("website_sale.out_of_stock_ribbon").assign = "out_of_stock"
        cls.in_stock_product = cls._create_product(name="Stockfilter In Stock")
        cls._add_product_qty_to_wh(cls.in_stock_product.id, 5, cls.warehouse.lot_stock_id.id)
        cls.oos_allowed_product = cls._create_product(
            name="Stockfilter Oos Allowed", allow_out_of_stock_order=True
        )

    def _shop_html(self, **params):
        response = self.url_open("/shop", params={"search": "Stockfilter", **params})
        self.assertEqual(response.status_code, 200)
        return response.text

    def test_in_stock_filter_hidden_without_sold_out_product(self):
        html = self._shop_html()
        self.assertNotIn("in_stock=1", html)

    def test_in_stock_filter_excludes_sold_out_products(self):
        self._create_product(name="Stockfilter Sold Out")

        html = self._shop_html()
        self.assertIn("in_stock=1", html)
        self.assertIn("Stockfilter Sold Out", html)

        html = self._shop_html(in_stock=1)
        self.assertNotIn("Stockfilter Sold Out", html)
        self.assertIn("Stockfilter In Stock", html)
        self.assertIn("Stockfilter Oos Allowed", html)
