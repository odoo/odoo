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
        def call_webhook(signature):
            webhook_url = self._build_url('/payment/stripe/webhook')
            self.reference = 'Test Transaction'
            stripe_post_data = {
                  "id": "evt_00000000000000",
                  "type": "checkout.session.completed",
                  "object": "event",
                  "data": {
                    "object": {
                      "id": "cs_00000000000000",
                      "client_reference_id": self.reference,
                      "object": "checkout.session",
                        "payment_status": "paid",
                    }
                  }
                }
            #1638270016

            stripe_signature = 't='+str(int(datetime.utcnow().timestamp()))+',v1='+signature+',v0=e9ea34475beed13f9a4b6376bab215828bd4468bcad526e64129b71044d7b851'

            self.create_transaction(flow='redirect')
            headers = {
                'host': '127.0.0.1:8069',
                'User-Agent': 'python-requests/2.22.0',
                'Accept-Encoding': 'gzip, deflate',
                'Accept': '*/*',
                'Connection': 'keep-alive',
                'Content-type': 'application/json',
                'Stripe-Signature': stripe_signature
            }

            response = requests.post(webhook_url, json=stripe_post_data, headers=headers)
            return response

        #Check if Forbidden error is not raise
        #Be carreful a Validation error is raise
        self._assert_not_raises(
            Forbidden,
            call_webhook,
            '4b32ab5e8b2f071ff7c603e303e34bdda59f01d346f9e92e08944ee091a7561d'
        )
