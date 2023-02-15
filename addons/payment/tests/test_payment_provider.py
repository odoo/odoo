# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon


@tagged('-at_install', 'post_install')
class TestPaymentProvider(PaymentCommon):

    def test_published_provider_compatible_with_all_users(self):
        """ Test that a published provider is always available to all users. """
        for user in (self.public_user, self.portal_user):
            self.env = self.env(user=user)

            compatible_providers = self.env['payment.provider'].sudo()._get_compatible_providers(
                self.company.id, self.partner.id, self.amount
            )
            self.assertIn(self.provider, compatible_providers)

    def test_unpublished_provider_compatible_with_internal_user(self):
        """ Test that an unpublished provider is still available to internal users. """
        self.provider.is_published = False

        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            self.company.id, self.partner.id, self.amount
        )
        self.assertIn(self.provider, compatible_providers)

    def test_unpublished_provider_not_compatible_with_non_internal_user(self):
        """ Test that an unpublished provider is not available to non-internal users. """
        self.provider.is_published = False
        for user in (self.public_user, self.portal_user):
            self.env = self.env(user=user)

            compatible_providers = self.env['payment.provider'].sudo()._get_compatible_providers(
                self.company.id, self.partner.id, self.amount
            )
            self.assertNotIn(self.provider, compatible_providers)

    def test_provider_compatible_when_maximum_amount_is_zero(self):
        """ Test that the maximum amount has no effect on the provider's compatibility when it is
        set to 0. """
        self.provider.maximum_amount = 0.
        currency = self.provider.main_currency_id.id

        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, currency_id=currency
        )
        self.assertIn(self.provider, compatible_providers)

    def test_provider_compatible_when_payment_below_maximum_amount(self):
        """ Test that a provider is compatible when the payment amount is less than the maximum
        amount. """
        self.provider.maximum_amount = self.amount + 10.0
        currency = self.provider.main_currency_id.id

        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, currency_id=currency
        )
        self.assertIn(self.provider, compatible_providers)

    def test_provider_not_compatible_when_payment_above_maximum_amount(self):
        """ Test that a provider is not compatible when the payment amount is more than the maximum
        amount. """
        self.provider.maximum_amount = self.amount - 10.0
        currency = self.provider.main_currency_id.id

        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, currency_id=currency
        )
        self.assertNotIn(self.provider, compatible_providers)

    def test_provider_compatible_with_available_currencies(self):
        """ Test that the provider is compatible with its available currencies. """
        compatible_providers = self.provider._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, currency_id=self.currency_euro.id
        )
        self.assertIn(self.provider, compatible_providers)

    def test_provider_not_compatible_with_unavailable_currencies(self):
        """ Test that the provider is not compatible with a currency that is not available. """
        # Make sure the list of available currencies is not empty.
        self.provider.available_currency_ids = [Command.unlink(self.currency_usd.id)]
        compatible_providers = self.provider._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, currency_id=self.currency_usd.id
        )
        self.assertNotIn(self.provider, compatible_providers)

    def test_provider_compatible_when_no_available_currency_set(self):
        """ Test that the provider is always compatible when no available currency is set. """
        self.provider.available_currency_ids = [Command.clear()]
        compatible_providers = self.provider._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, currency_id=self.currency_euro.id
        )
        self.assertIn(self.provider, compatible_providers)

    def test_fees_null_when_deactivated(self):
        """ Test that extra fees of a provider are null if these fees are deactivated. """
        self.provider.write({
            'fees_active': False,
            'fees_dom_fixed': 1.0,
            'fees_dom_var': 0.35,
            'fees_int_fixed': 0.1,
            'fees_int_var': 0.2,
        })
        transaction_fees = self.provider._compute_fees(
            self.amount, self.currency, self.partner.country_id
        )
        self.assertEqual(transaction_fees, 0)

    def test_fees_formula(self):
        """ Test that the extra fees of a provider are correctly computed in a domestic case. """
        self.provider.write({
            'fees_active': True,
            'fees_dom_fixed': 1.0,
            'fees_dom_var': 0.0035,
            'fees_int_fixed': 0.,
            'fees_int_var': 0.,
        })
        transaction_fees = self.currency.round(
            self.provider._compute_fees(
                self.amount,
                self.provider.company_id.currency_id,
                self.provider.company_id.country_id,
            )
        )
        self.assertEqual(transaction_fees, 4.91)

    def test_fees_with_currency_conversion(self):
        """ Test that the conversion of the fees is correctly computed. """
        # Some modules change the company settings and may make this test useless.
        if self.currency_euro == self.provider.main_currency_id or (
            self.country_france == self.provider.company_id.country_id
        ):
            return
        self.provider.write({
            'fees_active': True,
            'fees_dom_fixed': 0.,
            'fees_dom_var': 0.,
            'fees_int_fixed': 1.,
            'fees_int_var': 0.,
        })

        with patch(
            'odoo.addons.base.models.res_currency.Currency._get_rates',
            return_value={self.currency_euro.id: 2., self.provider.main_currency_id.id: 1.},
        ):
            transaction_fees = self.currency.round(
                self.provider._compute_fees(self.amount, self.currency_euro, self.country_france)
            )
            self.assertEqual(transaction_fees, 2.)
