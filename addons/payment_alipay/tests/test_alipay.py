# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import AlipayCommon
from ..controllers.main import AlipayController


@tagged('post_install', '-at_install')
class AlipayTest(AlipayCommon):

    def test_compatible_acquirers(self):
        self.alipay.alipay_payment_method = 'express_checkout'
        acquirers = self.env['payment.acquirer']._get_compatible_acquirers(
            partner_id=self.partner.id,
            currency_id=self.currency_yuan.id, # 'CNY'
            company_id=self.company.id,
        )
        self.assertIn(self.alipay, acquirers)
        acquirers = self.env['payment.acquirer']._get_compatible_acquirers(
            partner_id=self.partner.id,
            currency_id=self.currency_euro.id,
            company_id=self.company.id,
        )
        self.assertNotIn(self.alipay, acquirers)

        self.alipay.alipay_payment_method = 'standard_checkout'
        acquirers = self.env['payment.acquirer']._get_compatible_acquirers(
            partner_id=self.partner.id,
            currency_id=self.currency_yuan.id, # 'CNY'
            company_id=self.company.id,
        )
        self.assertIn(self.alipay, acquirers)
        acquirers = self.env['payment.acquirer']._get_compatible_acquirers(
            partner_id=self.partner.id,
            currency_id=self.currency_euro.id,
            company_id=self.company.id,
        )
        self.assertIn(self.alipay, acquirers)

    def test_01_redirect_form_standard_checkout(self):
        self.alipay.alipay_payment_method = 'standard_checkout'
        self._test_alipay_redirect_form()

    def test_02_redirect_form_express_checkout(self):
        self.alipay.alipay_payment_method = 'express_checkout'
        self._test_alipay_redirect_form()

    def _test_alipay_redirect_form(self):
        tx = self.create_transaction(flow='redirect') # Only flow implemented

        expected_values = {
            '_input_charset': 'utf-8',
            'notify_url': self._build_url(AlipayController._notify_url),
            'out_trade_no': self.reference,
            'partner': self.alipay.alipay_merchant_partner_id,
            'return_url': self._build_url(AlipayController._return_url),
            'subject': self.reference,
            'total_fee': str(self.amount), # Fees disabled by default
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
        sign = self.alipay._alipay_build_sign(expected_values)

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
        # update acquirer: compute fees
        self.alipay.write({
            'fees_active': True,
            'fees_dom_fixed': 1.0,
            'fees_dom_var': 0.35,
            'fees_int_fixed': 1.5,
            'fees_int_var': 0.50,
        })

        transaction_fees = self.currency.round(
            self.alipay._compute_fees(
                self.amount,
                self.currency,
                self.partner.country_id,
            )
        )
        self.assertEqual(transaction_fees, 7.09)
        total_fee = self.currency.round(self.amount + transaction_fees)
        self.assertEqual(total_fee, 1118.2)

        tx = self.create_transaction(flow='redirect')
        self.assertEqual(tx.fees, 7.09)
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = tx._get_processing_values()
        redirect_form_data = self._extract_values_from_html_form(processing_values['redirect_form_html'])

        self.assertEqual(redirect_form_data['inputs']['total_fee'], str(total_fee))

    def test_21_standard_checkout_feedback(self):
        self.alipay.alipay_payment_method = 'standard_checkout'
        self.currency = self.currency_euro
        self._test_alipay_feedback_processing()

    def test_22_express_checkout_feedback(self):
        self.alipay.alipay_payment_method = 'express_checkout'
        self.currency = self.currency_yuan
        self._test_alipay_feedback_processing()

    def _test_alipay_feedback_processing(self):
        # typical data posted by alipay after client has successfully paid
        custom_reference = 'test_ref_' + self.alipay.alipay_payment_method
        alipay_post_data = {
            'trade_no': '2017112321001003690200384552',
            'reference': custom_reference,
            'total_fee': 1.95,
            'trade_status': 'TRADE_CLOSED',
        }

        if self.alipay.alipay_payment_method == 'express_checkout':
            alipay_post_data.update({
                'seller_email': self.alipay.alipay_seller_email,
            })
        else:
            alipay_post_data.update({
                'currency': 'EUR',
            })

        alipay_post_data['sign'] = self.alipay._alipay_build_sign(alipay_post_data)
        with self.assertRaises(ValidationError): # unknown transactiion
            self.env['payment.transaction']._handle_feedback_data('alipay', alipay_post_data)

        tx = self.env['payment.transaction'].create({
            'amount': 1.95,
            'acquirer_id': self.alipay.id,
            'currency_id': self.currency.id,
            'reference': custom_reference,
            'partner_id': self.partner.id
        })

        self.env['payment.transaction']._handle_feedback_data('alipay', alipay_post_data)
        self.assertEqual(tx.state, 'cancel',
            'Alipay: wrong state after receiving a valid pending notification')
        self.assertEqual(tx.acquirer_reference, '2017112321001003690200384552',
            'Alipay: wrong txn_id after receiving a valid pending notification')

        # reset the transaction
        tx.write({'state': 'draft', 'acquirer_reference': False})

        # update notification from alipay should not go through since it has already been set as 'done'
        if self.alipay.alipay_payment_method == 'standard_checkout':
            alipay_post_data['trade_status'] = 'TRADE_FINISHED'
        else:
            alipay_post_data['trade_status'] = 'TRADE_SUCCESS'
        alipay_post_data['sign'] = self.alipay._alipay_build_sign(alipay_post_data)

        self.env['payment.transaction']._handle_feedback_data('alipay', alipay_post_data)
        self.assertEqual(tx.acquirer_reference, '2017112321001003690200384552',
            'Alipay: notification should not go throught since it has already been validated')

        # this time it should go through since the transaction is not validated yet
        tx.write({'state': 'draft', 'acquirer_reference': False})
        self.env['payment.transaction']._handle_feedback_data('alipay', alipay_post_data)
        self.assertEqual(tx.state, 'done',
            'Alipay: wrong state after receiving a valid pending notification')
        self.assertEqual(tx.acquirer_reference, '2017112321001003690200384552',
            'Alipay: wrong txn_id after receiving a valid pending notification')
