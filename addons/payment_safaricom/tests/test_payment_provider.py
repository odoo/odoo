# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment_safaricom.tests.common import SafaricomCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(SafaricomCommon):
    def test_incompatible_with_unsupported_currencies(self):
        """Test that Safaricom providers are filtered out when the currency is not supported."""
        available_providers = self.env["payment.provider"]._find_available_providers(
            self.company_id, self.partner.id, self.amount, currency_id=self.env.ref("base.AFN").id
        )
        self.assertNotIn(self.provider, available_providers)

    def test_till_number_required_for_buygoodsonline(self):
        """Test that setting the BuyGoods transaction type without a till number raises a
        ValidationError."""
        with self.assertRaises(ValidationError):
            self.provider.write({
                "safaricom_transaction_type": "CustomerBuyGoodsOnline",
                "safaricom_till_number": False,
            })

    def test_valid_access_token_is_not_refetched(self):
        """Test that a non-expired access token is returned from cache without an API call."""
        self.provider.write({
            "safaricom_access_token": "cached_token",
            "safaricom_access_token_expiry": fields.Datetime.now() + timedelta(seconds=3600),
        })
        with self._mock_send_api_request({}) as mock_request:
            token = self.provider._safaricom_fetch_access_token()
        self.assertEqual(token, "cached_token")
        mock_request.assert_not_called()

    def test_nearly_expired_access_token_is_refetched(self):
        """Test that a token within the refresh margin of its expiry triggers a new OAuth
        request."""
        self.provider.write({
            "safaricom_access_token": "old_token",
            "safaricom_access_token_expiry": fields.Datetime.now() + timedelta(seconds=30),
        })
        with self._mock_send_api_request({"access_token": "new_token", "expires_in": "3600"}):
            token = self.provider._safaricom_fetch_access_token()
        self.assertEqual(token, "new_token")

    @mute_logger("odoo.addons.payment_safaricom.models.payment_provider")
    def test_invalid_access_token_response_raises_validation_error(self):
        """Test that a malformed OAuth response raises a ValidationError instead of crashing."""
        with (
            self._mock_send_api_request({"access_token": "token", "expires_in": "soon"}),
            self.assertRaises(ValidationError),
        ):
            self.provider._safaricom_fetch_access_token()

    def test_safaricom_get_password(self):
        """Test that the M-PESA password is correctly computed as a base64-encoded string."""
        self.assertEqual(
            self.provider._safaricom_get_password(self.timestamp),
            "MTc0Mzc5YmZiMjc5ZjlhYTliZGJjZjE1OGU5N2RkNzFhNDY3Y2QyZTBjODkzMDU5YjEwZjc4ZTZiNzJh"
            "ZGExZWQyYzkxOTIwMjMxMTE4MTIwMDAw",
        )
