# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from werkzeug.exceptions import Forbidden

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_adyen.controllers.main import AdyenController
from odoo.addons.payment_adyen.tests.common import AdyenCommon


@tagged('post_install', '-at_install')
class TestProcessingFlows(AdyenCommon, PaymentHttpCommon):
    @mute_logger('odoo.addons.payment_aps.controllers.main')
    def test_webhook_notification_triggers_processing(self):
        """Test that receiving a webhook notification triggers the processing of the
        payment data."""
        self._create_transaction('direct')
        url = self._build_url(AdyenController._webhook_url)
        with patch(
            'odoo.addons.payment_adyen.controllers.main.AdyenController._verify_signature'
        ), patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
        ) as process_mock:
            self._make_json_request(url, data=self.webhook_notification_batch_data)
            self.assertEqual(process_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_adyen.controllers.main')
    def test_webhook_notification_triggers_signature_check(self):
        """Test that receiving a webhook notification triggers a signature check."""
        self._create_transaction('direct')
        url = self._build_url(AdyenController._webhook_url)
        with patch(
            'odoo.addons.payment_adyen.controllers.main.AdyenController._verify_signature'
        ) as signature_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
        ):
            self._make_json_request(url, data=self.webhook_notification_batch_data)
            self.assertEqual(signature_check_mock.call_count, 1)

    def test_accept_webhook_notification_with_valid_signature(self):
        """Test the verification of a webhook notification with a valid signature."""
        tx = self._create_transaction('direct')
        self._assert_does_not_raise(
            Forbidden, AdyenController._verify_signature, self.webhook_notification_payload, tx
        )

    @mute_logger('odoo.addons.payment_adyen.controllers.main', 'odoo.addons.payment.utils')
    def test_reject_webhook_notification_with_missing_signature(self):
        """Test the verification of a webhook notification with a missing signature."""
        payload = dict(self.webhook_notification_payload, additionalData={'hmacSignature': None})
        tx = self._create_transaction('direct')
        self.assertRaises(Forbidden, AdyenController._verify_signature, payload, tx)

    @mute_logger('odoo.addons.payment_adyen.controllers.main', 'odoo.addons.payment.utils')
    def test_reject_webhook_notification_with_invalid_signature(self):
        """Test the verification of a webhook notification with an invalid signature."""
        payload = dict(self.webhook_notification_payload, additionalData={'hmacSignature': 'dummy'})
        tx = self._create_transaction('direct')
        self.assertRaises(Forbidden, AdyenController._verify_signature, payload, tx)
