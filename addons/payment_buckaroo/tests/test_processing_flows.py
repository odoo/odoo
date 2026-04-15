# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_buckaroo.controllers.main import BuckarooController
from odoo.addons.payment_buckaroo.tests.common import BuckarooCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(BuckarooCommon, PaymentHttpCommon):
    @mute_logger("odoo.addons.payment_buckaroo.controllers.main")
    def test_redirect_notification_triggers_processing(self):
        self._create_transaction("redirect")
        url = self._build_url(BuckarooController._return_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment_buckaroo.models.payment_provider.PaymentProvider"
                "._buckaroo_generate_digital_sign"
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"
            ) as process_mock,
        ):
            self._make_http_post_request(url, data=self.async_payment_data)
            self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_buckaroo.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        self._create_transaction("redirect")
        url = self._build_url(BuckarooController._webhook_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment_buckaroo.models.payment_provider.PaymentProvider"
                "._buckaroo_generate_digital_sign"
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"
            ) as process_mock,
        ):
            self._make_http_post_request(url, data=self.async_payment_data)
            self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_buckaroo.controllers.main")
    def test_redirect_notification_triggers_signature_check(self):
        self._create_transaction("redirect")
        url = self._build_url(BuckarooController._return_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock,
            patch(
                "odoo.addons.payment_buckaroo.models.payment_provider.PaymentProvider"
                "._buckaroo_generate_digital_sign"
            ),
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"),
        ):
            self._make_http_post_request(url, data=self.async_payment_data)
            self.assertEqual(
                signature_check_mock.call_args[0][0], self.async_payment_data_signature
            )

    @mute_logger("odoo.addons.payment_buckaroo.controllers.main")
    def test_webhook_notification_triggers_signature_check(self):
        self._create_transaction("redirect")
        url = self._build_url(BuckarooController._webhook_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock,
            patch(
                "odoo.addons.payment_buckaroo.models.payment_provider.PaymentProvider"
                "._buckaroo_generate_digital_sign"
            ),
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"),
        ):
            self._make_http_post_request(url, data=self.async_payment_data)
            self.assertEqual(
                signature_check_mock.call_args[0][0], self.async_payment_data_signature
            )

    def test_compute_signature_returns_correct_signature(self):
        signature = self.provider._buckaroo_generate_digital_sign(
            self.async_payment_data, incoming=True
        )
        self.assertEqual(signature, self.async_payment_data_signature)
