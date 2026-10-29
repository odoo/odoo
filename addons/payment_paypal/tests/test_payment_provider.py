# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_paypal.tests.common import PaypalCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(PaypalCommon):
    def test_access_token_is_fetched_when_expiry_is_unset(self):
        self.paypal.paypal_access_token_expiry = False
        self.paypal.paypal_access_token = "old_token"
        with self._mock_send_api_request(
            return_value={"access_token": "new_token", "expires_in": 3600}
        ):
            access_token = self.paypal._paypal_fetch_access_token()
        self.assertEqual(access_token, "new_token")
