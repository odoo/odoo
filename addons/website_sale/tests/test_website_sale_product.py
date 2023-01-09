# coding: utf-8
from odoo.tests import tagged
from odoo.addons.website.tools import MockRequest
from odoo.addons.sale.tests.test_sale_product_attribute_value_config import TestSaleProductAttributeValueCommon

@tagged('post_install', '-at_install')
class WebsiteSaleProductTests(TestSaleProductAttributeValueCommon):

    def setUp(self):
        super().setUp()
        self.website = self.env.ref('website.default_website')

    def test_website_sale_contextual_price(self):
        contextual_price = self.computer._get_contextual_price()
        self.assertEqual(0.0, contextual_price, "With no pricelist context, the contextual price should be 0.")

        current_website = self.env['website'].get_current_website()
        pricelist = current_website.get_current_pricelist()

        # make sure the pricelist has a 10% discount
        self.env['product.pricelist.item'].create({
            'price_discount': 10,
            'compute_price': 'formula',
            'pricelist_id': pricelist.id,
        })
        discount_rate = 0.9
        currency_ratio = 2
        pricelist.currency_id = self._setup_currency(currency_ratio)
        with MockRequest(self.env, website=self.website):
            contextual_price = self.computer._get_contextual_price()
        self.assertEqual(
            2000.0 * currency_ratio * discount_rate, contextual_price,
            "With a website pricelist context, the contextual price should be the one defined for the website's pricelist."
        )
