# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from unittest.mock import patch

import requests

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_mercado_pago import const
from odoo.addons.payment_mercado_pago.tests.common import MercadoPagoCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(MercadoPagoCommon, PaymentHttpCommon):
    @mute_logger("odoo.addons.payment_mercado_pago.controllers.main")
    def test_redirect_notification_triggers_processing(self):
        """Test that receiving a redirect notification triggers the processing of the notification
        data."""
        self._create_transaction(flow="redirect")
        url = self._build_url(const.PAYMENT_RETURN_ROUTE)
        with (
            patch(
                "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
                return_value=self.verification_data,
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_http_get_request(url, params=self.redirect_payment_data)
        self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_mercado_pago.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        """Test that receiving a valid webhook notification triggers the processing of the
        payment data."""
        tx = self._create_transaction(flow="redirect")
        url = self._build_url(f"{const.WEBHOOK_ROUTE}/{tx.reference}")
        with (
            patch(
                "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
                return_value=self.verification_data,
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_json_request(url, data=self.webhook_payment_data)
        self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment.models.payment_provider")
    def test_proxy_rejection_is_shown_on_the_authorization_error_page(self):
        self.provider.action_reset_credentials()
        self.provider.is_live = True
        proxy_response = requests.Response()
        proxy_response.status_code = 403
        proxy_response._content = json.dumps({"message": "Account mismatch"}).encode()
        self.authenticate(self.admin_user.login, self.admin_user.password)
        params = {
            "provider_id": self.provider.id,
            "authorization_code": "dummy_auth_code",
            "csrf_token": self.csrf_token(),
        }
        with (
            patch(
                "odoo.addons.payment.models.payment_provider.requests.request",
                return_value=proxy_response,
            ) as request_mock,
            patch.object(
                self.env.registry["ir.ui.view"], "_render_template", return_value="<html/>"
            ) as render_mock,
        ):
            self._make_http_get_request(self._build_url(const.OAUTH_RETURN_ROUTE), params=params)
        self.assertIs(request_mock.call_args.kwargs["json"]["is_live"], True)
        template, values = render_mock.call_args.args[:2]
        self.assertEqual(template, "payment_mercado_pago.authorization_error")
        self.assertIn("Account mismatch", values["error_message"])
