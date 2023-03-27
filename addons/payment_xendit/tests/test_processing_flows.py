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
    def test_webhook_notification_triggers_signature_verification(self):
        """When webhook data is received, make sure to do signature verification"""
        self._create_transaction('redirect', reference='TEST0001')
        url = self._build_url(XenditController._webhook_url)
        with patch('odoo.addons.payment_xendit.controllers.main.XenditController.'
                   '_xendit_verify_notification_signature'
                   ) as verify_signature_mock:
            self._make_json_request(url, data=self.webhook_notification_data_invoice)
        self.assertEqual(verify_signature_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_xendit.controllers.main')
    def test_webhook_notification_no_signature_deny(self):
        """When a webhook data is received but no signature is found, there should be an issue such that the data is never processed"""
        self._create_transaction('redirect', reference='TEST0001')
        url = self._build_url(XenditController._webhook_url)
        with patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ) as handle_notification_mock:
            self._make_json_request(url, data=self.webhook_notification_data_invoice)
        handle_notification_mock.assert_not_called()

    @mute_logger('odoo.addons.payment_xendit.controllers.main')
    def test_webhook_notification_triggers_processing(self):
        """ Test that receiving a valid webhook notification and signature verified triggers the processing of the
        notification data. """
        self._create_transaction('direct', reference='TEST0001')
        url = self._build_url(XenditController._webhook_url)
        with patch(
            'odoo.addons.payment_xendit.controllers.main.XenditController.'
            '_xendit_verify_notification_signature'
        ), patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ) as handle_notification_data_mock:
            self._make_json_request(url, data=self.webhook_notification_data_invoice)
        self.assertEqual(handle_notification_data_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_xendit.controllers.main')
    def test_reject_notification_with_invalid_signature(self):
        """ Test the verification of a notification with an invalid signature. Forbidden should be raised """
        tx = self._create_transaction('redirect')

        self.assertRaises(
            Forbidden,
            XenditController._xendit_verify_notification_signature,
            'bad_signature',
            tx,
        )

    @mute_logger('odoo.addons.payment_xendit.controllers.main')
    def test_no_error_after_signature(self):
        """If the signature is valid, should not be raising any exceptions"""
        tx = self._create_transaction('redirect')

        self._assert_does_not_raise(
            Forbidden,
            XenditController._xendit_verify_notification_signature,
            'sYFoR4IJxz680OCSjF6B3NAPVQUGVBFRQpYdqwcx0hgIPgYJ',
            tx,
        )

    @mute_logger('odoo.addons.payment_xendit.controllers.main')
    def test_webhook_notif_tokenizes_payment_method(self):
        self._create_transaction('dummy', operation='validation', tokenize=True, reference='TEST0002')
        url = self._build_url(XenditController._webhook_url)
        data = {
            "created": "2023-08-15T09:12:05.672Z",
            "id": "64db4165dcd0c6001a068cff",
            "business_id": "64118d86854d7d89206e732d",
            "card_expiration_month": "10",
            "card_expiration_year": "2025",
            "masked_card_number": "400000XXXXXX1091",
            "status": "VALID",
        }

        with patch(
            'odoo.addons.payment_xendit.controllers.main.XenditController'
            '._xendit_verify_notification_signature'
        ), patch(
            'odoo.addons.payment_xendit.models.payment_provider.PaymentProvider'
            '._xendit_make_request',
            return_value=data
        ), patch(
            'odoo.addons.payment_xendit.models.payment_transaction.PaymentTransaction'
            '._xendit_tokenize_notification_data'
        ) as tokenize_check_mock:
            self._make_json_request(url, data=self.webhook_notification_data_invoice_cc)

        tokenize_check_mock.assert_called_once()

    def test_payment_with_token_charge_card(self):
        """ Flow being used for payment with token is different from the invoice"""
        token = self._create_token(provider_ref="test_ref")
        tx = self._create_transaction('redirect', token_id=token.id, amount=10000, reference="Test tx")

        with patch(
            'odoo.addons.payment_xendit.models.payment_provider.PaymentProvider'
            '._xendit_make_request'
        ) as mock_req:
            tx._send_payment_request()
        mock_req.assert_called_once()
