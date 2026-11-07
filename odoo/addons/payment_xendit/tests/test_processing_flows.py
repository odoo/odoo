# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from werkzeug.exceptions import Forbidden
from werkzeug.urls import url_encode

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

    def test_set_xendit_transactions_to_pending_on_return(self):
        def build_return_url(**kwargs):
            url_params = url_encode(dict(kwargs, tx_ref=self.reference))
            return self._build_url(f'{XenditController._return_url}?{url_params}')

        self.reference = "xendit_tx1"
        tx = self._create_transaction('redirect')

        with patch(
            'odoo.addons.payment.utils.generate_access_token', new=self._generate_test_access_token
        ):
            access_token = self._generate_test_access_token(tx.reference, tx.amount)

            self._make_http_get_request(build_return_url(success='true', access_token='coincoin'))
            self.assertEqual(tx.state, 'draft', "Random GET requests shouldn't affect tx state")

            self._make_http_get_request(build_return_url(success='false', access_token=access_token))
            self.assertEqual(tx.state, 'draft', "Failure returns shouldn't change tx state")

            self._make_http_get_request(build_return_url(success='true', access_token=access_token))
            self.assertEqual(tx.state, 'pending', "Successful returns should set state to pending")
