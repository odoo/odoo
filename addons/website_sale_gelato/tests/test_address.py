# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from odoo.addons.sale_gelato.tests.common import GelatoCommon
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon


@tagged("post_install", "-at_install")
class TestCheckoutAddress(GelatoCommon, WebsiteSaleCommon):
    def test_require_shortening_too_long_addresses(self):
        """Test that if the saved partner address is too long, they are redirected to edit form
        during checkout process.
        """
        user = self._create_new_portal_user()

        user.partner_id = self.partner_street_too_long.id
        website = self.website.with_user(user)
        self.gelato_order.write({
            "partner_id": self.partner_street_too_long,
            "website_id": website.id,
        })
        with MockRequest(website.env, website=website, sale_order_id=self.gelato_order.id):
            redirect = self.env["website.checkout.step"]._check_shop_address_completion(
                self.gelato_order
            )
            self.assertEqual(
                redirect,
                f"/shop/address?partner_id={self.partner_street_too_long.id}&address_type=delivery",
            )

    def test_do_not_allow_express_checkout_with_invalid_gelato_address(self):
        self.gelato_order.partner_id = self.partner_missing_street
        self.assertFalse(self.gelato_order._allow_express_checkout())

    def test_allow_express_checkout_with_valid_gelato_address(self):
        self.gelato_order.partner_id = self.partner_missing_street
        self.gelato_order.partner_shipping_id.street = "Valid Street"
        self.assertTrue(self.gelato_order._allow_express_checkout())
