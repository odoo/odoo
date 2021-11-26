# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger
from freezegun import freeze_time
from werkzeug.exceptions import Forbidden
from datetime import datetime

import requests
from .common import StripeCommon
from odoo.addons.payment.tests.http_common import PaymentHttpCommon


@tagged('post_install', '-at_install')
class StripeTest(StripeCommon, PaymentHttpCommon):

    def test_processing_values(self):
        dummy_session_id = 'cs_test_sbTG0yGwTszAqFUP8Ulecr1bUwEyQEo29M8taYvdP7UA6Qr37qX6uA6w'
        tx = self.create_transaction(flow='redirect')  # We don't really care what the flow is here.

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

    # freeze time for consistent singularize_prefix behavior during the test
    @freeze_time("2021-11-30 16:12:07")
    def test_webhook(self):
        """ Verify the correctness of error handling during the webhook.
        Note: As JSON-RPC encapsulates the error handling of a request into a 200 response,
         the raise of 403 can not been check here but only the non raise is verify.
        """

        def call_webhook(signature):
            webhook_url = self._build_url('/payment/stripe/webhook')
            self.reference = 'Test Transaction'
            payload_id = "pi_1Esnh9AlCFm536g8l8QNh0ud"
            stripe_post_data = {
                  "id": payload_id,
                  "type": "checkout.session.completed",
                  "object": "event",
                  "data": {
                    "object": {
                      "id": "cs_00000000000000",
                      "client_reference_id": self.reference,
                      "object": "checkout.session",
                      "payment_status": "paid",
                      "payment_intent": payload_id,
                    }
                  }
                }
            stripe_signature = 't=' + str(int(datetime.utcnow().timestamp())) + ',v1=' + signature +\
                               ',v0=e9ea34475beed13f9a4b6376bab215828bd4468bcad526e64129b71044d7b851'
            self.create_transaction(flow='redirect', stripe_payment_intent=payload_id, reference=self.reference)

            headers = {
                'host': '127.0.0.1:8069',
                'User-Agent': 'python-requests/2.22.0',
                'Accept-Encoding': 'gzip, deflate',
                'Accept': '*/*',
                'Connection': 'keep-alive',
                'Content-type': 'application/json',
                'Stripe-Signature': stripe_signature
            }

            return requests.post(webhook_url, json=stripe_post_data, headers=headers)

        self._assert_not_raises(
            Forbidden,
            call_webhook,
            '8bc12af6819ad4d9614582001c372f15e2ce138ad1a25bc981cf8330db814a1f'
        )
