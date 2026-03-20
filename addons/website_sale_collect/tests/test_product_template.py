# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests import tagged

from odoo.addons.website_sale.tests.common import MockRequest
from odoo.addons.website_sale_collect.tests.common import ClickAndCollectCommon


@tagged('post_install', '-at_install')
class TestProductTemplate(ClickAndCollectCommon):

    def test_out_of_stock_product_available_when_allow_continue_selling(self):
        product = self._create_product(allow_out_of_stock_order=True)
        self.free_delivery.is_published = True
        with MockRequest(self.env, website=self.website, sale_order_id=self.cart.id):
            comb_info = self.env['product.template']._get_additionnal_combination_info(
                product,
                quantity=1,
                date=datetime(2000, 1, 1),
                uom=self.uom_unit,
                website=self.website,
            )
        self.assertTrue(comb_info['delivery_stock_data']['in_stock'])
        self.assertTrue(comb_info['in_store_stock_data']['in_stock'])
