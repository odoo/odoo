# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment_nuvei.controllers.main import NuveiController
from odoo.addons.payment_nuvei.tests.common import NuveiCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(NuveiCommon):
    @mute_logger("odoo.addons.payment_nuvei.controllers.main")
    def test_returning_from_payment_triggers_processing(self):
        """Test that receiving a redirect notification triggers the processing of the notification
        data."""
        self._create_transaction(flow="redirect")
        url = self._build_url(NuveiController._return_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment_nuvei.models.payment_provider.PaymentProvider"
                "._nuvei_calculate_signature"
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_http_get_request(url, params=self.payment_data)
            self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_nuvei.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        """Test that receiving a valid webhook notification triggers the processing of the
        payment data."""
        self._create_transaction("redirect")
        url = self._build_url(NuveiController._webhook_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment_nuvei.models.payment_provider.PaymentProvider"
                "._nuvei_calculate_signature"
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_http_post_request(url, data=self.payment_data)
            self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_nuvei.controllers.main")
    def test_process_empty_payment_data_on_cancellation(self):
        tx = self._create_transaction("redirect")
        url = self._build_url(NuveiController._return_url)
        error_access_token = self._generate_test_access_token(tx.reference)
        payment_data = dict(
            tx_ref=tx.reference, error_access_token=error_access_token, **self.payment_data
        )
        with patch(
            "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
        ) as record_mock:
            self._make_http_get_request(url, params=payment_data)
            record_mock.assert_called_once_with({})

    @mute_logger("odoo.addons.payment_nuvei.controllers.main")
    def test_returning_from_payment_triggers_signature_check(self):
        self._create_transaction("redirect")
        url = self._build_url(NuveiController._return_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock,
            patch(
                "odoo.addons.payment_nuvei.models.payment_provider.PaymentProvider"
                "._nuvei_calculate_signature"
            ),
        ):
            self._make_http_get_request(url, params=self.payment_data)
            self.assertEqual(signature_check_mock.call_args[0][0], self.payment_data_signature)

    @mute_logger("odoo.addons.payment_nuvei.controllers.main")
    def test_webhook_notification_triggers_signature_check(self):
        self._create_transaction("redirect")
        url = self._build_url(NuveiController._webhook_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock,
            patch(
                "odoo.addons.payment_nuvei.models.payment_provider.PaymentProvider"
                "._nuvei_calculate_signature"
            ),
        ):
            self._make_http_post_request(url, data=self.payment_data)
            self.assertEqual(signature_check_mock.call_args[0][0], self.payment_data_signature)
