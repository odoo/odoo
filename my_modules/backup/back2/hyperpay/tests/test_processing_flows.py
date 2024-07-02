# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from werkzeug.exceptions import Forbidden

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_razorpay.controllers.main import RazorpayController
from odoo.addons.payment_razorpay.tests.common import RazorpayCommon


@tagged('post_install', '-at_install')
class TestProcessingFlows(RazorpayCommon, PaymentHttpCommon):

    @mute_logger('odoo.addons.payment_razorpay.controllers.main')
    def test_webhook_notification_triggers_processing(self):
        """ Test that receiving a valid webhook notification triggers the processing of the
        notification data. """
        self._create_transaction('direct')
        url = self._build_url(RazorpayController._webhook_url)
        with patch(
            'odoo.addons.payment_razorpay.controllers.main.RazorpayController.'
            '_verify_notification_signature'
        ), patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ) as handle_notification_data_mock:
            self._make_json_request(url, data=self.webhook_notification_data)
        self.assertEqual(handle_notification_data_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_razorpay.controllers.main')
    def test_webhook_notification_triggers_processing_for_tokenize_transaction(self):
        """ Test that receiving a valid webhook notification triggers the processing of the
        notification data for tokenize transaction. """
        self._create_transaction('redirect', tokenize=True, payment_method_id=self.payment_method_id)
        url = self._build_url(RazorpayController._webhook_url)
        with patch(
            'odoo.addons.payment_razorpay.controllers.main.RazorpayController.'
            '_verify_notification_signature'
        ), patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ) as handle_notification_data_mock:
            self._make_json_request(url, data=self.webhook_notification_data)
        self.assertEqual(handle_notification_data_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_razorpay.controllers.main')
    def test_webhook_notification_triggers_signature_check(self):
        """ Test that receiving a webhook notification triggers a signature check. """
        self._create_transaction('redirect')
        url = self._build_url(RazorpayController._webhook_url)
        with patch(
            'odoo.addons.payment_razorpay.controllers.main.RazorpayController'
            '._verify_notification_signature'
        ) as signature_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ):
            self._make_json_request(url, data=self.webhook_notification_data)
            self.assertEqual(signature_check_mock.call_count, 1)

    def test_accept_webhook_notification_with_valid_signature(self):
        """ Test the verification of a webhook notification with a valid signature. """
        tx = self._create_transaction('redirect')
        with patch(
            'odoo.addons.payment_razorpay.models.payment_provider.PaymentProvider'
            '._razorpay_calculate_signature', return_value='valid_signature'
        ):
            self._assert_does_not_raise(
                Forbidden,
                RazorpayController._verify_notification_signature,
                self.webhook_notification_data,
                'valid_signature',
                tx,
                is_redirect=False,
            )

    @mute_logger('odoo.addons.payment_razorpay.controllers.main')
    def test_reject_notification_with_missing_signature(self):
        """ Test the verification of a notification with a missing signature. """
        tx = self._create_transaction('redirect')
        self.assertRaises(
            Forbidden,
            RazorpayController._verify_notification_signature,
            self.webhook_notification_data,
            None,
            tx,
        )

    @mute_logger('odoo.addons.payment_razorpay.controllers.main')
    def test_reject_notification_with_invalid_signature(self):
        """ Test the verification of a notification with an invalid signature. """
        tx = self._create_transaction('redirect')
        with patch(
            'odoo.addons.payment_razorpay.models.payment_provider.PaymentProvider'
            '._razorpay_calculate_signature', return_value='valid_signature'
        ):
            self.assertRaises(
                Forbidden,
                RazorpayController._verify_notification_signature,
                self.webhook_notification_data,
                'bad_signature',
                tx,
            )
