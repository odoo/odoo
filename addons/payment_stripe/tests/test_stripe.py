# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment_stripe.controllers.onboarding import OnboardingController
from odoo.addons.payment_stripe.const import WEBHOOK_HANDLED_EVENTS
from .common import StripeCommon


@tagged('post_install', '-at_install')
class StripeTest(StripeCommon):

    def test_processing_values(self):
        dummy_session_id = 'cs_test_sbTG0yGwTszAqFUP8Ulecr1bUwEyQEo29M8taYvdP7UA6Qr37qX6uA6w'
        tx = self.create_transaction(flow='redirect') # We don't really care what the flow is here.

        # Ensure no external API call is done, we only want to check the processing values logic
        def mock_stripe_create_checkout_session(self):
            return {'id': dummy_session_id}
        with patch.object(
            type(self.env['payment.transaction']),
            '_stripe_create_checkout_session',
            mock_stripe_create_checkout_session,
        ), mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = tx._get_processing_values()

        self.assertEqual(processing_values['publishable_key'], self.stripe.stripe_publishable_key)
        self.assertEqual(processing_values['session_id'], dummy_session_id)

    def test_onboarding_action_redirect_to_url(self):
        """ Test that the action generate and return an URL when the acquirer is disabled. """
        with patch.object(
            type(self.env['payment.acquirer']), '_stripe_fetch_or_create_connected_account',
            return_value={'id': 'dummy'},
        ), patch.object(
            type(self.env['payment.acquirer']), '_stripe_create_account_link',
            return_value='https://dummy.url',
        ):
            onboarding_url = self.stripe.action_stripe_connect_account()
        self.assertEqual(onboarding_url['url'], 'https://dummy.url')

    def test_only_create_webhook_if_not_already_done(self):
        """ Test that a webhook is created only if the webhook secret is not already set. """
        self.stripe.stripe_webhook_secret = False
        with patch.object(type(self.env['payment.acquirer']), '_stripe_make_request') as mock:
            self.stripe.action_stripe_create_webhook()
            self.assertEqual(mock.call_count, 1)

    def test_do_not_create_webhook_if_already_done(self):
        """ Test that no webhook is created if the webhook secret is already set. """
        self.stripe.stripe_webhook_secret = 'dummy'
        with patch.object(type(self.env['payment.acquirer']), '_stripe_make_request') as mock:
            self.stripe.action_stripe_create_webhook()
            self.assertEqual(mock.call_count, 0)

    def test_create_account_link_pass_required_parameters(self):
        """ Test that the generation of an account link includes all the required parameters. """
        with patch.object(
            type(self.env['payment.acquirer']), '_stripe_make_proxy_request',
            return_value={'url': 'https://dummy.url'},
        ) as mock:
            self.stripe._stripe_create_account_link('dummy', 'dummy')
            for payload_param in ('account', 'return_url', 'refresh_url', 'type'):
                self.assertIn(payload_param, mock.call_args.kwargs['payload'].keys())
