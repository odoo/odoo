# Part of Odoo. See LICENSE file for full copyright and licensing details.

from json.decoder import JSONDecodeError
from unittest.mock import patch

import requests

from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.const import REPORT_REASONS_MAPPING
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
                '._get_default_payment_method_codes', return_value={self.payment_method_code},
            ):
                self.provider.state = new_state
                self.assertTrue(self.payment_methods.active)

    def test_enabling_manual_capture_provider_activates_compatible_default_pms(self):
        """Test that only payment methods supporting manual capture are activated when a provider
        requiring manual capture is enabled."""
        payment_method_with_manual_capture = self.env['payment.method'].create({
            'name': 'Payment Method With Manual Capture',
            'code': 'pm_with_manual_capture',
            'support_manual_capture': 'full_only',
        })
        self.provider.state = 'disabled'
        self.provider.capture_manually = True
        self.provider.payment_method_ids = [Command.set([
            self.payment_method.id, payment_method_with_manual_capture.id
        ])]
        self.payment_method.support_manual_capture = 'none'
        default_codes = {self.payment_method_code, payment_method_with_manual_capture.code}
        with patch(
            'odoo.addons.payment.models.payment_provider.PaymentProvider'
            '._get_default_payment_method_codes', return_value=default_codes,
        ):
            self.provider.state = 'test'
            self.assertFalse(self.payment_methods.active)
            self.assertTrue(payment_method_with_manual_capture.active)

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

    def test_enabling_provider_activates_processing_cron(self):
        """ Test that the post-processing cron is activated when a provider is enabled. """
        self.env['payment.provider'].search([]).state = 'disabled'  # Reset providers' state.
        post_processing_cron = self.env.ref('payment.cron_post_process_payment_tx')
        for enabled_state in ('enabled', 'test'):
            post_processing_cron.active = False  # Reset the cron's active field.
            self.provider.state = 'disabled'  # Prepare the dummy provider for enabling.
            self.provider.state = enabled_state
            self.assertTrue(post_processing_cron.active)

    def test_disabling_provider_deactivates_processing_cron(self):
        """ Test that the post-processing cron is deactivated when a provider is disabled. """
        self.env['payment.provider'].search([]).state = 'disabled'  # Reset providers' state.
        post_processing_cron = self.env.ref('payment.cron_post_process_payment_tx')
        for enabled_state in ('enabled', 'test'):
            post_processing_cron.active = True  # Reset the cron's active field.
            self.provider.state = enabled_state  # Prepare the dummy provider for disabling.
            self.provider.state = 'disabled'
            self.assertFalse(post_processing_cron.active)

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

    def test_provider_compatible_with_branch_companies(self):
        """ Test that the provider is available to branch companies. """
        branch_company = self.env['res.company'].create({
            'name': "Provider Branch Company",
            'parent_id': self.provider.company_id.id,
        })
        compatible_providers = self.provider._get_compatible_providers(
            branch_company.id, self.partner.id, self.amount,
        )
        self.assertIn(self.provider, compatible_providers)

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

    def test_availability_report_covers_all_reasons(self):
        """ Test that every possible unavailability reason is correctly reported. """
        # Disable all providers.
        providers = self.env['payment.provider'].search([])
        providers.state = 'disabled'

        # Prepare a base provider.
        self.provider.write({
            'state': 'test',
            'allow_express_checkout': True,
            'allow_tokenization': True,
        })

        # Prepare a provider with an incompatible country.
        invalid_country_provider = self.provider.copy()
        belgium = self.env.ref('base.be')
        invalid_country_provider.write({
            'state': 'test',
            'available_country_ids': [Command.set([belgium.id])],
        })
        france = self.env.ref('base.fr')
        self.partner.country_id = france

        # Prepare a provider with a maximum amount lower than the payment amount.
        exceeding_max_provider = self.provider.copy()
        exceeding_max_provider.write({
            'state': 'test',
            'maximum_amount': self.amount - 10.0,
        })

        # Prepare a provider with an incompatible currency.
        invalid_currency_provider = self.provider.copy()
        invalid_currency_provider.write({
            'state': 'test',
            'available_currency_ids': [Command.unlink(self.currency_usd.id)],
        })

        # Prepare a provider without tokenization support.
        no_tokenization_provider = self.provider.copy()
        no_tokenization_provider.write({
            'state': 'test',
            'allow_tokenization': False,
        })

        # Prepare a provider without express checkout support.
        no_express_checkout_provider = self.provider.copy()
        no_express_checkout_provider.write({
            'state': 'test',
            'allow_express_checkout': False,
        })

        # Get compatible providers to generate their availability report.
        report = {}
        self.env['payment.provider']._get_compatible_providers(
            self.company_id,
            self.partner.id,
            self.amount,
            currency_id=self.currency_usd.id,
            force_tokenization=True,
            is_express_checkout=True,
            report=report,
        )

        # Compare the generated providers report with the expected one.
        expected_providers_report = {
            self.provider: {
                'available': True,
                'reason': '',
            },
            invalid_country_provider: {
                'available': False,
                'reason': REPORT_REASONS_MAPPING['incompatible_country'],
             },
            exceeding_max_provider: {
                'available': False,
                'reason': REPORT_REASONS_MAPPING['exceed_max_amount'],
            },
            invalid_currency_provider: {
                'available': False,
                'reason': REPORT_REASONS_MAPPING['incompatible_currency'],
             },
            no_tokenization_provider: {
                'available': False,
                'reason': REPORT_REASONS_MAPPING['tokenization_not_supported'],
             },
            no_express_checkout_provider: {
                'available': False,
                'reason': REPORT_REASONS_MAPPING['express_checkout_not_supported'],
            },
        }
        self.maxDiff = None
        self.assertDictEqual(report['providers'], expected_providers_report)

    def test_validation_currency_is_supported(self):
        """ Test that only currencies supported by both the provider and the payment method can be
        used in validation operations. """
        self.provider.available_currency_ids = [Command.clear()]  # Supports all currencies.
        self.payment_method.supported_currency_ids = [Command.clear()]  # Supports all currencies.
        validation_currency = self.provider.with_context(
            validation_pm=self.payment_method
        )._get_validation_currency()
        self.assertEqual(validation_currency, self.provider.company_id.currency_id)

        self.provider.available_currency_ids = [Command.set(self.currency_usd.ids)]
        self.payment_method.supported_currency_ids = [Command.clear()]  # Supports all currencies.
        validation_currency = self.provider.with_context(
            validation_pm=self.payment_method
        )._get_validation_currency()
        self.assertIn(validation_currency, self.provider.available_currency_ids)

        self.provider.available_currency_ids = [Command.clear()]  # Supports all currencies.
        self.payment_method.supported_currency_ids = [Command.set(self.currency_usd.ids)]
        validation_currency = self.provider.with_context(
            validation_pm=self.payment_method
        )._get_validation_currency()
        self.assertIn(validation_currency, self.payment_method.supported_currency_ids)

        self.provider.available_currency_ids = [Command.set(self.currency_usd.ids)]
        self.payment_method.supported_currency_ids = [Command.set(self.currency_usd.ids)]
        validation_currency = self.provider.with_context(
            validation_pm=self.payment_method
        )._get_validation_currency()
        self.assertIn(validation_currency, self.provider.available_currency_ids)
        self.assertIn(validation_currency, self.payment_method.supported_currency_ids)

    @mute_logger('odoo.addons.payment.models.payment_provider')
    def test_parsing_non_json_response_falls_back_to_text_response(self):
        """Test that a non-JSON response is smoothly parsed as a text response."""
        response = requests.Response()
        response.status_code = 502
        response._content = b"<html><body>Cloudflare Error</body></html>"
        with (
            patch('requests.request', return_value=response),
            patch(
                'odoo.addons.payment.models.payment_provider.PaymentProvider._parse_response_error',
                new=lambda _self, _response: _response.json(),
            ),
        ):
            try:
                self.provider._send_api_request('GET', '/dummy')
            except Exception as e:  # noqa: BLE001
                self.assertNotIsInstance(e, JSONDecodeError)
                self.assertIsInstance(e, ValidationError)
                self.assertIn("Cloudflare Error", e.args[0])
