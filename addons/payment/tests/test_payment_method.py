# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.models import Command
from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon


@tagged('-at_install', 'post_install')
class TestPaymentMethod(PaymentCommon):

    def test_unlinking_payment_method_from_provider_state_archives_tokens(self):
        """ Test that the active tokens of a payment method created through a provider are archived
        when the method is unlinked from the provider. """
        token = self._create_token()
        self.payment_method.provider_ids = [Command.unlink(self.payment_method.provider_ids[:1].id)]
        self.assertFalse(token.active)

    def test_payment_method_requires_provider_to_be_activated(self):
        """ Test that activating a payment method that is not linked to an enabled provider is
        forbidden. """
        self.provider.state = 'disabled'
        with self.assertRaises(UserError):
            self.payment_methods.active = True

    def test_payment_method_compatible_when_provider_is_enabled(self):
        """ Test that a payment method is available when it is supported by an enabled provider. """
        compatible_payment_methods = self.env['payment.method']._get_compatible_payment_methods(
            self.provider.ids, self.partner.id
        )
        self.assertIn(self.payment_method, compatible_payment_methods)

    def test_payment_method_not_compatible_when_provider_is_disabled(self):
        """ Test that a payment method is not available when there is no enabled provider that
        supports it. """
        self.provider.state = 'disabled'
        compatible_payment_methods = self.env['payment.method']._get_compatible_payment_methods(
            self.provider.ids, self.partner.id
        )
        self.assertNotIn(self.payment_method, compatible_payment_methods)

    def test_non_primary_payment_method_not_compatible(self):
        """ Test that a "brand" (i.e., non-primary) payment method is never available. """
        brand_payment_method = self.payment_method.copy()
        brand_payment_method.primary_payment_method_id = self.payment_method_id  # Make it a brand.
        compatible_payment_methods = self.env['payment.method']._get_compatible_payment_methods(
            self.provider.ids, self.partner.id
        )
        self.assertNotIn(brand_payment_method, compatible_payment_methods)

    def test_payment_method_compatible_with_supported_countries(self):
        """ Test that the payment method is compatible with its supported countries. """
        belgium = self.env.ref('base.be')
        self.payment_method.supported_country_ids = [Command.set([belgium.id])]
        self.partner.country_id = belgium
        compatible_payment_methods = self.env['payment.method']._get_compatible_payment_methods(
            self.provider.ids, self.partner.id
        )
        self.assertIn(self.payment_method, compatible_payment_methods)

    def test_payment_method_not_compatible_with_unsupported_countries(self):
        """ Test that the payment method is not compatible with a country that is not supported. """
        belgium = self.env.ref('base.be')
        self.payment_method.supported_country_ids = [Command.set([belgium.id])]
        france = self.env.ref('base.fr')
        self.partner.country_id = france
        compatible_payment_methods = self.env['payment.method']._get_compatible_payment_methods(
            self.provider.ids, self.partner.id
        )
        self.assertNotIn(self.payment_method, compatible_payment_methods)

    def test_payment_method_compatible_when_no_supported_countries_set(self):
        """ Test that the payment method is always compatible when no supported countries are
        set. """
        self.payment_method.supported_country_ids = [Command.clear()]
        belgium = self.env.ref('base.be')
        self.partner.country_id = belgium
        compatible_payment_methods = self.env['payment.method']._get_compatible_payment_methods(
            self.provider.ids, self.partner.id
        )
        self.assertIn(self.payment_method, compatible_payment_methods)

    def test_payment_method_compatible_with_supported_currencies(self):
        """ Test that the payment method is compatible with its supported currencies. """
        self.payment_method.supported_currency_ids = [Command.set([self.currency_euro.id])]
        compatible_payment_methods = self.env['payment.method']._get_compatible_payment_methods(
            self.provider.ids, self.partner.id, currency_id=self.currency_euro.id
        )
        self.assertIn(self.payment_method, compatible_payment_methods)

    def test_payment_method_not_compatible_with_unsupported_currencies(self):
        """ Test that the payment method is not compatible with a currency that is not
        supported. """
        self.payment_method.supported_currency_ids = [Command.set([self.currency_euro.id])]
        compatible_payment_methods = self.env['payment.method']._get_compatible_payment_methods(
            self.provider.ids, self.partner.id, currency_id=self.currency_usd.id
        )
        self.assertNotIn(self.payment_method, compatible_payment_methods)

    def test_payment_method_compatible_when_no_supported_currencies_set(self):
        """ Test that the payment method is always compatible when no supported currencies are
        set. """
        self.payment_method.supported_currency_ids = [Command.clear()]
        compatible_payment_methods = self.env['payment.method']._get_compatible_payment_methods(
            self.provider.ids, self.partner.id, currency_id=self.currency_euro.id
        )
        self.assertIn(self.payment_method, compatible_payment_methods)

    def test_payment_method_compatible_when_tokenization_forced(self):
        """ Test that the payment method is compatible when it supports tokenization while it is
        forced by the calling module. """
        self.payment_method.support_tokenization = True
        compatible_payment_methods = self.env['payment.method']._get_compatible_payment_methods(
            self.provider.ids, self.partner.id, force_tokenization=True
        )
        self.assertIn(self.payment_method, compatible_payment_methods)

    def test_payment_method_not_compatible_when_tokenization_forced(self):
        """ Test that the payment method is not compatible when it does not support tokenization
        while it is forced by the calling module. """
        self.payment_method.support_tokenization = False
        compatible_payment_methods = self.env['payment.method']._get_compatible_payment_methods(
            self.provider.ids, self.partner.id, force_tokenization=True
        )
        self.assertNotIn(self.payment_method, compatible_payment_methods)

    def test_payment_method_compatible_with_express_checkout(self):
        """ Test that the payment method is compatible when it supports express checkout while it is
        an express checkout flow. """
        self.payment_method.support_express_checkout = True
        compatible_payment_methods = self.env['payment.method']._get_compatible_payment_methods(
            self.provider.ids, self.partner.id, is_express_checkout=True
        )
        self.assertIn(self.payment_method, compatible_payment_methods)

    def test_payment_method_not_compatible_with_express_checkout(self):
        """ Test that the payment method is not compatible when it does not support express checkout
        while it is an express checkout flow. """
        self.payment_method.support_express_checkout = False
        compatible_payment_methods = self.env['payment.method']._get_compatible_payment_methods(
            self.provider.ids, self.partner.id, is_express_checkout=True
        )
        self.assertNotIn(self.payment_method, compatible_payment_methods)
