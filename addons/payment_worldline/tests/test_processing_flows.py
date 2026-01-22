# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import json
from base64 import b64encode
from unittest.mock import patch

from werkzeug.exceptions import Forbidden

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_worldline.controllers.main import WorldlineController
from odoo.addons.payment_worldline.tests.common import WorldlineCommon


@tagged('post_install', '-at_install')
class TestProcessingFlows(WorldlineCommon, PaymentHttpCommon):
    @mute_logger('odoo.addons.payment_worldline.controllers.main')
    def test_redirect_notification_triggers_processing(self):
        """Test that receiving a redirect notification triggers the processing of the
        payment data."""
        tx = self._create_transaction('redirect')
        url = self._build_url(WorldlineController._return_url)
        with (
            patch(
                'odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request',
            ),
            patch(
                'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
            ) as process_mock
        ):
            self.payment_data['provider_id'] = tx.provider_id.id
            self.payment_data['hostedCheckoutId'] = ''
            self._make_http_get_request(url, params=self.payment_data)
            self.assertEqual(process_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_worldline.controllers.main')
    def test_webhook_notification_triggers_processing(self):
        """Test that receiwebhookedirect notification triggers the processing of the
        payment data."""
        self._create_transaction('redirect')
        url = self._build_url(WorldlineController._webhook_url)
        with patch(
            'odoo.addons.payment_worldline.controllers.main.WorldlineController._verify_signature'
        ), patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
        ) as process_mock:
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(process_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_worldline.controllers.main')
    def test_webhook_notification_triggers_signature_check(self):
        """Test that receiving a webhook notification triggers a signature check."""
        self._create_transaction('redirect')
        url = self._build_url(WorldlineController._webhook_url)
        with patch(
            'odoo.addons.payment_worldline.controllers.main.WorldlineController._verify_signature'
        ) as signature_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
        ):
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(signature_check_mock.call_count, 1)

    def test_accept_notification_with_valid_signature(self):
        """Test the verification of a notification with a valid signature."""
        tx = self._create_transaction('redirect')
        unencoded_result = hmac.new(
            self.worldline.worldline_webhook_secret.encode(),
            json.dumps(self.payment_data).encode(),
            hashlib.sha256,
        ).digest()
        expected_signature = b64encode(unencoded_result)
        self._assert_does_not_raise(
            Forbidden,
            WorldlineController._verify_signature,
            json.dumps(self.payment_data).encode(),
            expected_signature,
            tx,
        )

    @mute_logger('odoo.addons.payment_worldline.controllers.main', 'odoo.addons.payment.utils')
    def test_reject_notification_with_missing_signature(self):
        """Test the verification of a notification with a missing signature."""
        tx = self._create_transaction('redirect')
        self.assertRaises(
            Forbidden,
            WorldlineController._verify_signature,
            json.dumps(self.payment_data).encode(),
            None,
            tx,
        )

    @mute_logger('odoo.addons.payment_worldline.controllers.main', 'odoo.addons.payment.utils')
    def test_reject_notification_with_invalid_signature(self):
        """Test the verification of a notification with an invalid signature."""
        tx = self._create_transaction('redirect')
        self.assertRaises(
            Forbidden,
            WorldlineController._verify_signature,
            json.dumps(self.payment_data).encode(),
            b'dummy',
            tx,
        )
