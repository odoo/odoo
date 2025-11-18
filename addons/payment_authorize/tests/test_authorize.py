# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_authorize.tests.common import AuthorizeCommon


@tagged('post_install', '-at_install')
class AuthorizeTest(AuthorizeCommon):

    def test_compatible_providers(self):
        # Note: in the test common, 'USD' is specified as the currency linked to the user account.
        unsupported_currency = self._enable_currency('CHF')
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

    def test_amount_validation_is_skipped_when_transaction_details_are_missing(self):
        """Test that the amount validation is skipped when the API returns with an error."""
        tx = self._create_transaction('direct')
        with patch(
            'odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI'
            '.get_transaction_details',
            return_value={'err_code': 'E00040', 'err_msg': "The record cannot be found."},
        ):
            amount_data = tx._extract_amount_data({
                'response': {
                    'x_response_code': "E00040",
                    'x_response_reason_text': 'The record cannot be found.',
                }
            })
        self.assertEqual(amount_data, None)  # Amount validation is skipped.

    def test_voiding_confirmed_tx_cancels_it(self):
        """ Test that voiding a transaction cancels it even if it's already confirmed. """
        source_tx = self._create_transaction('direct', state='done')
        with patch(
            'odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI'
            '.get_transaction_details', return_value={'transaction': {'authAmount': self.amount}},
        ):
            source_tx._process('authorize', {
                'response': {
                    'x_response_code': '1',
                    'x_type': 'void',
                },
            })
        self.assertEqual(source_tx.state, 'cancel')

    @mute_logger('odoo.addons.payment_authorize.models.payment_transaction')
    def test_extract_token_values_maps_fields_correctly(self):
        tx = self._create_transaction('direct')
        payment_data = {
            'payment_details': '1234',
            'payment_profile_id': '123456789',
            'profile_id': '987654321',
        }
        with patch(
            'odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI'
            '.create_customer_profile', return_value=payment_data,
        ):
            token_values = tx._extract_token_values({})
        self.assertDictEqual(token_values, {
            'payment_details': '1234',
            'provider_ref': '123456789',
            'authorize_profile': '987654321',
        })
