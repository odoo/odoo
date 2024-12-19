# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests import tagged

from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockProductTemplate(WebsiteSaleStockCommon):

    def test_website_sale_stock_get_additional_configurator_data(self):
        product = self._create_product(is_storable=True, allow_out_of_stock_order=False)
        self.env['stock.quant'].create({
            'product_id': product.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'quantity': 10,
        })

        env = self.env(user=self.public_user)
        with MockRequest(env, website=self.website.with_env(env)):
            configurator_data = self.env['product.template']._get_additional_configurator_data(
                product_or_template=product,
                date=datetime(2000, 1, 1),
                currency=self.currency,
                pricelist=self.pricelist,
            )

        self.assertEqual(configurator_data['free_qty'], 10)
