from .test_stripe import StripeCommon

from ..models.stripe_request import StripeApi

import odoo
from odoo.tools import mute_logger


@odoo.tests.tagged('post_install', '-at_install', '-standard', 'external')
class StripeRequestTest(StripeCommon):
    def setUp(self):
        StripeCommon.setUp(self)
        self.api = StripeApi(self.stripe)

    def run(self, result=None):
        with mute_logger('odoo.addons.payment_stripe.models.stripe_request'):
            StripeCommon.run(self, result)

    def test_create_payment_intent(self):
        tx = self.env['payment.transaction'].create({
            'amount': 4700.0,
            'acquirer_id': self.stripe.id,
            'currency_id': self.currency_euro.id,
            'reference': 'tx_test_create_payment_intent',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id,
            'payment_token_id': self.token.id,
        })

        actual = self.api.create_payment_intent(tx.with_context(off_session=True))

        self.assertEqual(actual['object'], 'payment_intent')
        self.assertEqual(actual['amount'], 470000)
        self.assertEqual(actual['amount_capturable'], 0)
        self.assertEqual(actual['amount_received'], 470000)
        self.assertEqual(actual['capture_method'], 'automatic')

    def test_authorize_payment_intent(self):
        tx = self.env['payment.transaction'].create({
            'amount': 4700.0,
            'acquirer_id': self.stripe.id,
            'currency_id': self.currency_euro.id,
            'reference': 'tx_test_create_payment_intent',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id,
            'payment_token_id': self.token.id,
        })

        actual = self.api.create_payment_intent(tx.with_context(off_session=True), capture_method='manual')

        self.assertEqual(actual['object'], 'payment_intent')
        self.assertEqual(actual['amount'], 470000)
        self.assertEqual(actual['amount_capturable'], 470000)
        self.assertEqual(actual['amount_received'], 0)
        self.assertEqual(actual['capture_method'], 'manual')

    def test_capture_payment_intent(self):
        tx = self.env['payment.transaction'].create({
            'amount': 4700.0,
            'acquirer_id': self.stripe.id,
            'currency_id': self.currency_euro.id,
            'reference': 'tx_test_create_payment_intent',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id,
            'payment_token_id': self.token.id,
        })
        self.stripe.capture_manually = True
        tx.stripe_s2s_do_transaction()

        actual = self.api.capture_payment_intent(tx)

        self.assertEqual(actual['object'], 'payment_intent')
        self.assertEqual(actual['amount'], 470000)
        self.assertEqual(actual['amount_capturable'], 0)
        self.assertEqual(actual['amount_received'], 470000)
        self.assertEqual(actual['capture_method'], 'manual')

    def test_create_refund(self):
        tx = self.env['payment.transaction'].create({
            'amount': 4700.0,
            'acquirer_id': self.stripe.id,
            'currency_id': self.currency_euro.id,
            'reference': 'tx_test_create_payment_intent',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id,
            'payment_token_id': self.token.id,
        })
        tx.stripe_s2s_do_transaction()

        actual = self.api.create_refund(tx)

        self.assertEqual(actual['object'], 'refund')
        self.assertEqual(actual['amount'], 470000)
        self.assertEqual(actual['metadata']['reference'], tx.reference)
        self.assertEqual(actual['status'], 'succeeded')

    def test_create_setup_intent(self):
        actual = self.api.create_setup_intent()

        self.assertEqual(actual['object'], 'setup_intent')
