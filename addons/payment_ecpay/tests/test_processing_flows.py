# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from werkzeug.exceptions import Forbidden

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_ecpay.controllers.main import EcpayController
from odoo.addons.payment_ecpay.tests.common import EcpayCommon


@tagged('post_install', '-at_install')
class TestProcessingFlows(EcpayCommon, PaymentHttpCommon):
    @mute_logger('odoo.addons.payment_ecpay.controllers.main')
    def test_webhook_triggers_processing(self):
        """Test that receiving a valid webhook notification triggers the processing of the payment
        data."""
        self._create_transaction('redirect', reference="S0000220251104095811")
        url = self._build_url(EcpayController._webhook_url)
        with (
            patch('odoo.addons.payment_ecpay.controllers.main.EcpayController._verify_signature'),
            patch(
                'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
            ) as process_mock,
        ):
            self._make_http_post_request(url, data=self.payment_result_data)
        self.assertEqual(process_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_ecpay.controllers.main')
    def test_webhook_triggers_signature_check(self):
        """Test that receiving a webhook notification triggers a signature check."""
        self._create_transaction('redirect', reference="S0000220251104095811")
        url = self._build_url(EcpayController._webhook_url)
        with (
            patch(
                'odoo.addons.payment_ecpay.controllers.main.EcpayController._verify_signature'
            ) as signature_check_mock,
            patch('odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'),
        ):
            self._make_http_post_request(url, data=self.payment_result_data)
        self.assertEqual(signature_check_mock.call_count, 1)

    def test_accept_notification_with_valid_signature(self):
        """Test the verification of a notification with a valid signature."""
        tx = self._create_transaction('redirect')
        self._assert_does_not_raise(
            Forbidden, EcpayController._verify_signature, self.payment_result_data, tx
        )

    @mute_logger('odoo.addons.payment_ecpay.controllers.main')
    def test_reject_notification_with_missing_signature(self):
        """Test the verification of a notification with a missing signature."""
        tx = self._create_transaction('redirect')
        payload = dict(self.payment_result_data, CheckMacValue=None)
        self.assertRaises(Forbidden, EcpayController._verify_signature, payload, tx)

    @mute_logger('odoo.addons.payment_ecpay.controllers.main')
    def test_reject_notification_with_invalid_signature(self):
        """Test the verification of a notification with an invalid signature."""
        tx = self._create_transaction('redirect')
        payload = dict(self.payment_result_data, CheckMacValue='dummy')
        self.assertRaises(Forbidden, EcpayController._verify_signature, payload, tx)
