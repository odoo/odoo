# -*- coding: utf-8 -*-
from unittest.mock import patch

import odoo
from odoo.tools import mute_logger
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from . import stripe_mocks
from ..models.payment import STRIPE_SIGNATURE_AGE_TOLERANCE


class StripeCommon(PaymentAcquirerCommon):

    def setUp(self):
        super(StripeCommon, self).setUp()
        self.stripe = self.env.ref('payment.payment_acquirer_stripe')
        self.stripe.write({
            'stripe_secret_key': 'sk_test_KJtHgNwt2KS3xM7QJPr4O5E8',
            'stripe_publishable_key': 'pk_test_QSPnimmb4ZhtkEy3Uhdm4S6J',
            'stripe_webhook_secret': 'whsec_vG1fL6CMUouQ7cObF2VJprLVXT5jBLxB',
        })
        self.token = self.env['payment.token'].create({
            'name': 'Test Card',
            'acquirer_id': self.stripe.id,
            'acquirer_ref': 'cus_G27S7FqQ2w3fuH',
            'stripe_payment_method': 'pm_1FW3DdAlCFm536g8eQoSCejY',
            'partner_id': self.buyer.id,
            'verified': True,
        })


@odoo.tests.tagged('post_install', '-at_install', '-standard', 'external')
class StripeTest(StripeCommon):

    def test_discarded_webhook(self):
        self.assertFalse(self.env['payment.acquirer']._handle_stripe_webhook(dict(type='payment.intent.succeeded')))

    def test_handle_checkout_webhook_no_secret(self):
        self.stripe.stripe_webhook_secret = None

        with self.assertRaises(ValidationError):
            self.env['payment.acquirer']._handle_stripe_webhook(dict(type='checkout.session.completed'))

    @mute_logger('odoo.addons.payment_stripe.models.payment')
    @patch('odoo.addons.payment_stripe_checkout_webhook.models.payment.requests')
    @patch('odoo.addons.payment_stripe_checkout_webhook.models.payment.request')
    @patch('odoo.addons.payment_stripe_checkout_webhook.models.payment.datetime')
    def test_handle_checkout_webhook(self, dt, ch_request, tx_request):
        # pass signature verification
        dt.utcnow.return_value.timestamp.return_value = 1591264652
        ch_request.httprequest.headers = {'Stripe-Signature': stripe_mocks.checkout_session_signature}
        ch_request.httprequest.data = stripe_mocks.checkout_session_body
        # test setup
        tx = self.env['payment.transaction'].create({
            'reference': 'tx_ref_test_handle_checkout_webhook',
            'currency_id': self.currency_euro.id,
            'acquirer_id': self.stripe.id,
            'partner_id': self.buyer_id,
            'payment_token_id': self.token.id,
            'type': 'server2server',
            'amount': 30
        })
        tx.stripe_payment_intent = 'pi_1GptaRAlCFm536g8AfCF6Zi0'
        stripe_object = stripe_mocks.checkout_session_object
        tx_request.request.return_value = stripe_mocks.ok_tx_resp

        actual = self.stripe._handle_checkout_webhook(stripe_object)

        self.assertTrue(actual)

    @mute_logger('odoo.addons.payment_stripe.models.payment')
    @mute_logger('odoo.addons.payment.models.payment_acquirer')
    @patch('odoo.addons.payment_stripe_checkout_webhook.models.payment.requests')
    @patch('odoo.addons.payment_stripe_checkout_webhook.models.payment.request')
    @patch('odoo.addons.payment_stripe_checkout_webhook.models.payment.datetime')
    def test_handle_checkout_webhook_wrong_amount(self, dt, ch_request, tx_request):
        # pass signature verification
        dt.utcnow.return_value.timestamp.return_value = 1591264652
        ch_request.httprequest.headers = {'Stripe-Signature': stripe_mocks.checkout_session_signature}
        ch_request.httprequest.data = stripe_mocks.checkout_session_body
        # mocking stripe tx
        tx_request.request.return_value = stripe_mocks.wrong_amount_tx_resp

        # test setup
        # tx that corresponds to the payment_intent
        bad_tx = self.env['payment.transaction'].create({
            'reference': 'tx_ref_test_handle_checkout_webhook_wrong_amount',
            'currency_id': self.currency_euro.id,
            'acquirer_id': self.stripe.id,
            'partner_id': self.buyer_id,
            'payment_token_id': self.token.id,
            'type': 'server2server',
            'amount': 10
        })
        # tx that corresponds to the client_reference_id (our internal reference)
        tx = self.env['payment.transaction'].create({
            'reference': 'tx_ref_test_handle_checkout_webhook',
            'currency_id': self.currency_euro.id,
            'acquirer_id': self.stripe.id,
            'partner_id': self.buyer_id,
            'payment_token_id': self.token.id,
            'type': 'server2server',
            'amount': 30
        })
        # stripe_payment_intent won't match stripe mock object "from" Stripe.
        tx.stripe_payment_intent = stripe_mocks.wrong_amount_tx_resp.json()['id']
        stripe_object = stripe_mocks.checkout_session_object

        actual = self.env['payment.acquirer']._handle_checkout_webhook(stripe_object)

        self.assertFalse(actual)

    @mute_logger('odoo.addons.payment_stripe.models.payment')
    def test_handle_checkout_webhook_no_odoo_tx(self):
        stripe_object = stripe_mocks.checkout_session_object

        actual = self.stripe._handle_checkout_webhook(stripe_object)

        self.assertFalse(actual)

    @patch('odoo.addons.payment_stripe_checkout_webhook.models.payment.requests')
    @patch('odoo.addons.payment_stripe_checkout_webhook.models.payment.request')
    @patch('odoo.addons.payment_stripe_checkout_webhook.models.payment.datetime')
    def test_handle_checkout_webhook_no_stripe_tx(self, dt, ch_request, tx_request):
        # pass signature verification
        dt.utcnow.return_value.timestamp.return_value = 1591264652
        ch_request.httprequest.headers = {'Stripe-Signature': stripe_mocks.checkout_session_signature}
        ch_request.httprequest.data = stripe_mocks.checkout_session_body
        # mock stripe api
        tx_request.request.return_value = stripe_mocks.missing_tx_resp
        # test setup
        self.env['payment.transaction'].create({
            'reference': 'tx_ref_test_handle_checkout_webhook',
            'currency_id': self.currency_euro.id,
            'acquirer_id': self.stripe.id,
            'partner_id': self.buyer_id,
            'payment_token_id': self.token.id,
            'type': 'server2server',
            'amount': 30
        })
        stripe_object = stripe_mocks.checkout_session_object

        with self.assertRaises(ValidationError):
            self.stripe._handle_checkout_webhook(stripe_object)

    @patch('odoo.addons.payment_stripe_checkout_webhook.models.payment.request')
    @patch('odoo.addons.payment_stripe_checkout_webhook.models.payment.datetime')
    def test_verify_stripe_signature(self, dt, request):
        dt.utcnow.return_value.timestamp.return_value = 1591264652
        request.httprequest.headers = {'Stripe-Signature': stripe_mocks.checkout_session_signature}
        request.httprequest.data = stripe_mocks.checkout_session_body

        actual = self.stripe._verify_stripe_signature()

        self.assertTrue(actual)

    @mute_logger('odoo.addons.payment_stripe_checkout_webhook.models.payment')
    @patch('odoo.addons.payment_stripe_checkout_webhook.models.payment.request')
    @patch('odoo.addons.payment_stripe_checkout_webhook.models.payment.datetime')
    def test_verify_stripe_signature_tampered_body(self, dt, request):
        dt.utcnow.return_value.timestamp.return_value = 1591264652
        request.httprequest.headers = {'Stripe-Signature': stripe_mocks.checkout_session_signature}
        request.httprequest.data = stripe_mocks.checkout_session_body.replace(b'1500', b'10')

        with self.assertRaises(ValidationError):
            self.stripe._verify_stripe_signature()

    @mute_logger('odoo.addons.payment_stripe_checkout_webhook.models.payment')
    @patch('odoo.addons.payment_stripe_checkout_webhook.models.payment.request')
    @patch('odoo.addons.payment_stripe_checkout_webhook.models.payment.datetime')
    def test_verify_stripe_signature_wrong_secret(self, dt, request):
        dt.utcnow.return_value.timestamp.return_value = 1591264652
        request.httprequest.headers = {'Stripe-Signature': stripe_mocks.checkout_session_signature}
        request.httprequest.data = stripe_mocks.checkout_session_body
        self.stripe.write({
            'stripe_webhook_secret': 'whsec_vG1fL6CMUouQ7cObF2VJprL_TAMPERED',
        })

        with self.assertRaises(ValidationError):
            self.stripe._verify_stripe_signature()

    @mute_logger('odoo.addons.payment_stripe_checkout_webhook.models.payment')
    @patch('odoo.addons.payment_stripe_checkout_webhook.models.payment.request')
    @patch('odoo.addons.payment_stripe_checkout_webhook.models.payment.datetime')
    def test_verify_stripe_signature_too_old(self, dt, request):
        dt.utcnow.return_value.timestamp.return_value = 1591264652 + STRIPE_SIGNATURE_AGE_TOLERANCE + 1
        request.httprequest.headers = {'Stripe-Signature': stripe_mocks.checkout_session_signature}
        request.httprequest.data = stripe_mocks.checkout_session_body

        with self.assertRaises(ValidationError):
            self.stripe._verify_stripe_signature()
