# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged
from odoo.addons.sale.tests.test_sale_product_attribute_value_config import TestSaleProductAttributeValueSetup


@tagged('post_install', '-at_install')
class TestUi(TestSaleProductAttributeValueSetup, HttpCase):

    post_install = True
    at_install = False

    def setUp(self):
        super(TestUi, self).setUp()

        # set currency to not rely on demo data and avoid possible race condition
        self.currency_ratio = 1.0
        pricelist = self.env.ref('product.list0')
        pricelist.currency_id = self._setup_currency(self.currency_ratio)

    def test_01_admin_shop_sale_coupon_tour(self):
        # pre enable "Show # found" option to avoid race condition...
        self.env.ref("website_sale.search_count_box").write({"active": True})
        self.start_tour("/", 'shop_sale_coupon', login="admin")
