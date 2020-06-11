# -*- coding: utf-8 -*-
import odoo
from odoo import fields
from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from odoo.tools import mute_logger


class StripeCommon(PaymentAcquirerCommon):

    def setUp(self):
        super(StripeCommon, self).setUp()
        self.stripe = self.env.ref('payment.payment_acquirer_stripe')
        self.stripe.write({
            'stripe_secret_key': 'sk_test_KJtHgNwt2KS3xM7QJPr4O5E8',
            'stripe_publishable_key': 'pk_test_QSPnimmb4ZhtkEy3Uhdm4S6J',
            'state': 'test',
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

    def test_add_available_payment_method_types(self):
        tx_values = {
            'billing_partner_country': self.env.ref('base.be'),
            'currency': self.env.ref('base.EUR'),
            'type': 'form'
        }
        stripe_session_data = {}

        self.stripe._add_available_payment_method_types(stripe_session_data, tx_values)

        actual = {pmt for key, pmt in stripe_session_data.items() if key.startswith('payment_method_types')}
        self.assertEqual({'card', 'bancontact'}, actual)

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
