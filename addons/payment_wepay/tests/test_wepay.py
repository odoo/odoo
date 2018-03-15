# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unittest

from odoo import fields
from odoo.tools import mute_logger
from odoo.addons.payment.tests.common import PaymentAcquirerCommon


class WePayTest(PaymentAcquirerCommon):

    def setUp(self):
        super(WePayTest, self).setUp()
        self.WePay = self.env.ref('payment.payment_acquirer_wepay')

    @unittest.skip("wepay test disabled: We do not want to overload wepay with runbot's requests")
    def test_10_WePay_s2s(self):
        self.assertEqual(self.WePay.environment, 'test', 'test without test environment')

        # Create payment meethod for wepay
        payment_token = self.env['payment.token'].create({
            'acquirer_id': self.WePay.id,
            'partner_id': self.buyer_id,
            'cc_number': '4242424242424242',
            'cc_expiry': '02 / 26',
            'cc_brand': 'visa',
            'cvc': '111',
            'cc_holder_name': 'Johndoe',
        })

        # Create transaction
        tx = self.env['payment.transaction'].create({
            'reference': 'test_ref_%s' % fields.date.today(),
            'currency_id': self.currency_euro.id,
            'acquirer_id': self.WePay.id,
            'partner_id': self.buyer_id,
            'payment_token_id': payment_token.id,
            'type': 'server2server',
            'amount': 115.0
        })
        tx.wepay_s2s_do_transaction()

        # Check transaction state
        self.assertEqual(tx.state, 'done', 'WePay: Transcation has been discarded.')

    @unittest.skip("wepay test disabled: We do not want to overload wepay with runbot's requests")
    def test_20_wepay_form_management(self):
        self.assertEqual(self.WePay.environment, 'test', 'test without test environment')

        # typical data posted by Wepay after client has successfully paid
        wepay_post_data = {
            'delivery_type': None,
            'hosted_checkout': {
                'theme_object': None,
                'shipping_address': None,
                'redirect_uri': 'http://localhost:8069/payment/wepay/dpn',
                'checkout_uri': 'https://stage.wepay.com/api/checkout/347035687/9c9a3548',
                'require_shipping': False,
                'mode': 'regular',
                'shipping_fee': 0,
                'auto_capture': True
            },
            'amount': 320.0,
            'state': 'authorized',
            'payment_method': None,
            'in_review': False,
            'callback_uri': 'http://localhost:8069/payment/wepay/ipn',
            'checkout_id': '347035687',
            'chargeback': {
                'dispute_uri': 'https://stage.wepay.com/dispute/payer_create/37813113/7640c38028a04c683667',
                'amount_charged_back': 0
            },
            'account_id': 12345,
            'npo_information': None,
            'payment_error': None,
            'short_description': 'Payment From Odoo E-commerce',
            'fee': {
                'fee_payer': 'payer',
                'processing_fee': 9.58,
                'app_fee': 0
            },
            'soft_descriptor': 'WPY*Individual',
            'refund': {
                'amount_refunded': 0,
                'refund_reason': None
            },
            'create_time': 1512975983,
            'type': 'goods',
            'reference_id': 'SO100',
            'currency': 'EUR',
            'gross': 329.58,
            'payer': {
                'home_address': None,
                'name': 'Administrator admin',
                'email': 'admin@yourcompany.example.com'}
        }

        tx = self.env['payment.transaction'].create({
            'amount': 320.0,
            'acquirer_id': self.WePay.id,
            'currency_id': self.currency_euro.id,
            'reference': 'SO100',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id})

        # validate tx
        tx.form_feedback(wepay_post_data, 'wepay')
        self.assertEqual(tx.state, 'done', 'Wepay: validation did not put tx into done state')
        self.assertEqual(tx.acquirer_reference, wepay_post_data.get('checkout_id'), 'Wepay: validation did not update tx id')
        # reset tx
        tx.write({'state': 'draft', 'date_validate': False, 'acquirer_reference': False})
        # simulate an error
        wepay_post_data['state'] = 'error'
        with mute_logger('odoo.addons.payment_wepay.models.payment'):
            tx.form_feedback(wepay_post_data, 'wepay')
        # check transaction state
        self.assertEqual(tx.state, 'error', 'Wepay: erroneous validation did not put tx into error state')
