# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_worldline.controllers.main import WorldlineController
from odoo.addons.payment_worldline.tests.common import WorldlineCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(WorldlineCommon, PaymentHttpCommon):
    @mute_logger("odoo.addons.payment_worldline.controllers.main")
    def test_redirect_notification_triggers_processing(self):
        tx = self._create_transaction("redirect")
        url = self._build_url(WorldlineController._return_url)
        with (
            patch("odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"
            ) as process_mock,
        ):
            self.payment_data["provider_id"] = tx.provider_id.id
            self.payment_data["hostedCheckoutId"] = ""
            self._make_http_get_request(url, params=self.payment_data)
            self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_worldline.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        self._create_transaction("redirect")
        url = self._build_url(WorldlineController._webhook_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"
            ) as process_mock,
        ):
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_worldline.controllers.main")
    def test_webhook_notification_triggers_signature_check(self):
        self._create_transaction("redirect")
        url = self._build_url(WorldlineController._webhook_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock,
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"),
        ):
            self.opener.headers["X-GCS-Signature"] = self.payment_data_signature
            self._make_json_request(url, data=self.payment_data)
            self.opener.headers.pop("X-GCS-Signature")

            self.assertEqual(signature_check_mock.call_args[0][0], self.payment_data_signature)
