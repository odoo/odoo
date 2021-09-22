# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.payment import utils as payment_utils
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import AuthorizeCommon


@tagged('post_install', '-at_install')
class AuthorizeTest(AuthorizeCommon):

    def test_compatible_acquirers(self):
        # Note: in the test common, 'USD' is specified as authorize_currency_id
        unsupported_currency = self._prepare_currency('CHF')
        acquirers = self.env['payment.acquirer']._get_compatible_acquirers(
            partner_id=self.partner.id,
            currency_id=unsupported_currency.id,
            company_id=self.company.id)
        self.assertNotIn(self.authorize, acquirers)
        acquirers = self.env['payment.acquirer']._get_compatible_acquirers(
            partner_id=self.partner.id,
            currency_id=self.currency_usd.id,
            company_id=self.company.id)
        self.assertIn(self.authorize, acquirers)

    def test_processing_values(self):
        """Test custom 'access_token' processing_values for authorize acquirer."""
        tx = self.create_transaction(flow='direct')
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
        self.assertEqual(self.authorize.authorize_currency_id, self.currency_usd)
        self.assertEqual(self.authorize._get_validation_amount(), 0.01)
        self.assertEqual(self.authorize._get_validation_currency(), self.currency_usd)

    def test_token_activation(self):
        """Activation of disabled authorize tokens is forbidden"""
        token = self.create_token(active=False)
        with self.assertRaises(UserError):
            token._handle_reactivation_request()
