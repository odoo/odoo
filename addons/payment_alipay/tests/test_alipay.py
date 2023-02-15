# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from werkzeug.exceptions import Forbidden

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_alipay.controllers.main import AlipayController
from odoo.addons.payment_alipay.tests.common import AlipayCommon


@tagged('post_install', '-at_install')
class AlipayTest(AlipayCommon, PaymentHttpCommon):

    def test_compatible_providers(self):
        self.alipay.alipay_payment_method = 'express_checkout'
        providers = self.env['payment.provider']._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, currency_id=self.currency_yuan.id
        )
        self.assertIn(self.alipay, providers)
        providers = self.env['payment.provider']._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, currency_id=self.currency_euro.id
        )
        self.assertNotIn(self.alipay, providers)

        self.alipay.alipay_payment_method = 'standard_checkout'
        providers = self.env['payment.provider']._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, currency_id=self.currency_yuan.id
        )
        self.assertIn(self.alipay, providers)
        providers = self.env['payment.provider']._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, currency_id=self.currency_euro.id
        )
        self.assertIn(self.alipay, providers)

    def test_01_redirect_form_standard_checkout(self):
        self.alipay.alipay_payment_method = 'standard_checkout'
        self._test_alipay_redirect_form()

    def test_02_redirect_form_express_checkout(self):
        self.alipay.alipay_payment_method = 'express_checkout'
        self._test_alipay_redirect_form()

    def _test_alipay_redirect_form(self):
        tx = self._create_transaction(flow='redirect')  # Only flow implemented

        expected_values = {
            '_input_charset': 'utf-8',
            'notify_url': self._build_url(AlipayController._webhook_url),
            'out_trade_no': self.reference,
            'partner': self.alipay.alipay_merchant_partner_id,
            'return_url': self._build_url(AlipayController._return_url),
            'subject': self.reference,
            'total_fee': str(self.amount),  # Fees disabled by default
        }

        if self.alipay.alipay_payment_method == 'standard_checkout':
            expected_values.update({
                'service': 'create_forex_trade',
                'product_code': 'NEW_OVERSEAS_SELLER',
                'currency': self.currency_yuan.name,
            })
        else:
            expected_values.update({
                'service': 'create_direct_pay_by_user',
                'payment_type': str(1),
                'seller_email': self.alipay.alipay_seller_email,
            })
        sign = self.alipay._alipay_compute_signature(expected_values)

        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = tx._get_processing_values()
        redirect_form_data = self._extract_values_from_html_form(processing_values['redirect_form_html'])

        expected_values.update({
            'sign': sign,
            'sign_type': 'MD5',
        })

        self.assertEqual(
            redirect_form_data['action'],
            'https://openapi.alipaydev.com/gateway.do',
        )
        self.assertDictEqual(
            expected_values,
            redirect_form_data['inputs'],
            "Alipay: invalid inputs specified in the redirect form.",
        )

    def test_03_redirect_form_with_fees(self):
        # update provider: compute fees
        self.alipay.write({
            'fees_active': True,
            'fees_dom_fixed': 1.0,
            'fees_dom_var': 0.0035,
            'fees_int_fixed': 1.5,
            'fees_int_var': 0.005,
        })

        transaction_fees = self.currency.round(
            self.alipay._compute_fees(
                self.amount,
                self.currency,
                self.partner.country_id,
            )
        )
        self.assertEqual(transaction_fees, 18.78)
        total_fee = self.currency.round(self.amount + transaction_fees)
        self.assertEqual(total_fee, 1129.89)

        tx = self._create_transaction(flow='redirect')
        self.assertEqual(tx.fees, 18.78)
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = tx._get_processing_values()
        redirect_form_data = self._extract_values_from_html_form(processing_values['redirect_form_html'])

        self.assertEqual(redirect_form_data['inputs']['total_fee'], f'{total_fee:.2f}')

    def test_21_standard_checkout_feedback(self):
        self.alipay.alipay_payment_method = 'standard_checkout'
        self.currency = self.currency_euro
        self._test_alipay_feedback_processing()

    def test_22_express_checkout_feedback(self):
        self.alipay.alipay_payment_method = 'express_checkout'
        self.currency = self.currency_yuan
        self._test_alipay_feedback_processing()

    def _test_alipay_feedback_processing(self):
        # Unknown transaction
        with self.assertRaises(ValidationError):
            self.env['payment.transaction']._handle_notification_data(
                'alipay', self.notification_data
            )

        # Confirmed transaction
        tx = self._create_transaction('redirect')
        self.env['payment.transaction']._handle_notification_data('alipay', self.notification_data)
        self.assertEqual(tx.state, 'done')
        self.assertEqual(tx.provider_reference, self.notification_data['trade_no'])

        # Pending transaction
        self.reference = 'Test Transaction 2'
        tx = self._create_transaction('redirect')
        payload = dict(
            self.notification_data, out_trade_no=self.reference, trade_status='TRADE_CLOSED'
        )
        self.env['payment.transaction']._handle_notification_data('alipay', payload)
        self.assertEqual(tx.state, 'cancel')

    @mute_logger('odoo.addons.payment_alipay.controllers.main')
    def test_webhook_notification_confirms_transaction(self):
        """ Test the processing of a webhook notification. """
        self.provider.alipay_payment_method = 'standard_checkout'
        tx = self._create_transaction('redirect')
        url = self._build_url(AlipayController._webhook_url)
        with patch(
            'odoo.addons.payment_alipay.controllers.main.AlipayController'
            '._verify_notification_origin'
        ), patch(
            'odoo.addons.payment_alipay.controllers.main.AlipayController'
            '._verify_notification_signature'
        ):
            self._make_http_post_request(url, data=self.notification_data)
        self.assertEqual(tx.state, 'done')

    @mute_logger('odoo.addons.payment_alipay.controllers.main')
    def test_webhook_notification_triggers_origin_and_signature_checks(self):
        """ Test that receiving a webhook notification triggers origin and signature checks. """
        self.provider.alipay_payment_method = 'standard_checkout'
        self._create_transaction('redirect')
        url = self._build_url(AlipayController._webhook_url)
        with patch(
            'odoo.addons.payment_alipay.controllers.main.AlipayController'
            '._verify_notification_origin'
        ) as origin_check_mock, patch(
            'odoo.addons.payment_alipay.controllers.main.AlipayController'
            '._verify_notification_signature'
        ) as signature_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ):
            self._make_http_post_request(url, data=self.notification_data)
            self.assertEqual(origin_check_mock.call_count, 1)
            self.assertEqual(signature_check_mock.call_count, 1)

    def test_accept_notification_with_valid_signature(self):
        """ Test the verification of a notification with a valid signature. """
        tx = self._create_transaction('redirect')
        self._assert_does_not_raise(
            Forbidden, AlipayController._verify_notification_signature, self.notification_data, tx
        )

    @mute_logger('odoo.addons.payment_alipay.controllers.main')
    def test_reject_notification_with_missing_signature(self):
        """ Test the verification of a notification with a missing signature. """
        tx = self._create_transaction('redirect')
        payload = dict(self.notification_data, sign=None)
        self.assertRaises(Forbidden, AlipayController._verify_notification_signature, payload, tx)

    @mute_logger('odoo.addons.payment_alipay.controllers.main')
    def test_reject_notification_with_invalid_signature(self):
        """ Test the verification of a notification with an invalid signature. """
        tx = self._create_transaction('redirect')
        payload = dict(self.notification_data, sign='dummy')
        self.assertRaises(Forbidden, AlipayController._verify_notification_signature, payload, tx)
