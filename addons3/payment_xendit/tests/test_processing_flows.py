# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from werkzeug.exceptions import Forbidden

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_xendit.controllers.main import XenditController
from odoo.addons.payment_xendit.tests.common import XenditCommon


@tagged('post_install', '-at_install')
class TestProcessingFlow(XenditCommon, PaymentHttpCommon):

    @mute_logger('odoo.addons.payment_xendit.controllers.main')
    def test_webhook_notification_triggers_processing(self):
        """ Test that receiving a valid webhook notification and signature verified triggers the
        processing of the notification data. """
        self._create_transaction('redirect')
        url = self._build_url(XenditController._webhook_url)
        with patch(
            'odoo.addons.payment_xendit.controllers.main.XenditController'
            '._verify_notification_token'
        ), patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ) as handle_notification_data_mock:
            self._make_json_request(url, data=self.webhook_notification_data)
        self.assertEqual(handle_notification_data_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_xendit.controllers.main')
    def test_webhook_notification_triggers_signature_check(self):
        """ Test that receiving a webhook notification triggers a signature check. """
        self._create_transaction('redirect')
        url = self._build_url(XenditController._webhook_url)
        with patch(
            'odoo.addons.payment_xendit.controllers.main.XenditController.'
            '_verify_notification_token'
        ) as signature_check_mock:
            self._make_json_request(url, data=self.webhook_notification_data)
            self.assertEqual(signature_check_mock.call_count, 1)

    def test_accept_webhook_notification_with_valid_signature(self):
        """ Test the verification of a webhook notification with a valid signature. """
        tx = self._create_transaction('redirect')
        self._assert_does_not_raise(
            Forbidden,
            XenditController._verify_notification_token,
            XenditController,
            self.provider.xendit_webhook_token,
            tx,
        )

    @mute_logger('odoo.addons.payment_xendit.controllers.main')
    def test_reject_notification_with_missing_signature(self):
        """ Test the verification of a notification with a missing signature. """
        tx = self._create_transaction('redirect')
        self.assertRaises(
            Forbidden,
            XenditController._verify_notification_token,
            XenditController,
            None,
            tx,
        )

    @mute_logger('odoo.addons.payment_xendit.controllers.main')
    def test_reject_notification_with_invalid_signature(self):
        """ Test the verification of a notification with an invalid signature. """
        tx = self._create_transaction('redirect')
        self.assertRaises(
            Forbidden, XenditController._verify_notification_token, XenditController, 'dummy', tx
        )
