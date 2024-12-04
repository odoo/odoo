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

    def test_extra_step_activation_from_settings(self):
        website = self.website.with_context(website_id=self.website.id)
        extra_step = website._get_checkout_step('/shop/extra_info')
        my_settings = self.env["res.config.settings"].create({})

        # Enable 'extra_step' in settings
        my_settings.enabled_extra_checkout_step = True
        my_settings.execute()
        # Take the newly created view once setting is activated
        extra_step_view = website.viewref('website_sale.extra_info')
        self.assertEqual(extra_step.is_published, True)
        self.assertEqual(extra_step_view.active, True)

        # Disable 'extra_step' in settings
        my_settings.enabled_extra_checkout_step = False
        my_settings.execute()
        self.assertEqual(extra_step.is_published, False)
        self.assertEqual(extra_step_view.active, False)
