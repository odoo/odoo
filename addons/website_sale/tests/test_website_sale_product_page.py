# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged

from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleProductPage(HttpCase, ProductVariantsCommon, WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_template_sofa.website_published = True

    def test_toggle_contact_us_button_visibility(self):
        """Check that the "Contact Us" button:
          - is shown for zero-priced products
          - is hidden for other products
          - is not displayed at the same time as the "Add to Cart" button
        """
        self.website.prevent_zero_price_sale = True

        self.product_template_sofa.list_price = 0
        red_sofa, blue_sofa = self.product_template_sofa.product_variant_ids[:2]
        blue_sofa.product_template_attribute_value_ids.price_extra = 20

        self.start_tour(red_sofa.website_url, 'website_sale_contact_us_button')
