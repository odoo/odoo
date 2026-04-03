# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged("post_install", "-at_install")
class TestWebsiteSaleStockJsonLd(WebsiteSaleStockCommon):
    def test_product_to_structured_data_with_stock(self):
        product = self._create_product(is_storable=True, allow_out_of_stock_order=False)
        self._add_product_qty_to_wh(product.id, 3, self.warehouse.lot_stock_id.id)

        with self.mock_request():
            json_ld = product._to_structured_data(self.website)
            markup_data = json_ld._render()

        self.assertEqual(markup_data["@type"], "Product")
        self.assertEqual(markup_data["offers"]["availability"], "https://schema.org/InStock")

    def test_product_to_structured_data_out_of_stock(self):
        product = self._create_product(is_storable=True, allow_out_of_stock_order=False)

        with self.mock_request():
            json_ld = product._to_structured_data(self.website)
            markup_data = json_ld._render()

        self.assertEqual(markup_data["@type"], "Product")
        self.assertEqual(markup_data["offers"]["availability"], "https://schema.org/OutOfStock")
