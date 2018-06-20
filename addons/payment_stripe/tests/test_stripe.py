# -*- coding: utf-8 -*-
import unittest
import odoo
from odoo import fields
from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from odoo.tools import mute_logger


@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(True)
class StripeCommon(PaymentAcquirerCommon):

    def setUp(self):
        super(StripeCommon, self).setUp()
        self.stripe = self.env.ref('payment.payment_acquirer_stripe')


@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(True)
class StripeTest(StripeCommon):

    @unittest.skip("Stripe test disabled: We do not want to overload Stripe with runbot's requests")
    def test_10_stripe_s2s(self):
        self.assertEqual(self.stripe.environment, 'test', 'test without test environment')

        # Add Stripe credentials
        self.stripe.write({
            'stripe_secret_key': 'sk_test_bldAlqh1U24L5HtRF9mBFpK7',
            'stripe_publishable_key': 'pk_test_0TKSyYSZS9AcS4keZ2cxQQCW',
        })

        # Create payment meethod for Stripe
        payment_token = self.env['payment.token'].create({
            'acquirer_id': self.stripe.id,
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
            'acquirer_id': self.stripe.id,
            'partner_id': self.buyer_id,
            'payment_token_id': payment_token.id,
            'type': 'server2server',
            'amount': 115.0
        })
        tx.stripe_s2s_do_transaction()

        # Check state
        self.assertEqual(tx.state, 'done', 'Stripe: Transcation has been discarded.')

    @unittest.skip("Stripe test disabled: We do not want to overload Stripe with runbot's requests")
    def test_20_stripe_form_render(self):
        self.assertEqual(self.stripe.environment, 'test', 'test without test environment')

        # ----------------------------------------
        # Test: button direct rendering
        # ----------------------------------------

        # render the button
        res = self.stripe.render('SO404', 320.0, self.currency_euro.id, values=self.buyer_values).decode('utf-8')
        popup_script_src = 'script src="https://checkout.stripe.com/checkout.js"'
        # check form result
        self.assertIn(popup_script_src, res, "Stripe: popup script not found in template render")
        # Generated and received
        self.assertIn(self.buyer_values.get('partner_email'), res, 'Stripe: email input not found in rendered template')

    @unittest.skip("Stripe test disabled: We do not want to overload Stripe with runbot's requests")
    def test_30_stripe_form_management(self):
        self.assertEqual(self.stripe.environment, 'test', 'test without test environment')

        # typical data posted by Stripe after client has successfully paid
        stripe_post_data = {
            u'amount': 4700,
            u'amount_refunded': 0,
            u'application_fee': None,
            u'balance_transaction': u'txn_172xfnGMfVJxozLwssrsQZyT',
            u'captured': True,
            u'created': 1446529775,
            u'currency': u'eur',
            u'customer': None,
            u'description': None,
            u'destination': None,
            u'dispute': None,
            u'failure_code': None,
            u'failure_message': None,
            u'fraud_details': {},
            u'id': u'ch_172xfnGMfVJxozLwEjSfpfxD',
            u'invoice': None,
            u'livemode': False,
            u'metadata': {u'reference': u'SO100'},
            u'object': u'charge',
            u'paid': True,
            u'receipt_email': None,
            u'receipt_number': None,
            u'refunded': False,
            u'refunds': {u'data': [],
                         u'has_more': False,
                         u'object': u'list',
                         u'total_count': 0,
                         u'url': u'/v1/charges/ch_172xfnGMfVJxozLwEjSfpfxD/refunds'},
            u'shipping': None,
            u'source': {u'address_city': None,
                        u'address_country': None,
                        u'address_line1': None,
                        u'address_line1_check': None,
                        u'address_line2': None,
                        u'address_state': None,
                        u'address_zip': None,
                        u'address_zip_check': None,
                        u'brand': u'Visa',
                        u'country': u'US',
                        u'customer': None,
                        u'cvc_check': u'pass',
                        u'dynamic_last4': None,
                        u'exp_month': 2,
                        u'exp_year': 2022,
                        u'fingerprint': u'9tJA9bUEuvEb3Ell',
                        u'funding': u'credit',
                        u'id': u'card_172xfjGMfVJxozLw1QO6gYNM',
                        u'last4': u'4242',
                        u'metadata': {},
                        u'name': u'norbert.buyer@example.com',
                        u'object': u'card',
                        u'tokenization_method': None},
            u'statement_descriptor': None,
            u'status': u'succeeded'}

        tx = self.env['payment.transaction'].create({
            'amount': 4700,
            'acquirer_id': self.stripe.id,
            'currency_id': self.currency_euro.id,
            'reference': 'SO100',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id})

        # validate it
        tx.form_feedback(stripe_post_data, 'stripe')
        self.assertEqual(tx.state, 'done', 'Stripe: validation did not put tx into done state')
        self.assertEqual(tx.acquirer_reference, stripe_post_data.get('id'), 'Stripe: validation did not update tx id')
        # reset tx
        tx.write({'state': 'draft', 'date_validate': False, 'acquirer_reference': False})
        # simulate an error
        stripe_post_data['status'] = 'error'
        stripe_post_data.update({u'error': {u'message': u"Your card's expiration year is invalid.", u'code': u'invalid_expiry_year', u'type': u'card_error', u'param': u'exp_year'}})
        with mute_logger('odoo.addons.payment_stripe.models.payment'):
            tx.form_feedback(stripe_post_data, 'stripe')
        # check state
        self.assertEqual(tx.state, 'error', 'Stipe: erroneous validation did not put tx into error state')
