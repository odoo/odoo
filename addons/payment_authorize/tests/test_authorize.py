# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.payment import utils as payment_utils
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

    def _handle_decline(self, reason_code='2', avs_result_code='Y', cvv_result_code='M'):
        tx = self._create_transaction('direct')
        tx._handle_notification_data('authorize', {
            'response': {
                'x_response_code': '2',
                'x_response_reason_code': reason_code,
                'x_response_reason_text': "This transaction has been declined.",
                'x_avs_result_code': avs_result_code,
                'x_cvv_result_code': cvv_result_code,
                'x_trans_id': '60000000001',
                'x_type': 'auth_capture',
                'payment_method_code': 'Visa',
            },
        })
        self.assertEqual(tx.state, 'cancel')
        return tx.state_message

    def test_decline_without_avs_or_cvv_mismatch_keeps_reason(self):
        self.assertEqual(self._handle_decline(), "This transaction has been declined.")

    def test_decline_with_cvv_mismatch_adds_hint(self):
        message = self._handle_decline(cvv_result_code='N')
        self.assertTrue(message.startswith("This transaction has been declined.\n"))
        self.assertIn("security code (CVV) does not match", message)

    def test_decline_with_avs_mismatch_adds_hint(self):
        message = self._handle_decline(avs_result_code='N')
        self.assertIn("billing address or postal code", message)

    def test_decline_with_avs_and_cvv_filter_adds_combined_hint(self):
        message = self._handle_decline(reason_code='45')
        self.assertIn("billing address and the card security code", message)

    def test_explicit_avs_decline_reason_is_not_duplicated(self):
        message = self._handle_decline(reason_code='27', avs_result_code='N')
        self.assertEqual(message, "This transaction has been declined.")
