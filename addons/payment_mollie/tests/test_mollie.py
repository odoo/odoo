# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_mollie.controllers.main import MollieController
from odoo.addons.payment_mollie.tests.common import MollieCommon


@tagged('post_install', '-at_install')
class MollieTest(MollieCommon, PaymentHttpCommon):

    def test_payment_request_payload_values(self):
        tx = self._create_transaction(flow='redirect')

        payload = tx._mollie_prepare_payment_request_payload()
        expected_billing_address = {
            'givenName': 'Norbert',
            'familyName': 'Buyer',
            'streetAndNumber': 'Huge Street 2/543',
            'postalCode': '1000',
            'city': 'Sin City',
            'country': 'BE',
            'email': 'norbert.buyer@example.com',
        }

        self.assertDictEqual(payload['amount'], {'currency': 'EUR', 'value': '1111.11'})
        self.assertDictEqual(payload['billingAddress'], expected_billing_address)
        self.assertDictEqual(payload['lines'][0]['totalAmount'], {'currency': 'EUR', 'value': '1111.11'})
        self.assertEqual(payload['description'], tx.reference)

    @mute_logger(
        'odoo.addons.payment_mollie.controllers.main',
        'odoo.addons.payment_mollie.models.payment_transaction',
    )
    def test_webhook_notification_confirms_transaction(self):
        """ Test the processing of a webhook notification. """
        tx = self._create_transaction('redirect')
        url = self._build_url(MollieController._webhook_url)
        with patch(
            'odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request',
            return_value={
                'status': 'paid',
                'amount': {'value': str(self.amount), 'currency': self.currency.name},
            },
        ):
            self._make_http_post_request(url, data=self.payment_data)
        self.assertEqual(tx.state, 'done')

    def test_payload_preparation_in_payment_with_tokenize(self):
        """Test that tokenization requests create a customer and set a 'first' sequence without a
        mandate ID."""
        tx = self._create_transaction('redirect')
        tx.tokenize = True
        with patch.object(
            self.env.registry['payment.transaction'], '_mollie_create_customer',
            return_value='cst_test987',
        ):
            payload = tx._mollie_prepare_payment_request_payload()

        self.assertEqual(payload.get('sequenceType'), 'first')
        self.assertEqual(payload.get('customerId'), 'cst_test987')
        self.assertNotIn('mandateId', payload)

    def test_payload_preparation_in_payment_with_token(self):
        """Test that using a saved token produces a recurring payload with customer and mandate IDs
        and no method."""
        tx = self._create_transaction('redirect')
        token = self._create_token()
        token.mollie_customer_id = 'cst_test987'
        tx.token_id = token

        payload = tx._mollie_prepare_payment_request_payload()

        self.assertEqual(payload.get('sequenceType'), 'recurring')
        self.assertEqual(payload.get('customerId'), 'cst_test987')
        self.assertEqual(payload.get('mandateId'), 'provider Ref (TEST)')
        self.assertNotIn('method', payload)

    def test_payload_preparation_in_oneoff_payment(self):
        """Test that a payment without tokenization or token is configured as a one-off sequence."""
        tx = self._create_transaction('redirect')
        payload = tx._mollie_prepare_payment_request_payload()

        self.assertEqual(payload.get('sequenceType'), 'oneoff')
