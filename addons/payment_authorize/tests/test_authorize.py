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
