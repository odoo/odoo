# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.const import REPORT_REASONS_MAPPING
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

    def test_brand_compatible_with_manual_capture(self):
        """ Test that a "brand" can be enabled for providers which support manual capture. """
        self.provider.update({
            'capture_manually': True,
            'support_manual_capture': 'partial',
        })
        self.payment_method.support_manual_capture = 'partial'
        brand_payment_method = self.env['payment.method'].create({
            'name': "Dummy Brand",
            'code': 'dumbrand',
            'primary_payment_method_id': self.payment_method.id,
            'active': False,
            'provider_ids': self.provider.ids,
        })
        self._assert_does_not_raise(ValidationError, brand_payment_method.action_unarchive)
        self.assertTrue(brand_payment_method.active)

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

    def test_availability_report_covers_all_reasons(self):
        """ Test that every possible unavailability reason is correctly reported. """
        # Disable all payment methods.
        pms = self.env['payment.method'].search([('is_primary', '=', True)])
        pms.active = False

        # Prepare a base payment method.
        self.payment_method.write({
            'active': True,
            'support_express_checkout': True,
            'support_tokenization': True,
        })

        # Prepare the report with a provider to allow checking provider availability.
        report = {}
        payment_utils.add_to_report(report, self.provider)

        # Prepare a payment method with an unavailable provider.
        unavailable_provider = self.provider.copy()
        payment_utils.add_to_report(report, unavailable_provider, available=False, reason="test")
        no_provider_pm = self.payment_method.copy()
        no_provider_pm.provider_ids = [Command.set([unavailable_provider.id])]
        unavailable_provider.payment_method_ids = [Command.set([no_provider_pm.id])]

        # Prepare a payment method with an incompatible country.
        invalid_country_pm = self.payment_method.copy()
        belgium = self.env.ref('base.be')
        invalid_country_pm.supported_country_ids = [Command.set([belgium.id])]
        france = self.env.ref('base.fr')
        self.partner.country_id = france

        # Prepare a payment method with an incompatible currency.
        invalid_currency_pm = self.payment_method.copy()
        invalid_currency_pm.supported_currency_ids = [Command.set([self.currency_euro.id])]

        # Prepare a payment method without support for tokenization.
        no_tokenization_pm = self.payment_method.copy()
        no_tokenization_pm.support_tokenization = False

        # Prepare a payment method without support for express checkout.
        no_express_checkout_pm = self.payment_method.copy()
        no_express_checkout_pm.support_express_checkout = False

        # Get compatible payment methods to generate their availability report.
        self.env['payment.method']._get_compatible_payment_methods(
            self.provider.ids,
            self.partner.id,
            currency_id=self.currency_usd.id,
            force_tokenization=True,
            is_express_checkout=True,
            report=report,
        )

        # Compare the generated payment methods report with the expected one.
        expected_pms_report = {
            self.payment_method: {
                'available': True,
                'reason': '',
                'supported_providers': [(self.provider, True)],
            },
            no_provider_pm: {
                'available': False,
                'reason': REPORT_REASONS_MAPPING['provider_not_available'],
                'supported_providers': [(unavailable_provider, False)],
             },
            invalid_country_pm: {
                'available': False,
                'reason': REPORT_REASONS_MAPPING['incompatible_country'],
                'supported_providers': [(self.provider, True)],
             },
            invalid_currency_pm: {
                'available': False,
                'reason': REPORT_REASONS_MAPPING['incompatible_currency'],
                'supported_providers': [(self.provider, True)],
             },
            no_tokenization_pm: {
                'available': False,
                'reason': REPORT_REASONS_MAPPING['tokenization_not_supported'],
                'supported_providers': [(self.provider, True)],
             },
            no_express_checkout_pm: {
                'available': False,
                'reason': REPORT_REASONS_MAPPING['express_checkout_not_supported'],
                'supported_providers': [(self.provider, True)],
            },
        }
        self.maxDiff = None
        self.assertDictEqual(report['payment_methods'], expected_pms_report)
