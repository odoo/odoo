# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_mercado_pago import const
from odoo.addons.payment_mercado_pago.tests.common import MercadoPagoCommon


@tagged("post_install", "-at_install")
class TestMercadoPagoOnboarding(MercadoPagoCommon, PaymentHttpCommon):
    def test_onboarding_authorization_error_renders_template(self):
        self.authenticate(self.admin_user.login, self.admin_user.password)
        url = self._build_url(const.OAUTH_RETURN_ROUTE)
        params = {
            "provider_id": self.provider.id,
            "authorization_code": "dummy_auth_code",
            "csrf_token": self.csrf_token(),
        }
        with (
            patch.object(
                self.env.registry["payment.provider"],
                "_send_api_request",
                side_effect=ValidationError("Invalid Mercado Pago credentials"),
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
        url = self._build_url(const.OAUTH_RETURN_ROUTE)
        params = {
            "provider_id": self.provider.id,
            "authorization_code": "dummy_auth_code",
            "csrf_token": self.csrf_token(),
        }
        mock_response = {
            "expires_in": 3600,
            "access_token": "dummy_access_token",
            "refresh_token": "dummy_refresh_token",
            "public_key": "dummy_public_key",
        }
        with patch.object(
            self.env.registry["payment.provider"], "_send_api_request", return_value=mock_response
        ):
            response = self._make_http_get_request(url, params=params)

        self.assertIn(response.history[0].status_code, (302, 303))

        redirect_url = response.history[0].headers.get("Location", "")
        self.assertIn(f"/{self.provider.id}", redirect_url)
