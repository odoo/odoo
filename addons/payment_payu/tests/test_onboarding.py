# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from urllib.parse import urlsplit

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_payu import const
from odoo.addons.payment_payu.tests.common import PayuCommon


@tagged("post_install", "-at_install")
class TestOnboarding(PayuCommon, PaymentHttpCommon):
    def test_failed_authorization_renders_error_page(self):
        self.authenticate(self.admin_user.login, self.admin_user.password)
        url = self._build_url(const.OAUTH_RETURN_ROUTE)
        params = {
            "provider_id": self.provider.id,
            "auth_code": "dummy_auth_code",
            "csrf_token": self.csrf_token(),
        }
        with (
            patch.object(
                self.env.registry["payment.provider"],
                "_send_api_request",
                side_effect=ValidationError("error"),
            ),
            patch.object(
                self.env.registry["ir.ui.view"], "_render_template", return_value="<html/>"
            ) as mock_render,
        ):
            self._make_http_get_request(url, params=params)

        self.assertEqual(mock_render.call_args.args[0], "payment.authorization_error")

    def test_successful_authorization_redirects_to_provider_form(self):
        self.authenticate(self.admin_user.login, self.admin_user.password)
        url = self._build_url(const.OAUTH_RETURN_ROUTE)
        params = {
            "provider_id": self.provider.id,
            "auth_code": "dummy_auth_code",
            "merchant_id": "dummy_merchant_id",
            "csrf_token": self.csrf_token(),
        }
        mock_token_response = {"access_token": "dummy_access_token"}
        mock_credentials_response = {
            "data": {"credentials": {"prod_key": "dummy_prod_key", "prod_salt": "dummy_prod_salt"}}
        }
        with patch.object(
            self.env.registry["payment.provider"],
            "_send_api_request",
            side_effect=[mock_token_response, mock_credentials_response],
        ):
            response = self._make_http_get_request(url, params=params)

        action = self.env.ref("payment.action_payment_provider")
        location = response.history[0].headers["Location"]
        self.assertEqual(urlsplit(location).path, f"/odoo/action-{action.id}/{self.provider.id}")
