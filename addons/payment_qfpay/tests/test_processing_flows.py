# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from werkzeug.exceptions import Forbidden

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_qfpay import const
from odoo.addons.payment_qfpay.controllers.main import QFPayController
from odoo.addons.payment_qfpay.tests.common import QFPayCommon


@tagged('post_install', '-at_install')
class TestProcessingFlows(QFPayCommon, PaymentHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.webhook_data = {
            'out_trade_no': cls.reference,
            'txamt': str(int(cls.amount * 100)),
            'txcurrcd': cls.currency.name,
            'respcd': '0000',
        }
        cls.webhook_data['sign'] = cls.provider._qfpay_generate_sign(cls.webhook_data)

    @mute_logger('odoo.addons.payment_qfpay.controllers.main')
    def test_webhook_notification_triggers_processing(self):
        """Test that receiving a valid webhook triggers processing of payment data."""
        self._create_transaction('direct')
        url = self._build_url(const.WEBHOOK_URL)
        with (
            patch('odoo.addons.payment_qfpay.controllers.main.QFPayController._verify_signature'),
            patch('odoo.addons.payment.models.payment_transaction.PaymentTransaction._process') as process_mock,
        ):
            self._make_http_post_request(url, data=self.webhook_data)
        self.assertEqual(process_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_qfpay.controllers.main')
    def test_webhook_notification_triggers_signature_check(self):
        """Test that receiving a webhook triggers the signature verification method."""
        self._create_transaction('direct')
        url = self._build_url(const.WEBHOOK_URL)
        with (
            patch('odoo.addons.payment_qfpay.controllers.main.QFPayController._verify_signature') as signature_check_mock,
            patch('odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'),
        ):
            self._make_http_post_request(url, data=self.webhook_data)
        self.assertEqual(signature_check_mock.call_count, 1)

    def test_accept_payment_data_with_valid_signature(self):
        """Test the verification of payment data with a valid MD5 signature."""
        tx = self._create_transaction('direct')
        self._assert_does_not_raise(
            Forbidden, QFPayController._verify_signature, self.webhook_data, tx
        )

    @mute_logger('odoo.addons.payment_qfpay.controllers.main')
    def test_reject_payment_data_with_missing_signature(self):
        """Test that a missing signature raises a Forbidden exception."""
        tx = self._create_transaction('direct')
        bad_data = dict(self.webhook_data, sign=None)
        self.assertRaises(Forbidden, QFPayController._verify_signature, bad_data, tx)

    @mute_logger('odoo.addons.payment_qfpay.controllers.main')
    def test_reject_payment_data_with_invalid_signature(self):
        """Test that an incorrect signature raises a Forbidden exception."""
        tx = self._create_transaction('direct')
        bad_data = dict(self.webhook_data, sign='dummy_invalid_hash')
        self.assertRaises(Forbidden, QFPayController._verify_signature, bad_data, tx)
