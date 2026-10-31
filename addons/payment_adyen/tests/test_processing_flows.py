# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo import release
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_adyen.controllers.main import AdyenController
from odoo.addons.payment_adyen.tests.common import AdyenCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(AdyenCommon, PaymentHttpCommon):
    @mute_logger("odoo.addons.payment_adyen.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        self._create_transaction("direct")
        url = self._build_url(AdyenController._webhook_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch("odoo.addons.payment_adyen.controllers.main.AdyenController._compute_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_json_request(url, data=self.webhook_notification_batch_data)
            self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_adyen.controllers.main")
    def test_webhook_notification_triggers_signature_check(self):
        self._create_transaction("direct")
        url = self._build_url(AdyenController._webhook_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock,
            patch("odoo.addons.payment_adyen.controllers.main.AdyenController._compute_signature"),
        ):
            self._make_json_request(url, data=self.webhook_notification_batch_data)
            self.assertEqual(
                signature_check_mock.call_args[0][0], self.webhook_notification_payload_signature
            )

    def test_compute_signature_returns_correct_signature(self):
        signature = AdyenController._compute_signature(
            self.webhook_notification_payload, self.provider.adyen_hmac_key
        )
        self.assertEqual(signature, self.webhook_notification_payload_signature)

    def test_application_info_passed_in_payment_request(self):
        """Ensure applicationInfo is added correctly to the payment request payload."""
        tx = self._create_transaction("direct")
        with (
            patch("odoo.addons.payment.utils.check_access_token", return_value="dummy_token"),
            self._mock_send_api_request(return_value=dict()) as mock_make_request,
        ):
            self.make_jsonrpc_request(
                "/payment/adyen/payments",
                params={
                    "provider_id": tx.provider_id.id,
                    "reference": tx.reference,
                    "converted_amount": 1,
                    "currency_id": tx.currency_id.id,
                    "partner_id": tx.partner_id.id,
                    "payment_method": {"type": "scheme"},
                    "access_token": "dummy",
                },
            )
        application_info = mock_make_request.call_args.kwargs["json"].get("applicationInfo")
        self.assertDictEqual(
            application_info,
            {
                "externalPlatform": {
                    "name": "Odoo",
                    "version": release.version,
                    "integrator": "Odoo SA",
                }
            },
        )
