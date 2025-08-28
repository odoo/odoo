# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from werkzeug.exceptions import Forbidden

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_redsys.controllers.main import RedsysController
from odoo.addons.payment_redsys.tests.common import RedsysCommon


@tagged('post_install', '-at_install')
class TestProcessingFlows(RedsysCommon, PaymentHttpCommon):

    @mute_logger('odoo.addons.payment_redsys.controllers.main')
    def test_returning_from_payment_triggers_processing(self):
        """Test that receiving a valid redirect notification triggers the processing of the
        payment data."""
        self._create_transaction('redirect')
        url = self._build_url(RedsysController._return_url)
        with patch(
            'odoo.addons.payment_redsys.controllers.main.RedsysController._verify_signature',
        ), patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
        ) as process_mock:
            self._make_http_get_request(url, params=self.payment_data)
        self.assertEqual(process_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_redsys.controllers.main')
    def test_webhook_triggers_processing(self):
        """Test that receiving a valid webhook notification triggers the processing of the payment
        data."""
        self._create_transaction('redirect')
        url = self._build_url(RedsysController._webhook_url)
        with patch(
            'odoo.addons.payment_redsys.controllers.main.RedsysController._verify_signature'
        ), patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
        ) as process_mock:
            self._make_http_post_request(url, data=self.payment_data)
        self.assertEqual(process_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_redsys.controllers.main')
    def test_returning_from_payment_triggers_signature_check(self):
        """Test that receiving a redirect notification triggers a signature check."""
        self._create_transaction('redirect')
        url = self._build_url(RedsysController._return_url)
        with patch(
            'odoo.addons.payment_redsys.controllers.main.RedsysController._verify_signature'
        ) as signature_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
        ):
            self._make_http_get_request(url, params=self.payment_data)
        self.assertEqual(signature_check_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_redsys.controllers.main')
    def test_webhook_triggers_signature_check(self):
        """Test that receiving a webhook notification triggers a signature check."""
        self._create_transaction('redirect')
        url = self._build_url(RedsysController._webhook_url)
        with patch(
            'odoo.addons.payment_redsys.controllers.main.RedsysController._verify_signature'
        ) as signature_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
        ):
            self._make_http_post_request(url, data=self.payment_data)
        self.assertEqual(signature_check_mock.call_count, 1)

    def test_accept_notification_with_valid_signature(self):
        """Test the verification of a notification with a valid signature."""
        tx = self._create_transaction('redirect')
        self._assert_does_not_raise(
            Forbidden, RedsysController._verify_signature, self.payment_data, tx
        )

    @mute_logger('odoo.addons.payment_redsys.controllers.main')
    def test_reject_notification_with_missing_signature(self):
        """Test the verification of a notification with a missing signature."""
        tx = self._create_transaction('redirect')
        payload = dict(self.payment_data, Ds_Signature=None)
        self.assertRaises(Forbidden, RedsysController._verify_signature, payload, tx)

    @mute_logger('odoo.addons.payment_redsys.controllers.main')
    def test_reject_notification_with_invalid_signature(self):
        """Test the verification of a notification with an invalid signature."""
        tx = self._create_transaction('redirect')
        payload = dict(self.payment_data, Ds_Signature='dummy')
        self.assertRaises(Forbidden, RedsysController._verify_signature, payload, tx)
