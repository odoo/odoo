# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from werkzeug.exceptions import Forbidden

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_payu import const as payu_consts
from odoo.addons.payment_payu.controllers.main import PayUController
from odoo.addons.payment_payu.tests.common import PayUCommon


@tagged('post_install', '-at_install')
class TestProcessingFlows(PayUCommon, PaymentHttpCommon):

    @mute_logger('odoo.addons.payment_payu.controllers.main')
    def test_webhook_notification_triggers_processing(self):
        """ Test that receiving a valid webhook notification triggers the processing of the
        payment data. """
        self._create_transaction('direct')
        url = self._build_url(payu_consts.WEBHOOK_URL)
        with patch(
            'odoo.addons.payment_payu.controllers.main.PayUController._verify_signature'
        ), patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
        ) as process_mock:
            self._make_http_post_request(url, data=self.webhook_payment_data)
        self.assertEqual(process_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_payu.controllers.main')
    def test_webhook_notification_triggers_signature_check(self):
        """ Test that receiving a webhook notification triggers a signature check. """
        self._create_transaction('direct')
        url = self._build_url(payu_consts.WEBHOOK_URL)
        with patch(
            'odoo.addons.payment_payu.controllers.main.PayUController._verify_signature'
        ) as signature_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
        ):
            self._make_http_post_request(url, data=self.webhook_payment_data)
            self.assertEqual(signature_check_mock.call_count, 1)

    def test_accept_webhook_notification_with_valid_signature(self):
        """ Test the verification of a webhook notification with a valid signature. """
        tx = self._create_transaction('direct')
        with patch(
            'odoo.addons.payment_payu.utils.generate_payu_hash',
            return_value='valid_hash',
        ):
            data = dict(self.webhook_payment_data, hash='valid_hash')
            self._assert_does_not_raise(
                Forbidden,
                PayUController._verify_signature,
                data,
                'valid_hash',
                tx,
            )

    @mute_logger('odoo.addons.payment_payu.controllers.main')
    def test_reject_notification_with_missing_signature(self):
        """ Test the verification of a notification with a missing hash. """
        tx = self._create_transaction('direct')
        data = dict(self.webhook_payment_data, hash='')
        self.assertRaises(
            Forbidden, PayUController._verify_signature, data, '', tx,
        )

    @mute_logger('odoo.addons.payment_payu.controllers.main')
    def test_reject_notification_with_invalid_signature(self):
        """ Test the verification of a notification with an invalid hash. """
        tx = self._create_transaction('direct')
        data = dict(self.webhook_payment_data, hash='bad_hash')
        with patch(
            'odoo.addons.payment_payu.utils.generate_payu_hash',
            return_value='valid_hash',
        ):
            self.assertRaises(
                Forbidden, PayUController._verify_signature, data, 'bad_hash', tx,
            )

    def test_accept_refund_webhook_with_valid_key(self):
        """ Test that a refund webhook is accepted when the merchant key matches. """
        tx = self._create_transaction('direct')
        self._assert_does_not_raise(
            Forbidden,
            PayUController._verify_signature,
            self.webhook_refund_data,
            self.payu_merchant_key,
            tx,
            is_refund=True,
        )

    @mute_logger('odoo.addons.payment_payu.controllers.main')
    def test_reject_refund_webhook_with_invalid_key(self):
        """ Test that a refund webhook is rejected when the merchant key doesn't match. """
        tx = self._create_transaction('direct')
        self.assertRaises(
            Forbidden, PayUController._verify_signature, self.webhook_refund_data, 'wrong_key', tx, is_refund=True,
        )
