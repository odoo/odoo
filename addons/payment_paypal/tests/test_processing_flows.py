# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_paypal.controllers.main import PaypalController
from odoo.addons.payment_paypal.tests.common import PaypalCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(PaypalCommon, PaymentHttpCommon):
    def test_webhook_notification_triggers_processing(self):
        """Test that receiving a valid webhook notification triggers the processing of the
        payment data."""
        self._create_transaction("direct")
        url = self._build_url(PaypalController._webhook_url)
        with (
            patch(
                "odoo.addons.payment_paypal.controllers.main.PaypalController"
                "._verify_notification_origin"
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_webhook_notification_skips_processing_for_errored_txs(self):
        self._create_transaction("direct")
        PaymentTransaction = self.env.registry["payment.transaction"]
        url = self._build_url(PaypalController._webhook_url)
        with (
            self._mock_send_api_request(side_effect=ValidationError("Test error")),
            patch.object(PaymentTransaction, "_record") as record_mock,
        ):
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(record_mock.call_count, 0)

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_webhook_notification_triggers_origin_check(self):
        """Test that receiving a webhook notification triggers an origin check."""
        self._create_transaction("direct")
        url = self._build_url(PaypalController._webhook_url)
        with patch(
            "odoo.addons.payment_paypal.controllers.main.PaypalController"
            "._verify_notification_origin"
        ) as origin_check_mock:
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(origin_check_mock.call_count, 1)
