# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.controllers.payment_status import PaymentStatus
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_payfast.controllers.main import PayfastController
from odoo.addons.payment_payfast.tests.common import PayfastCommon

PROVIDER_PATH = "odoo.addons.payment_payfast.models.payment_provider.PaymentProvider"
CONTROLLER_PATH = "odoo.addons.payment_payfast.controllers.main.PayfastController"
RECORD_PATH = "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"


@tagged("post_install", "-at_install")
class TestProcessingFlows(PayfastCommon, PaymentHttpCommon):
    def _get_notify_url(self):
        return self._build_url(PayfastController._notify_url)

    @mute_logger("odoo.addons.payment_payfast.controllers.main")
    def test_notification_triggers_processing(self):
        """Test that a fully valid ITN notification triggers the processing of the payment
        data."""
        self._create_transaction(flow="redirect")
        with (
            patch(
                f"{PROVIDER_PATH}._payfast_generate_signature",
                return_value=self.notification_data["signature"],
            ),
            patch(f"{CONTROLLER_PATH}._verify_source", return_value=True),
            patch(f"{PROVIDER_PATH}._payfast_validate_with_server", return_value=True),
            patch(RECORD_PATH) as record_mock,
        ):
            self._make_http_post_request(self._get_notify_url(), data=self.notification_data)
        self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_payfast.controllers.main")
    def test_notification_with_invalid_signature_does_not_trigger_processing(self):
        self._create_transaction(flow="redirect")
        with (
            patch(f"{PROVIDER_PATH}._payfast_generate_signature", return_value="wrong_signature"),
            patch(RECORD_PATH) as record_mock,
        ):
            self._make_http_post_request(self._get_notify_url(), data=self.notification_data)
        record_mock.assert_not_called()

    @mute_logger("odoo.addons.payment_payfast.controllers.main")
    def test_notification_from_untrusted_source_does_not_trigger_processing(self):
        self._create_transaction(flow="redirect")
        with (
            patch(
                f"{PROVIDER_PATH}._payfast_generate_signature",
                return_value=self.notification_data["signature"],
            ),
            # No Referer header is sent by the test client, so the source check fails on its own.
            patch(RECORD_PATH) as record_mock,
        ):
            self._make_http_post_request(self._get_notify_url(), data=self.notification_data)
        record_mock.assert_not_called()

    @mute_logger("odoo.addons.payment_payfast.controllers.main")
    def test_notification_with_mismatched_amount_does_not_trigger_processing(self):
        self._create_transaction(flow="redirect")
        mismatched_data = {**self.notification_data, "amount_gross": "0.01"}
        with (
            patch(
                f"{PROVIDER_PATH}._payfast_generate_signature",
                return_value=mismatched_data["signature"],
            ),
            patch(f"{CONTROLLER_PATH}._verify_source", return_value=True),
            patch(RECORD_PATH) as record_mock,
        ):
            self._make_http_post_request(self._get_notify_url(), data=mismatched_data)
        record_mock.assert_not_called()

    @mute_logger("odoo.addons.payment_payfast.controllers.main")
    def test_notification_not_confirmed_by_server_does_not_trigger_processing(self):
        self._create_transaction(flow="redirect")
        with (
            patch(
                f"{PROVIDER_PATH}._payfast_generate_signature",
                return_value=self.notification_data["signature"],
            ),
            patch(f"{CONTROLLER_PATH}._verify_source", return_value=True),
            patch(f"{PROVIDER_PATH}._payfast_validate_with_server", return_value=False),
            patch(RECORD_PATH) as record_mock,
        ):
            self._make_http_post_request(self._get_notify_url(), data=self.notification_data)
        record_mock.assert_not_called()

    def test_cancel_route_end_to_end_cancels_the_monitored_transaction(self):
        """Test the cancel route without mocking `_record`, exercising the real `payment.data`
        write and cron-based processing, end to end."""
        tx = self._create_transaction(flow="redirect")
        self.authenticate(None, None)
        self.update_session(**{PaymentStatus.MONITORED_TX_ID_KEY: tx.id})
        self._make_http_get_request(self._build_url(PayfastController._cancel_url))
        self._run_processing()
        self.assertEqual(tx.state, "cancel")

    def test_cancel_route_without_a_monitored_transaction_does_not_crash(self):
        self.authenticate(None, None)
        with patch(RECORD_PATH) as record_mock:
            response = self._make_http_get_request(self._build_url(PayfastController._cancel_url))
        record_mock.assert_not_called()
        self.assertEqual(response.status_code, 200)
