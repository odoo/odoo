# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_authorize.models.authorize_request import AuthorizeAPI
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import AuthorizeCommon


@tagged('post_install', '-at_install')
class AuthorizeTest(AuthorizeCommon):

    def test_compatible_providers(self):
        # Note: in the test common, 'USD' is specified as the currency linked to the user account.
        unsupported_currency = self._prepare_currency('CHF')
        providers = self.env['payment.provider']._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, currency_id=unsupported_currency.id
        )
        self.assertNotIn(self.authorize, providers)
        providers = self.env['payment.provider']._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, currency_id=self.currency_usd.id
        )
        self.assertIn(self.authorize, providers)

    def test_processing_values(self):
        """Test custom 'access_token' processing_values for authorize provider."""
        tx = self._create_transaction(flow='direct')
        with mute_logger('odoo.addons.payment.models.payment_transaction'), \
            patch(
                'odoo.addons.payment.utils.generate_access_token',
                new=self._generate_test_access_token
            ):
            processing_values = tx._get_processing_values()

        with patch(
            'odoo.addons.payment.utils.generate_access_token', new=self._generate_test_access_token
        ):
            self.assertTrue(payment_utils.check_access_token(
                processing_values['access_token'], self.reference, self.partner.id,
            ))

    def test_validation(self):
        self.assertEqual(self.authorize.available_currency_ids[0], self.currency_usd)
        self.assertEqual(self.authorize._get_validation_amount(), 0.01)
        self.assertEqual(self.authorize._get_validation_currency(), self.currency_usd)

    def test_voiding_confirmed_tx_cancels_it(self):
        """ Test that voiding a transaction cancels it even if it's already confirmed. """
        source_tx = self._create_transaction('direct', state='done')
        source_tx._handle_notification_data('authorize', {
            'response': {
                'x_response_code': '1',
                'x_type': 'void',
            },
        })
        self.assertEqual(source_tx.state, 'cancel')

    def test_declined_authorization_keeps_reason(self):
        """ Test that a declined auth-only request keeps the decline reason on the transaction. """
        tx = self._create_transaction('direct')
        declined_response = {
            'messages': {'resultCode': 'Ok', 'message': [{'code': 'I00001', 'text': 'Successful.'}]},
            'transactionResponse': {
                'responseCode': '2',
                'transId': '60000000001',
                'accountType': 'Visa',
                'errors': [{'errorCode': '2', 'errorText': "This transaction has been declined."}],
            },
        }
        with patch.object(AuthorizeAPI, '_make_request', return_value=declined_response):
            response = AuthorizeAPI(self.authorize).authorize(tx, opaque_data={'dataValue': 'x'})
        self.assertEqual(response['x_response_reason_text'], "This transaction has been declined.")

        tx._handle_notification_data('authorize', {'response': response})
        self.assertEqual(tx.state, 'cancel')
        self.assertEqual(tx.state_message, "This transaction has been declined.")
