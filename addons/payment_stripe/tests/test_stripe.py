# Part of Odoo. See LICENSE file for full copyright and licensing details.

import sys
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_stripe.controllers.main import StripeController
from odoo.addons.payment_stripe.tests.common import StripeCommon


@tagged('post_install', '-at_install')
class StripeTest(StripeCommon, PaymentHttpCommon):

    def test_processing_values(self):
        dummy_session_id = 'cs_test_sbTG0yGwTszAqFUP8Ulecr1bUwEyQEo29M8taYvdP7UA6Qr37qX6uA6w'
        tx = self._create_transaction(flow='redirect')  # We don't really care what the flow is here.

        # Ensure no external API call is done, we only want to check the processing values logic
        def mock_stripe_create_checkout_session(self):
            return {'id': dummy_session_id}

        with patch.object(
            type(self.env['payment.transaction']), '_stripe_create_checkout_session',
            mock_stripe_create_checkout_session,
        ), mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = tx._get_processing_values()

        self.assertEqual(processing_values['publishable_key'], self.stripe.stripe_publishable_key)
        self.assertEqual(processing_values['session_id'], dummy_session_id)

    @mute_logger('odoo.addons.payment_stripe.models.payment_transaction')
    def test_tx_state_after_send_capture_request(self):
        self.provider.capture_manually = True
        tx = self._create_transaction('redirect', state='authorized')

        with patch(
            'odoo.addons.payment_stripe.models.payment_provider.PaymentProvider'
            '._stripe_make_request',
            return_value={'status': 'succeeded'},
        ):
            tx._send_capture_request()
        self.assertEqual(
            tx.state, 'done', msg="The state should be 'done' after a successful capture."
        )

    @mute_logger('odoo.addons.payment_stripe.models.payment_transaction')
    def test_tx_state_after_send_void_request(self):
        self.provider.capture_manually = True
        tx = self._create_transaction('redirect', state='authorized')

        with patch(
            'odoo.addons.payment_stripe.models.payment_provider.PaymentProvider'
            '._stripe_make_request',
            return_value={'status': 'canceled'},
        ):
            tx._send_void_request()
        self.assertEqual(
            tx.state, 'cancel', msg="The state should be 'cancel' after voiding the transaction."
        )

    @mute_logger('odoo.addons.payment_stripe.controllers.main')
    def test_webhook_notification_confirms_transaction(self):
        """ Test the processing of a webhook notification. """
        tx = self._create_transaction('redirect')
        url = self._build_url(StripeController._webhook_url)
        with patch(
            'odoo.addons.payment_stripe.controllers.main.StripeController'
            '._verify_notification_signature'
        ):
            self._make_json_request(url, data=self.notification_data)
        self.assertEqual(tx.state, 'done')

    @mute_logger('odoo.addons.payment_stripe.controllers.main')
    def test_webhook_notification_tokenizes_payment_method(self):
        """ Test the processing of a webhook notification. """
        self._create_transaction('dummy', operation='validation', tokenize=True)
        url = self._build_url(StripeController._webhook_url)
        payment_method_response = {
            'card': {'last4': '4242'},
            'id': 'pm_1KVZSNAlCFm536g8sYB92I1G',
            'type': 'card'
        }
        with patch(
            'odoo.addons.payment_stripe.controllers.main.StripeController'
            '._verify_notification_signature'
        ), patch(
            'odoo.addons.payment_stripe.models.payment_provider.PaymentProvider'
            '._stripe_make_request',
            return_value=payment_method_response,
        ), patch(
            'odoo.addons.payment_stripe.models.payment_transaction.PaymentTransaction'
            '._stripe_tokenize_from_notification_data'
        ) as tokenize_check_mock:
            self._make_json_request(
                url, data=dict(self.notification_data, type="setup_intent.succeeded")
            )
        self.assertEqual(tokenize_check_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_stripe.controllers.main')
    def test_webhook_notification_triggers_signature_check(self):
        """ Test that receiving a webhook notification triggers a signature check. """
        self._create_transaction('redirect')
        url = self._build_url(StripeController._webhook_url)
        with patch(
            'odoo.addons.payment_stripe.controllers.main.StripeController'
            '._verify_notification_signature'
        ) as signature_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ):
            self._make_json_request(url, data=self.notification_data)
            self.assertEqual(signature_check_mock.call_count, 1)

    def test_stripe_neutralize(self):
        self.env['payment.provider']._neutralize()

        self.assertEqual(self.provider.stripe_secret_key, False)
        self.assertEqual(self.provider.stripe_publishable_key, False)
        self.assertEqual(self.provider.stripe_webhook_secret, False)

    def test_onboarding_action_redirect_to_url(self):
        """ Test that the action generate and return an URL when the provider is disabled. """
        with patch.object(
            type(self.env['payment.provider']), '_stripe_fetch_or_create_connected_account',
            return_value={'id': 'dummy'},
        ), patch.object(
            type(self.env['payment.provider']), '_stripe_create_account_link',
            return_value='https://dummy.url',
        ):
            onboarding_url = self.stripe.action_stripe_connect_account()
        self.assertEqual(onboarding_url['url'], 'https://dummy.url')

    def test_only_create_webhook_if_not_already_done(self):
        """ Test that a webhook is created only if the webhook secret is not already set. """
        self.stripe.stripe_webhook_secret = False
        with patch.object(type(self.env['payment.provider']), '_stripe_make_request') as mock:
            self.stripe.action_stripe_create_webhook()
            self.assertEqual(mock.call_count, 1)

    def test_do_not_create_webhook_if_already_done(self):
        """ Test that no webhook is created if the webhook secret is already set. """
        self.stripe.stripe_webhook_secret = 'dummy'
        with patch.object(type(self.env['payment.provider']), '_stripe_make_request') as mock:
            self.stripe.action_stripe_create_webhook()
            self.assertEqual(mock.call_count, 0)

    def test_create_account_link_pass_required_parameters(self):
        """ Test that the generation of an account link includes all the required parameters. """
        with patch.object(
            type(self.env['payment.provider']), '_stripe_make_proxy_request',
            return_value={'url': 'https://dummy.url'},
        ) as mock:
            self.stripe._stripe_create_account_link('dummy', 'dummy')
            mock.assert_called_once()
            if sys.version_info >= (3, 8):
                # call_args.kwargs is only available in python 3.8+
                call_args = mock.call_args.kwargs['payload'].keys()
                for payload_param in ('account', 'return_url', 'refresh_url', 'type'):
                    self.assertIn(payload_param, call_args)
