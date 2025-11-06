# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import json
from unittest.mock import patch

from werkzeug.exceptions import Forbidden

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_authorize.controllers.main import AuthorizeController
from odoo.addons.payment_authorize.tests.common import AuthorizeCommon


@tagged('post_install', '-at_install')
class TestProcessingFlows(AuthorizeCommon, PaymentHttpCommon):

    @mute_logger('odoo.addons.payment_authorize.controllers.main')
    def test_webhook_notification_triggers_processing(self):
        """Test that receiving a valid webhook notification triggers the processing of the
        payment data."""
        self._create_transaction('direct')
        url = self._build_url(AuthorizeController._webhook_url)

        with patch(
            'odoo.addons.payment_authorize.controllers.main.AuthorizeController._verify_signature'
        ), patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
        ) as process_mock:
            self._make_json_request(url, data=self.webhook_authcapture_data)
        self.assertEqual(process_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_authorize.controllers.main')
    def test_webhook_notification_triggers_signature_check(self):
        """Test that receiving a webhook notification triggers a signature check."""
        self._create_transaction('direct')
        url = self._build_url(AuthorizeController._webhook_url)

        with patch(
            'odoo.addons.payment_authorize.controllers.main.AuthorizeController._verify_signature'
        ) as signature_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
        ):
            self._make_json_request(url, data=self.webhook_authcapture_data)
            self.assertEqual(signature_check_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_authorize.controllers.main')
    def test_accept_notification_with_valid_signature(self):
        """Test that webhook notification with valid signature is accepted."""
        tx = self._create_transaction('direct')
        body = json.dumps(self.webhook_authcapture_data).encode('utf-8')
        signature_key = self.authorize.authorize_signature_key
        signature = hmac.new(
            signature_key.encode('utf-8'), body, hashlib.sha512
        ).hexdigest().upper()

        self._assert_does_not_raise(
            Forbidden, AuthorizeController._verify_signature, signature, body, tx
        )

    @mute_logger('odoo.addons.payment_authorize.controllers.main')
    def test_webhook_notification_rejects_missing_signature(self):
        """Test that webhook notification with missing signature is rejected."""
        tx = self._create_transaction('direct')
        body = json.dumps(self.webhook_authcapture_data).encode('utf-8')

        self.assertRaises(Forbidden, AuthorizeController._verify_signature, None, body, tx)

    @mute_logger('odoo.addons.payment_authorize.controllers.main')
    def test_webhook_notification_rejects_invalid_signature(self):
        """Test that webhook notification with invalid signature is rejected."""
        tx = self._create_transaction('direct')
        body = json.dumps(self.webhook_authcapture_data).encode('utf-8')
        self.assertRaises(
            Forbidden, AuthorizeController._verify_signature, 'INVALIDSIGNATURE', body, tx
        )
