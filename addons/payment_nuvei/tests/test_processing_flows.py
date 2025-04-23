# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from werkzeug.exceptions import Forbidden

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment_nuvei.controllers.main import NuveiController
from odoo.addons.payment_nuvei.tests.common import NuveiCommon


@tagged('post_install', '-at_install')
class TestProcessingFlows(NuveiCommon):

    @mute_logger('odoo.addons.payment_nuvei.controllers.main')
    def test_redirect_notification_triggers_processing(self):
        """ Test that receiving a redirect notification triggers the processing of the notification
        data. """
        self._create_transaction(flow='redirect')
        url = self._build_url(NuveiController._return_url)
        with patch(
            'odoo.addons.payment_nuvei.controllers.main.NuveiController'
            '._verify_notification_signature'
        ), patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ) as handle_notification_data_mock:
            self._make_http_get_request(url, params=self.notification_data)
            self.assertEqual(handle_notification_data_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_nuvei.controllers.main')
    def test_webhook_notification_triggers_processing(self):
        """ Test that receiving a valid webhook notification triggers the processing of the
        notification data. """
        self._create_transaction('redirect')
        url = self._build_url(NuveiController._webhook_url)
        with patch(
            'odoo.addons.payment_nuvei.controllers.main.NuveiController'
            '._verify_notification_signature'
        ), patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ) as handle_notification_data_mock:
            self._make_http_post_request(url, data=self.notification_data)
            self.assertEqual(handle_notification_data_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_nuvei.controllers.main')
    def test_redirect_notification_triggers_signature_check(self):
        """ Test that receiving a redirect notification triggers a signature check. """
        self._create_transaction('redirect')
        url = self._build_url(NuveiController._return_url)
        with patch(
            'odoo.addons.payment_nuvei.controllers.main.NuveiController'
            '._verify_notification_signature'
        ) as signature_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ):
            self._make_http_get_request(url, params=self.notification_data)
            self.assertEqual(signature_check_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_nuvei.controllers.main')
    def test_webhook_notification_triggers_signature_check(self):
        """ Test that receiving a webhook notification triggers a signature check. """
        self._create_transaction('redirect')
        url = self._build_url(NuveiController._webhook_url)
        with patch(
            'odoo.addons.payment_nuvei.controllers.main.NuveiController'
            '._verify_notification_signature'
        ) as signature_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ):
            self._make_http_post_request(url, data=self.notification_data)
            self.assertEqual(signature_check_mock.call_count, 1)

    def test_accept_notification_with_valid_signature(self):
        """ Test the verification of a notification with a valid signature. """
        tx = self._create_transaction('redirect')
        self._assert_does_not_raise(
            Forbidden, NuveiController._verify_notification_signature, tx, self.notification_data
        )

    @mute_logger('odoo.addons.payment_nuvei.controllers.main')
    def test_reject_notification_with_missing_signature(self):
        """ Test the verification of a notification with a missing signature. """
        tx = self._create_transaction('redirect')
        payload = dict(self.notification_data, advanceResponseChecksum=None)
        self.assertRaises(Forbidden, NuveiController._verify_notification_signature, tx, payload)

    @mute_logger('odoo.addons.payment_nuvei.controllers.main')
    def test_reject_notification_with_invalid_signature(self):
        """ Test the verification of a notification with an invalid signature. """
        tx = self._create_transaction('redirect')
        payload = dict(self.notification_data, advanceResponseChecksum='dummy')
        self.assertRaises(Forbidden, NuveiController._verify_notification_signature, tx, payload)
