# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_mollie.controllers.main import MollieController
from odoo.addons.payment_mollie.tests.common import MollieCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(MollieCommon, PaymentHttpCommon):
    @mute_logger("odoo.addons.payment_mollie.controllers.main")
    def test_returning_from_payment_triggers_processing(self):
        self._create_transaction("direct")
        url = self._build_url(MollieController._return_url)
        with (
            self._mock_send_api_request(return_value=self.payment_data),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_http_post_request(url, data=self.payment_data)
            self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_mollie.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        self._create_transaction("direct")
        url = self._build_url(MollieController._webhook_url)
        with (
            self._mock_send_api_request(return_value=self.payment_data),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_http_post_request(url, data=self.payment_data)
            self.assertEqual(record_mock.call_count, 1)
