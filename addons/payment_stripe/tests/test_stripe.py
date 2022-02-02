# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
        tx = self.create_transaction(flow='redirect')  # We don't really care what the flow is here.

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

    @mute_logger('odoo.addons.payment_stripe.controllers.main')
    def test_webhook_notification_confirms_transaction(self):
        """ Test the processing of a webhook notification. """
        tx = self.create_transaction('redirect')
        url = self._build_url(StripeController._webhook_url)
        with patch(
            'odoo.addons.payment_stripe.controllers.main.StripeController'
            '._verify_notification_signature'
        ), patch(
            'odoo.addons.payment_stripe.models.payment_acquirer.PaymentAcquirer'
            '._stripe_make_request',
            return_value={'status': 'succeeded'},
        ):
            self._make_json_request(url, data=self.NOTIFICATION_DATA)
        self.assertEqual(tx.state, 'done')

    @mute_logger('odoo.addons.payment_stripe.controllers.main')
    def test_webhook_notification_triggers_signature_check(self):
        """ Test that receiving a webhook notification triggers a signature check. """
        self.create_transaction('redirect')
        url = self._build_url(StripeController._webhook_url)
        with patch(
            'odoo.addons.payment_stripe.controllers.main.StripeController'
            '._verify_notification_signature'
        ) as signature_check_mock, patch(
            'odoo.addons.payment_stripe.models.payment_acquirer.PaymentAcquirer'
            '._stripe_make_request',
            return_value={},
        ), patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ):
            self._make_json_request(url, data=self.NOTIFICATION_DATA)
            self.assertEqual(signature_check_mock.call_count, 1)

    def test_stripe_neutralize(self):
        self.env['payment.acquirer']._neutralize()

        self.assertEqual(self.acquirer.stripe_secret_key, False)
        self.assertEqual(self.acquirer.stripe_publishable_key, False)
        self.assertEqual(self.acquirer.stripe_webhook_secret, False)
