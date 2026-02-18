# Part of Odoo. See LICENSE file for full copyright and licensing details.
import copy
from datetime import datetime, UTC, timedelta
from unittest.mock import patch

from werkzeug.exceptions import Forbidden

from odoo.tests import tagged, freeze_time
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_stripe.controllers.main import StripeController
from odoo.addons.payment_stripe.tests.common import StripeCommon


@tagged('post_install', '-at_install')
class TestProcessingFlows(StripeCommon, PaymentHttpCommon):
    @mute_logger('odoo.addons.payment_stripe.controllers.main')
    def test_redirect_notification_triggers_processing(self):
        """Test that receiving a redirect notification triggers the processing of the
        payment data."""
        self._create_transaction('redirect')
        url = self._build_url(StripeController._return_url)
        with (
            patch(
                'odoo.addons.payment.models.payment_transaction.PaymentTransaction._send_api_request',
                self._mock_setup_intent_request,
            ),
            patch(
                'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
            ) as process_mock,
        ):
            self._make_http_get_request(url, params={'reference': self.reference})
            self.assertEqual(process_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_stripe.controllers.main')
    def test_webhook_notification_triggers_processing(self):
        """Test that receiving a webhook notification triggers the processing of the
        payment data."""
        self._create_transaction('redirect')
        url = self._build_url(StripeController._webhook_url)
        with (
            patch('odoo.addons.payment_stripe.controllers.main.StripeController._verify_signature'),
            patch(
                'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
            ) as process_mock,
        ):
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(process_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_stripe.controllers.main')
    def test_webhook_notification_triggers_signature_check(self):
        """Test that receiving a webhook notification triggers a signature check."""
        self._create_transaction('redirect')
        url = self._build_url(StripeController._webhook_url)
        with patch(
            'odoo.addons.payment_stripe.controllers.main.StripeController._verify_signature'
        ) as signature_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
        ):
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(signature_check_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_stripe.controllers.main')
    @mute_logger('odoo.addons.payment_stripe.models.payment_transaction')
    def test_webhook_notification_skips_signature_verification_for_missing_transactions(self):
        """Test that the webhook ignores signature verification for unknown transactions (e.g. POS)."""
        url = self._build_url(StripeController._webhook_url)
        payload = copy.deepcopy(self.payment_data)
        payload['data']['object']['description'] = None
        with patch(
                'odoo.addons.payment_stripe.controllers.main.StripeController._verify_signature'
        ) as signature_check_mock:
            self._make_json_request(url, data=payload)
            self.assertEqual(signature_check_mock.call_count, 0)

    @freeze_time('2026-02-13 15:08:21')
    def test_accept_notification_with_valid_signature(self):
        """Test the verification of a notification with a valid signature."""
        tx = self._create_transaction('redirect')
        timestamp = int((datetime.now(UTC) - timedelta(minutes=1)).timestamp())
        signature_data = {
            'v1': '784393e05d0740e61283ff81eb3738b3355a67e031bf465e92ebd0f424478a26',
            't': timestamp,
        }
        signature_header = ','.join(f"{k}={v}" for k, v in signature_data.items())
        self._assert_does_not_raise(
            Forbidden,
            StripeController._verify_signature,
            '',
            signature_header,
            tx,
        )

    @freeze_time('2026-02-13 15:08:21')
    @mute_logger('odoo.addons.payment_stripe.controllers.main', 'odoo.addons.payment.utils')
    def test_reject_notification_with_missing_signature(self):
        """Test the verification of a notification with a missing signature."""
        tx = self._create_transaction('redirect')
        timestamp = int((datetime.now(UTC) - timedelta(minutes=1)).timestamp())
        signature_data = ({'v1': None, 't': timestamp})
        signature_header = ','.join(f"{k}={v}" for k, v in signature_data.items())
        self.assertRaises(
            Forbidden,
            StripeController._verify_signature,
            '',
            signature_header,
            tx,
        )

    @freeze_time('2026-02-13 15:08:21')
    @mute_logger('odoo.addons.payment_stripe.controllers.main', 'odoo.addons.payment.utils')
    def test_reject_notification_with_invalid_signature(self):
        """Test the verification of a notification with an invalid signature."""
        tx = self._create_transaction('redirect')
        timestamp = int((datetime.now(UTC) - timedelta(minutes=1)).timestamp())
        signature_data = {'v1': 'Wrong', 't': timestamp}
        signature_header = ','.join(f"{k}={v}" for k, v in signature_data.items())
        self.assertRaises(
            Forbidden,
            StripeController._verify_signature,
            '',
            signature_header,
            tx,
        )

    @freeze_time('2026-02-13 15:08:21')
    @mute_logger('odoo.addons.payment_stripe.controllers.main', 'odoo.addons.payment.utils')
    def test_reject_notification_with_outdated_signature(self):
        """Test the verification of a notification with an outdated signature."""
        tx = self._create_transaction('redirect')
        timestamp = int(
            (datetime.now(UTC) - timedelta(minutes=1)).timestamp()
            - StripeController.WEBHOOK_AGE_TOLERANCE
        )
        signature_data = {'v1': 'Test Signature', 't': timestamp}
        signature_header = ','.join(f"{k}={v}" for k, v in signature_data.items())
        self.assertRaises(
            Forbidden,
            StripeController._verify_signature,
            '',
            signature_header,
            tx,
        )
