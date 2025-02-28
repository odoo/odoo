# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleCheckoutSteps(WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.generic_extra_step = cls.env['website.checkout.step'].create({
            'name': 'Extra Info',
            'step_href': '/shop/extra_info',
        })

    def test_create_specific_extra_step(self):
        specific_extra_step = self.website._get_website_specific_extra_step()
        self.assertNotEqual(specific_extra_step, self.generic_extra_step)
        self.assertEqual(specific_extra_step.website_id, self.website)

    def test_get_existing_specific_extra_step(self):
        already_existing_step = self.env['website.checkout.step'].create({
            'name': 'Extra Info',
            'step_href': '/shop/extra_info',
            'website_id': self.website.id,
        })
        specific_extra_step = self.website._get_website_specific_extra_step()
        self.assertEqual(specific_extra_step, already_existing_step)

    def test_extra_step_activation_from_settings(self):
        website = self.website.with_context(website_id=self.website.id)
        extra_step = website._get_website_specific_extra_step()
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
