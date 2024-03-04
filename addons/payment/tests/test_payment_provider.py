# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon


@tagged('-at_install', 'post_install')
class TestPaymentProvider(PaymentCommon):

    def test_changing_provider_state_archives_tokens(self):
        """ Test that all active tokens of a provider are archived when its state is changed. """
        for old_state in ('enabled', 'test'):  # No need to check when the provided was disabled.
            for new_state in ('enabled', 'test', 'disabled'):
                if old_state != new_state:  # No need to check when the state is unchanged.
                    self.provider.state = old_state
                    token = self._create_token()
                    self.provider.state = new_state
                    self.assertFalse(token.active)

    def test_enabling_provider_activates_default_payment_methods(self):
        """ Test that the default payment methods of a provider are activated when it is
        enabled. """
        self.payment_methods.active = False
        for new_state in ('enabled', 'test'):
            self.provider.state = 'disabled'
            with patch(
                'odoo.addons.payment.models.payment_provider.PaymentProvider'
                '._get_default_payment_method_codes', return_value=self.payment_method_code,
            ):
                self.provider.state = new_state
                self.assertTrue(self.payment_methods.active)

    def test_disabling_provider_deactivates_default_payment_methods(self):
        """ Test that the default payment methods of a provider are deactivated when it is
        disabled. """
        self.payment_methods.active = True
        for old_state in ('enabled', 'test'):
            self.provider.state = old_state
            with patch(
                'odoo.addons.payment.models.payment_provider.PaymentProvider'
                '._get_default_payment_method_codes', return_value=self.payment_method_code,
            ):
                self.provider.state = 'disabled'
                self.assertFalse(self.payment_methods.active)

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

    def test_provider_compatible_with_available_countries(self):
        """ Test that the provider is compatible with its available countries. """
        belgium = self.env.ref('base.be')
        self.provider.available_country_ids = [Command.set([belgium.id])]
        self.partner.country_id = belgium
        compatible_providers = self.provider._get_compatible_providers(
            self.company.id, self.partner.id, self.amount
        )
        self.assertIn(self.provider, compatible_providers)

    def test_provider_not_compatible_with_unavailable_countries(self):
        """ Test that the provider is not compatible with a country that is not available. """
        belgium = self.env.ref('base.be')
        self.provider.available_country_ids = [Command.set([belgium.id])]
        france = self.env.ref('base.fr')
        self.partner.country_id = france
        compatible_providers = self.provider._get_compatible_providers(
            self.company.id, self.partner.id, self.amount
        )
        self.assertNotIn(self.provider, compatible_providers)

    def test_provider_compatible_when_no_available_countries_set(self):
        """ Test that the provider is always compatible when no available countries are set. """
        self.provider.available_country_ids = [Command.clear()]
        belgium = self.env.ref('base.be')
        self.partner.country_id = belgium
        compatible_providers = self.provider._get_compatible_providers(
            self.company.id, self.partner.id, self.amount
        )
        self.assertIn(self.provider, compatible_providers)

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

    def test_provider_compatible_when_no_available_currencies_set(self):
        """ Test that the provider is always compatible when no available currency is set. """
        self.provider.available_currency_ids = [Command.clear()]
        compatible_providers = self.provider._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, currency_id=self.currency_euro.id
        )
        self.assertIn(self.provider, compatible_providers)

    def test_provider_compatible_when_tokenization_forced(self):
        """ Test that the provider is compatible when it allows tokenization while it is forced by
        the calling module. """
        self.provider.allow_tokenization = True
        compatible_providers = self.provider._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, force_tokenization=True
        )
        self.assertIn(self.provider, compatible_providers)

    def test_provider_not_compatible_when_tokenization_forced(self):
        """ Test that the provider is not compatible when it does not allow tokenization while it
        is forced by the calling module. """
        self.provider.allow_tokenization = False
        compatible_providers = self.provider._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, force_tokenization=True
        )
        self.assertNotIn(self.provider, compatible_providers)

    def test_provider_compatible_when_tokenization_required(self):
        """ Test that the provider is compatible when it allows tokenization while it is required by
        the payment context (e.g., when paying for a subscription). """
        self.provider.allow_tokenization = True
        with patch(
            'odoo.addons.payment.models.payment_provider.PaymentProvider._is_tokenization_required',
            return_value=True,
        ):
            compatible_providers = self.provider._get_compatible_providers(
                self.company.id, self.partner.id, self.amount
            )
        self.assertIn(self.provider, compatible_providers)

    def test_provider_not_compatible_when_tokenization_required(self):
        """ Test that the provider is not compatible when it does not allow tokenization while it
        is required by the payment context (e.g., when paying for a subscription). """
        self.provider.allow_tokenization = False
        with patch(
            'odoo.addons.payment.models.payment_provider.PaymentProvider._is_tokenization_required',
            return_value=True,
        ):
            compatible_providers = self.provider._get_compatible_providers(
                self.company.id, self.partner.id, self.amount
            )
        self.assertNotIn(self.provider, compatible_providers)

    def test_provider_compatible_with_express_checkout(self):
        """ Test that the provider is compatible when it allows express checkout while it is an
        express checkout flow. """
        self.provider.allow_express_checkout = True
        compatible_providers = self.provider._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, is_express_checkout=True
        )
        self.assertIn(self.provider, compatible_providers)

    def test_provider_not_compatible_with_express_checkout(self):
        """ Test that the provider is not compatible when it does not allow express checkout while
        it is an express checkout flow. """
        self.provider.allow_express_checkout = False
        compatible_providers = self.provider._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, is_express_checkout=True
        )
        self.assertNotIn(self.provider, compatible_providers)
