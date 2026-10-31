# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_razorpay.controllers.onboarding import RazorpayController
from odoo.addons.payment_razorpay.tests.common import RazorpayCommon


@tagged("post_install", "-at_install")
class TestRazorpayOnboarding(RazorpayCommon, PaymentHttpCommon):
    def test_onboarding_authorization_error_renders_template(self):
        self.authenticate(self.admin_user.login, self.admin_user.password)
        url = self._build_url(RazorpayController.OAUTH_RETURN_URL)
        params = {
            "provider_id": self.provider.id,
            "authorization_code": "dummy_auth_code",
            "csrf_token": self.csrf_token(),
        }
        with (
            patch.object(
                self.env.registry["payment.provider"],
                "_send_api_request",
                side_effect=ValidationError("Invalid Razorpay credentials"),
            ),
            patch.object(
                self.env.registry["ir.ui.view"], "_render_template", return_value="<html/>"
            ) as mock_render,
        ):
            self._make_http_get_request(url, params=params)

        mock_render.assert_called()
        self.assertEqual(mock_render.call_args[0][0], "payment.authorization_error")

    def test_onboarding_authorization_success_redirects(self):
        """Test that successful authorization redirects to the provider action form."""
        self.authenticate(self.admin_user.login, self.admin_user.password)
        url = self._build_url(RazorpayController.OAUTH_RETURN_URL)
        params = {
            "provider_id": self.provider.id,
            "authorization_code": "dummy_auth_code",
            "csrf_token": self.csrf_token(),
        }
        mock_response = {
            "expires_in": 3600,
            "razorpay_account_id": "dummy_acc_id",
            "public_token": "dummy_pub_token",
            "refresh_token": "dummy_ref_token",
            "access_token": "dummy_acc_token",
        }
        with patch.object(
            self.env.registry["payment.provider"], "_send_api_request", return_value=mock_response
        ):
            response = self._make_http_get_request(url, params=params)

        self.assertIn(response.history[0].status_code, (302, 303))

        redirect_url = response.history[0].headers.get("Location", "")
        self.assertIn(f"/{self.provider.id}", redirect_url)
