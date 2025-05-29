# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleCheckoutSteps(WebsiteSaleCommon):

    def test_get_existing_specific_extra_step(self):
        specific_extra_step = self.website._get_checkout_step('/shop/extra_info')
        generic_extra_step = self.env.ref('website_sale.checkout_step_extra')
        self.assertNotEqual(specific_extra_step, generic_extra_step)
        self.assertEqual(specific_extra_step.website_id, self.website)
