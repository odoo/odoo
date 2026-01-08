# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from odoo.addons.sale_gelato.tests.common import GelatoCommon
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon
from odoo.addons.website_sale_gelato.controllers.main import WebsiteSale


@tagged('post_install', '-at_install')
class TestCheckoutAddress(GelatoCommon, WebsiteSaleCommon):
    def setUp(self):
        super().setUp()
        self.WebsiteSaleController = WebsiteSale()

    def test_require_shortening_too_long_addresses(self):
        """Test that if the saved partner address is too long, they are redirected to edit form
        during checkout process.
        """
        user = self._create_new_portal_user()

        user.partner_id = self.partner_street_too_long.id
        website = self.website.with_user(user)
        self.gelato_order.write({
            'partner_id': self.partner_street_too_long,
            'website_id': website.id,
        })
        with MockRequest(website.env, website=website, sale_order_id=self.gelato_order.id):
            redirect = self.WebsiteSaleController._check_addresses(self.gelato_order)
            self.assertIsNotNone(redirect)
            self.assertEqual(
                redirect.location,
                f'/shop/address?partner_id={self.partner_street_too_long.id}&address_type=delivery',
            )
