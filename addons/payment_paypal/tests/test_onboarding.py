# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_paypal import const
from odoo.addons.payment_paypal.controllers.onboarding import PaypalOnboardingController
from odoo.addons.payment_paypal.tests.common import PaypalCommon


@tagged("post_install", "-at_install")
class PaypalOnboardingTest(PaypalCommon, PaymentHttpCommon):
    def test_publishing_without_credentials_is_blocked(self):
        self.paypal.paypal_account_id = False
        with self.assertRaises(ValidationError):
            self.paypal.is_published = True

    def test_onboarding_status_enables_tokenization_when_vaulting_is_active(self):
        self.paypal.allow_tokenization = False
        with patch.object(
            self.env.registry["payment.provider"],
            "_send_api_request",
            return_value={
                "capabilities": [{"name": const.VAULTING_CAPABILITY, "status": "ACTIVE"}]
            },
        ):
            self.paypal._paypal_update_onboarding_status()
        self.assertTrue(self.paypal.allow_tokenization)

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_merchant_webhook_confirms_seller_email(self):
        self.paypal.paypal_account_id = self.merchant_notification["resource"]["merchant_id"]
        url = self._build_url(const.WEBHOOK_ROUTE)
        with patch(
            "odoo.addons.payment_paypal.controllers.main.PaypalController"
            "._verify_notification_origin"
        ):
            self._make_json_request(url, data=self.merchant_notification)
        self.assertTrue(self.paypal.paypal_email_confirmed)

    @mute_logger("odoo.addons.payment_paypal.controllers.main", "odoo.http")
    def test_merchant_webhook_with_unverified_origin_does_not_confirm_seller_email(self):
        self.paypal.paypal_account_id = self.merchant_notification["resource"]["merchant_id"]
        url = self._build_url(const.WEBHOOK_ROUTE)
        with patch.object(
            self.env.registry["payment.provider"],
            "_send_api_request",
            return_value={"verification_status": "FAILURE"},
        ):
            self._make_json_request(url, data=self.merchant_notification)
        self.assertFalse(self.paypal.paypal_email_confirmed)

    @mute_logger("odoo.addons.payment_paypal.controllers.onboarding")
    def test_finalizing_onboarding_saves_merchant_credentials(self):
        self.paypal.write({
            "paypal_client_id": False,
            "paypal_client_secret": False,
            "paypal_account_id": False,
        })
        # A single mocked response serves the token, credentials, status and webhook requests.
        with (
            MockRequest(self.env),
            patch.object(
                self.env.registry["payment.provider"],
                "_send_api_request",
                return_value={
                    "access_token": "onboarding_token",
                    "client_id": "merchant_client_id",
                    "client_secret": "merchant_client_secret",
                    "payer_id": "MERCHANT123",
                },
            ),
        ):
            PaypalOnboardingController().finalize_onboarding(
                auth_code="dummy_auth_code", shared_id="dummy_shared_id", provider_id=self.paypal.id
            )
        self.assertRecordValues(
            self.paypal,
            [
                {
                    "paypal_client_id": "merchant_client_id",
                    "paypal_client_secret": "merchant_client_secret",
                    "paypal_account_id": "MERCHANT123",
                }
            ],
        )
