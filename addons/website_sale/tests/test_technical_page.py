from odoo.tests import tagged

from odoo.addons.website.tests.test_website_technical_page import TestWebsiteTechnicalPage


@tagged("post_install", "-at_install")
class TestWebsiteSaleTechnicalPage(TestWebsiteTechnicalPage):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expected_routes = [
            '/shop',
            '/shop/confirmation',
            '/shop/payment',
            '/shop/checkout',
        ]

    def _set_extra_info_active(self, active):
        """Helper to activate or deactivate the 'extra_info' view."""
        website = self.env['website'].get_current_website()
        view = website.viewref('website_sale.extra_info')
        view.active = active

    def test_routes_with_extra_info_toggle(self):
        for active in [True, False]:
            with self.subTest(active=active):
                self._set_extra_info_active(active)
                if active:
                    self.expected_routes.append('/shop/extra_info')
                self._validate_routes(self.expected_routes)
