# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import HttpCase

from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockProductProduct(HttpCase, WebsiteSaleStockCommon):

    def test_get_max_quantity_with_max(self):
        product = self._create_product(is_storable=True, allow_out_of_stock_order=False)
        self.env['stock.quant'].create({
            'product_id': product.id, 'location_id': self.warehouse.lot_stock_id.id, 'quantity': 5
        })
        self.cart.order_line = [Command.create({'product_id': product.id, 'product_uom_qty': 3})]

        with MockRequest(self.env, website=self.website, sale_order_id=self.cart.id):
            self.assertEqual(product._get_max_quantity(self.website), 2)

    def test_get_max_quantity_without_max(self):
        product = self._create_product(is_storable=True, allow_out_of_stock_order=True)

        self.assertIsNone(product._get_max_quantity(self.website))
