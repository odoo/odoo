# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

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
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"
            ) as process_mock,
        ):
            self._make_json_request(url, data=self.webhook_notification_batch_data)
            self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_adyen.controllers.main")
    def test_webhook_notification_triggers_signature_check(self):
        self._create_transaction("direct")
        url = self._build_url(AdyenController._webhook_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock,
            patch("odoo.addons.payment_adyen.controllers.main.AdyenController._compute_signature"),
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"),
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
