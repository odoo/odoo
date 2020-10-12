# -*- coding: utf-8 -*-
import odoo
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from unittest.mock import patch
from . import stripe_mocks
from ..models.payment import STRIPE_SIGNATURE_AGE_TOLERANCE
from odoo.tools import mute_logger


class StripeCommon(PaymentAcquirerCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.stripe = cls.env.ref('payment.payment_acquirer_stripe')
        cls.stripe.write({
            'stripe_secret_key': 'sk_test_KJtHgNwt2KS3xM7QJPr4O5E8',
            'stripe_publishable_key': 'pk_test_QSPnimmb4ZhtkEy3Uhdm4S6J',
            'stripe_webhook_secret': 'whsec_vG1fL6CMUouQ7cObF2VJprLVXT5jBLxB',
            'state': 'test',
        })
        cls.token = cls.env['payment.token'].create({
            'name': 'Test Card',
            'acquirer_id': cls.stripe.id,
            'acquirer_ref': 'cus_G27S7FqQ2w3fuH',
            'stripe_payment_method': 'pm_1FW3DdAlCFm536g8eQoSCejY',
            'partner_id': cls.buyer.id,
            'verified': True,
        })
        cls.ideal_icon = cls.env.ref("payment.payment_icon_cc_ideal")
        cls.bancontact_icon = cls.env.ref("payment.payment_icon_cc_bancontact")
        cls.p24_icon = cls.env.ref("payment.payment_icon_cc_p24")
        cls.eps_icon = cls.env.ref("payment.payment_icon_cc_eps")
        cls.giropay_icon = cls.env.ref("payment.payment_icon_cc_giropay")
        cls.all_icons = [cls.ideal_icon, cls.bancontact_icon, cls.p24_icon, cls.eps_icon, cls.giropay_icon]
        cls.stripe.write({'payment_icon_ids': [(5, 0, 0)]})


@odoo.tests.tagged('post_install', '-at_install', '-standard', 'external')
class StripeTest(StripeCommon):

    def run(self, result=None):
        with mute_logger('odoo.addons.payment.models.payment_acquirer', 'odoo.addons.payment_stripe.models.payment'):
            StripeCommon.run(self, result)

    def test_10_stripe_s2s(self):
        self.assertEqual(self.stripe.state, 'test', 'test without test environment')
        # Create transaction
        tx = self.env['payment.transaction'].create({
            'reference': 'stripe_test_10_%s' % fields.datetime.now().strftime('%Y%m%d_%H%M%S'),
            'currency_id': self.currency_euro.id,
            'acquirer_id': self.stripe.id,
            'partner_id': self.buyer_id,
            'payment_token_id': self.token.id,
            'type': 'server2server',
            'amount': 115.0
        })
        tx.with_context(off_session=True).stripe_s2s_do_transaction()

        # Check state
        self.assertEqual(tx.state, 'done', 'Stripe: Transcation has been discarded.')

    def test_20_stripe_form_render(self):
        self.assertEqual(self.stripe.state, 'test', 'test without test environment')

        # ----------------------------------------
        # Test: button direct rendering
        # ----------------------------------------

        # render the button
        self.stripe.render('SO404', 320.0, self.currency_euro.id, values=self.buyer_values).decode('utf-8')

    def test_30_stripe_form_management(self):
        self.assertEqual(self.stripe.state, 'test', 'test without test environment')
        ref = 'stripe_test_30_%s' % fields.datetime.now().strftime('%Y%m%d_%H%M%S')
        tx = self.env['payment.transaction'].create({
            'amount': 4700.0,
            'acquirer_id': self.stripe.id,
            'currency_id': self.currency_euro.id,
            'reference': ref,
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id,
            'payment_token_id': self.token.id,
        })
        res = tx.with_context(off_session=True)._stripe_create_payment_intent()
        tx.stripe_payment_intent = res.get('payment_intent')

        # typical data posted by Stripe after client has successfully paid
        stripe_post_data = {'reference': ref}
        # validate it
        tx.form_feedback(stripe_post_data, 'stripe')
        self.assertEqual(tx.state, 'done', 'Stripe: validation did not put tx into done state')
        self.assertEqual(tx.acquirer_reference, stripe_post_data.get('id'), 'Stripe: validation did not update tx id')

    def test_add_available_payment_method_types_local_enabled(self):
        self.stripe.payment_icon_ids = [(6, 0, [i.id for i in self.all_icons])]
        tx_values = {
            'billing_partner_country': self.env.ref('base.be'),
            'currency': self.env.ref('base.EUR'),
            'type': 'form'
        }
        stripe_session_data = {}

        self.stripe._add_available_payment_method_types(stripe_session_data, tx_values)

        actual = {pmt for key, pmt in stripe_session_data.items() if key.startswith('payment_method_types')}
        self.assertEqual({'card', 'bancontact'}, actual)

    def test_add_available_payment_method_types_local_enabled_2(self):
        self.stripe.payment_icon_ids = [(6, 0, [i.id for i in self.all_icons])]
        tx_values = {
            'billing_partner_country': self.env.ref('base.pl'),
            'currency': self.env.ref('base.PLN'),
            'type': 'form'
        }
        stripe_session_data = {}

        self.stripe._add_available_payment_method_types(stripe_session_data, tx_values)

        actual = {pmt for key, pmt in stripe_session_data.items() if key.startswith('payment_method_types')}
        self.assertEqual({'card', 'p24'}, actual)

    def test_add_available_payment_method_types_pmt_does_not_exist(self):
        self.bancontact_icon.unlink()
        tx_values = {
            'billing_partner_country': self.env.ref('base.be'),
            'currency': self.env.ref('base.EUR'),
            'type': 'form'
        }
        stripe_session_data = {}

        self.stripe._add_available_payment_method_types(stripe_session_data, tx_values)

        actual = {pmt for key, pmt in stripe_session_data.items() if key.startswith('payment_method_types')}
        self.assertEqual({'card', 'bancontact'}, actual)

    def test_add_available_payment_method_types_local_disabled(self):
        tx_values = {
            'billing_partner_country': self.env.ref('base.be'),
            'currency': self.env.ref('base.EUR'),
            'type': 'form'
        }
        stripe_session_data = {}

        self.stripe._add_available_payment_method_types(stripe_session_data, tx_values)

        actual = {pmt for key, pmt in stripe_session_data.items() if key.startswith('payment_method_types')}
        self.assertEqual({'card'}, actual)

    def test_add_available_payment_method_types_local_all_but_bancontact(self):
        self.stripe.payment_icon_ids = [(4, icon.id) for icon in self.all_icons if icon.name.lower() != 'bancontact']
        tx_values = {
            'billing_partner_country': self.env.ref('base.be'),
            'currency': self.env.ref('base.EUR'),
            'type': 'form'
        }
        stripe_session_data = {}

        self.stripe._add_available_payment_method_types(stripe_session_data, tx_values)

        actual = {pmt for key, pmt in stripe_session_data.items() if key.startswith('payment_method_types')}
        self.assertEqual({'card'}, actual)

    def test_add_available_payment_method_types_recurrent(self):
        tx_values = {
            'billing_partner_country': self.env.ref('base.be'),
            'currency': self.env.ref('base.EUR'),
            'type': 'form_save'
        }
        stripe_session_data = {}

        self.stripe._add_available_payment_method_types(stripe_session_data, tx_values)

        actual = {pmt for key, pmt in stripe_session_data.items() if key.startswith('payment_method_types')}
        self.assertEqual({'card'}, actual)

    def test_discarded_webhook(self):
        self.assertFalse(self.env['payment.acquirer']._handle_stripe_webhook(dict(type='payment.intent.succeeded')))

    def test_handle_checkout_webhook_no_secret(self):
        self.stripe.stripe_webhook_secret = None

        with self.assertRaises(ValidationError):
            self.env['payment.acquirer']._handle_stripe_webhook(dict(type='checkout.session.completed'))

    @patch('odoo.addons.payment_stripe.models.payment.request')
    @patch('odoo.addons.payment_stripe.models.payment.datetime')
    def test_handle_checkout_webhook(self, dt, request):
        # pass signature verification
        dt.utcnow.return_value.timestamp.return_value = 1591264652
        request.httprequest.headers = {'Stripe-Signature': stripe_mocks.checkout_session_signature}
        request.httprequest.data = stripe_mocks.checkout_session_body
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
        res = tx.with_context(off_session=True)._stripe_create_payment_intent()
        tx.stripe_payment_intent = res.get('payment_intent')
        stripe_object = stripe_mocks.checkout_session_object

        actual = self.stripe._handle_checkout_webhook(stripe_object)

        self.assertTrue(actual)

    @patch('odoo.addons.payment_stripe.models.payment.request')
    @patch('odoo.addons.payment_stripe.models.payment.datetime')
    def test_handle_checkout_webhook_wrong_amount(self, dt, request):
        # pass signature verification
        dt.utcnow.return_value.timestamp.return_value = 1591264652
        request.httprequest.headers = {'Stripe-Signature': stripe_mocks.checkout_session_signature}
        request.httprequest.data = stripe_mocks.checkout_session_body
        # test setup
        bad_tx = self.env['payment.transaction'].create({
            'reference': 'tx_ref_test_handle_checkout_webhook_wrong_amount',
            'currency_id': self.currency_euro.id,
            'acquirer_id': self.stripe.id,
            'partner_id': self.buyer_id,
            'payment_token_id': self.token.id,
            'type': 'server2server',
            'amount': 10
        })
        wrong_amount_stripe_payment_intent = bad_tx.with_context(off_session=True)._stripe_create_payment_intent()
        tx = self.env['payment.transaction'].create({
            'reference': 'tx_ref_test_handle_checkout_webhook',
            'currency_id': self.currency_euro.id,
            'acquirer_id': self.stripe.id,
            'partner_id': self.buyer_id,
            'payment_token_id': self.token.id,
            'type': 'server2server',
            'amount': 30
        })
        tx.stripe_payment_intent = wrong_amount_stripe_payment_intent.get('payment_intent')
        stripe_object = stripe_mocks.checkout_session_object

        actual = self.env['payment.acquirer']._handle_checkout_webhook(stripe_object)

        self.assertFalse(actual)

    def test_handle_checkout_webhook_no_odoo_tx(self):
        stripe_object = stripe_mocks.checkout_session_object

        actual = self.stripe._handle_checkout_webhook(stripe_object)

        self.assertFalse(actual)

    @patch('odoo.addons.payment_stripe.models.payment.request')
    @patch('odoo.addons.payment_stripe.models.payment.datetime')
    def test_handle_checkout_webhook_no_stripe_tx(self, dt, request):
        # pass signature verification
        dt.utcnow.return_value.timestamp.return_value = 1591264652
        request.httprequest.headers = {'Stripe-Signature': stripe_mocks.checkout_session_signature}
        request.httprequest.data = stripe_mocks.checkout_session_body
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

    @patch('odoo.addons.payment_stripe.models.payment.request')
    @patch('odoo.addons.payment_stripe.models.payment.datetime')
    def test_verify_stripe_signature(self, dt, request):
        dt.utcnow.return_value.timestamp.return_value = 1591264652
        request.httprequest.headers = {'Stripe-Signature': stripe_mocks.checkout_session_signature}
        request.httprequest.data = stripe_mocks.checkout_session_body

        actual = self.stripe._verify_stripe_signature()

        self.assertTrue(actual)

    @patch('odoo.addons.payment_stripe.models.payment.request')
    @patch('odoo.addons.payment_stripe.models.payment.datetime')
    def test_verify_stripe_signature_tampered_body(self, dt, request):
        dt.utcnow.return_value.timestamp.return_value = 1591264652
        request.httprequest.headers = {'Stripe-Signature': stripe_mocks.checkout_session_signature}
        request.httprequest.data = stripe_mocks.checkout_session_body.replace(b'1500', b'10')

        with self.assertRaises(ValidationError):
            self.stripe._verify_stripe_signature()

    @patch('odoo.addons.payment_stripe.models.payment.request')
    @patch('odoo.addons.payment_stripe.models.payment.datetime')
    def test_verify_stripe_signature_wrong_secret(self, dt, request):
        dt.utcnow.return_value.timestamp.return_value = 1591264652
        request.httprequest.headers = {'Stripe-Signature': stripe_mocks.checkout_session_signature}
        request.httprequest.data = stripe_mocks.checkout_session_body
        self.stripe.write({
            'stripe_webhook_secret': 'whsec_vG1fL6CMUouQ7cObF2VJprL_TAMPERED',
        })

        with self.assertRaises(ValidationError):
            self.stripe._verify_stripe_signature()

    @patch('odoo.addons.payment_stripe.models.payment.request')
    @patch('odoo.addons.payment_stripe.models.payment.datetime')
    def test_verify_stripe_signature_too_old(self, dt, request):
        dt.utcnow.return_value.timestamp.return_value = 1591264652 + STRIPE_SIGNATURE_AGE_TOLERANCE + 1
        request.httprequest.headers = {'Stripe-Signature': stripe_mocks.checkout_session_signature}
        request.httprequest.data = stripe_mocks.checkout_session_body

        with self.assertRaises(ValidationError):
            self.stripe._verify_stripe_signature()
