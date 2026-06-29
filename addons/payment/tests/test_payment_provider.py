# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

import requests

from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests.common import MockHTTPClient, tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.const import REPORT_REASONS_MAPPING
from odoo.addons.payment.tests.common import PaymentCommon


@tagged("-at_install", "post_install")
class TestPaymentProvider(PaymentCommon):
    _test_groups = None  # FIXME list needed groups

    def test_toggling_live_mode_archives_tokens(self):
        """Test that toggling live mode of a provider archives all its active tokens."""
        for is_live in (True, False):
            self.provider.is_live = not is_live
            token = self._create_token()
            self.provider.is_live = is_live
            self.assertFalse(token.active)

    def test_archiving_provider_archives_tokens(self):
        """Test that archiving a provider archives all its active tokens."""
        token = self._create_token()
        self.provider.active = False
        self.assertFalse(token.active)

    def test_archiving_provider_deactivates_default_payment_methods(self):
        """Test that archiving a provider deactivates its default payment methods ."""
        self.payment_methods.active = True
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider"
            "._get_default_payment_method_codes",
            return_value=self.payment_method_code,
        ):
            self.provider.active = False
            self.assertFalse(self.payment_methods.active)

    def test_unarchiving_provider_activates_default_payment_methods(self):
        """Test that unarchiving a provider activates its default payment methods."""
        self.provider.active = False
        self.payment_methods.active = False
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider"
            "._get_default_payment_method_codes",
            return_value={self.payment_method_code},
        ):
            self.provider.active = True
            self.assertTrue(self.payment_methods.active)

    def test_unarchiving_manual_capture_provider_activates_only_compatible_default_pms(self):
        """Test that archiving a manual capture provider only activates its compatible default
        payment methods."""
        payment_method_with_manual_capture = self.env["payment.method"].create({
            "name": "Payment Method With Manual Capture",
            "code": "pm_with_manual_capture",
            "support_manual_capture": "full_only",
            "provider_id": self.provider.id,
        })
        self.provider.write({"active": False, "capture_manually": True})
        self.payment_method.support_manual_capture = "none"
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider"
            "._get_default_payment_method_codes",
            return_value={self.payment_method_code, payment_method_with_manual_capture.code},
        ):
            self.provider.active = True
            self.assertFalse(self.payment_method.active)
            self.assertTrue(payment_method_with_manual_capture.active)

    def test_copy_provider_copies_methods(self):
        """Ensure primary PMs are copied to the new provider when the provider is copied."""
        primary_pm = self.env["payment.method"].create({
            "name": "Card",
            "code": "card_test",
            "active": True,
            "provider_id": self.dummy_provider.id,
        })
        new_provider = self.dummy_provider.copy()
        new_primary = new_provider.payment_method_ids.filtered(
            lambda pm: pm.code == primary_pm.code and not pm.primary_payment_method_id
        )
        self.assertEqual(len(new_primary), 1)

    def test_copy_provider_copies_brands(self):
        primary_pm = self.env["payment.method"].create({
            "name": "Card",
            "code": "card_test",
            "active": True,
            "provider_id": self.dummy_provider.id,
        })
        brand_pm = self.env["payment.method"].create({
            "name": "Visa",
            "code": "visa_test",
            "active": True,
            "primary_payment_method_id": primary_pm.id,
            "provider_id": self.dummy_provider.id,
        })
        new_provider = self.dummy_provider.copy()
        new_primary = new_provider.payment_method_ids.filtered(
            lambda pm: pm.code == primary_pm.code and not pm.primary_payment_method_id
        )
        new_brand = new_provider.payment_method_ids.filtered(lambda pm: pm.code == brand_pm.code)
        self.assertEqual(new_brand.primary_payment_method_id, new_primary)

    def test_installing_provider_activates_default_pms(self):
        self.provider.payment_method_ids.active = False
        PaymentProvider = self.registry["payment.provider"]
        with (
            patch.object(
                PaymentProvider,
                "_get_default_payment_method_codes",
                return_value={self.payment_method_code},
            ),
            patch.object(
                PaymentProvider,
                "_get_provider_domain",
                return_value=[("id", "=", self.dummy_provider.id)],
            ),
        ):
            self.provider._setup_provider("none")
        self.assertTrue(self.payment_method.active)

    def test_installing_provider_activates_default_pms_in_other_companies(self):
        self.provider.payment_method_ids.active = False
        other_company = self.env["res.company"].create({"name": "Other Company"})
        PaymentProvider = self.registry["payment.provider"]
        with (
            patch.object(
                PaymentProvider,
                "_get_default_payment_method_codes",
                return_value={self.payment_method_code},
            ),
            patch.object(
                PaymentProvider,
                "_get_provider_domain",
                return_value=[("id", "=", self.dummy_provider.id)],
            ),
        ):
            self.provider._setup_provider("none")
        copied_provider = self.env["payment.provider"].search([
            ("code", "=", "none"),
            ("company_id", "=", other_company.id),
        ])
        new_default_pm = copied_provider.payment_method_ids.filtered(
            lambda pm: pm.code == self.payment_method_code
        )
        self.assertTrue(new_default_pm.active)

    def test_installing_provider_activates_post_processing_cron(self):
        """Test that the post-processing cron is activated when a provider is installed."""
        post_processing_cron = self.env.ref("payment.cron_post_process_payment_tx")
        post_processing_cron.active = False
        self.provider._setup_provider("none")
        self.assertTrue(post_processing_cron.active)

    def test_uninstalling_provider_deactivates_default_payment_methods(self):
        """Test that uninstalling a provider deactivates its default payment methods ."""
        self.payment_methods.active = True
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider"
            "._get_default_payment_method_codes",
            return_value=self.payment_method_code,
        ):
            self.provider._remove_provider("none")
            self.assertFalse(self.payment_methods.active)

    def test_uninstalling_provider_deactivates_post_processing_cron(self):
        """Test that the post-processing cron is deactivated when a provider is uninstalled."""
        post_processing_cron = self.env.ref("payment.cron_post_process_payment_tx")
        post_processing_cron.active = True
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider.search_count",
            return_value=0,
        ):
            self.provider._remove_provider("none")
        self.assertFalse(post_processing_cron.active)

    def test_published_provider_available_to_all_users(self):
        for user in (self.public_user, self.portal_user):
            self.env = self.env(user=user)

            available_providers = (
                self
                .env["payment.provider"]
                .sudo()
                ._find_available_providers(self.company.id, self.partner.id, self.amount)
            )
            self.assertIn(self.provider, available_providers)

    def test_unpublished_provider_available_to_internal_user(self):
        self.provider.is_published = False

        available_providers = self.env["payment.provider"]._find_available_providers(
            self.company.id, self.partner.id, self.amount
        )
        self.assertIn(self.provider, available_providers)

    def test_unpublished_provider_not_available_to_non_internal_user(self):
        self.provider.is_published = False
        for user in (self.public_user, self.portal_user):
            self.env = self.env(user=user)

            available_providers = (
                self
                .env["payment.provider"]
                .sudo()
                ._find_available_providers(self.company.id, self.partner.id, self.amount)
            )
            self.assertNotIn(self.provider, available_providers)

    def test_provider_available_in_branch_companies(self):
        branch_company = self.env["res.company"].create({
            "name": "Provider Branch Company",
            "parent_id": self.provider.company_id.id,
        })
        available_providers = self.provider._find_available_providers(
            branch_company.id, self.partner.id, self.amount
        )
        self.assertIn(self.provider, available_providers)

    def test_provider_available_in_available_countries(self):
        belgium = self.env.ref("base.be")
        self.provider.available_country_ids = [Command.set([belgium.id])]
        self.partner.country_id = belgium
        available_providers = self.provider._find_available_providers(
            self.company.id, self.partner.id, self.amount
        )
        self.assertIn(self.provider, available_providers)

    def test_provider_not_available_in_unavailable_countries(self):
        belgium = self.env.ref("base.be")
        self.provider.available_country_ids = [Command.set([belgium.id])]
        france = self.env.ref("base.fr")
        self.partner.country_id = france
        available_providers = self.provider._find_available_providers(
            self.company.id, self.partner.id, self.amount
        )
        self.assertNotIn(self.provider, available_providers)

    def test_provider_available_when_no_available_countries_set(self):
        self.provider.available_country_ids = [Command.clear()]
        belgium = self.env.ref("base.be")
        self.partner.country_id = belgium
        available_providers = self.provider._find_available_providers(
            self.company.id, self.partner.id, self.amount
        )
        self.assertIn(self.provider, available_providers)

    def test_provider_available_when_minimum_amount_is_zero(self):
        self.provider.minimum_amount = 0
        currency = self.provider.main_currency_id.id

        available_providers = self.env["payment.provider"]._find_available_providers(
            self.company.id, self.partner.id, self.amount, currency_id=currency
        )
        self.assertIn(self.provider, available_providers)

    def test_provider_available_when_payment_above_minimum_amount(self):
        self.provider.minimum_amount = self.amount - 10
        currency = self.provider.main_currency_id.id

        available_providers = self.env["payment.provider"]._find_available_providers(
            self.company.id, self.partner.id, self.amount, currency_id=currency
        )
        self.assertIn(self.provider, available_providers)

    def test_provider_not_available_when_payment_below_minimum_amount(self):
        self.provider.minimum_amount = self.amount + 10
        currency = self.provider.main_currency_id.id

        available_providers = self.env["payment.provider"]._find_available_providers(
            self.company.id, self.partner.id, self.amount, currency_id=currency
        )
        self.assertNotIn(self.provider, available_providers)

    def test_provider_available_when_maximum_amount_is_zero(self):
        self.provider.maximum_amount = 0.0
        currency = self.provider.main_currency_id.id

        available_providers = self.env["payment.provider"]._find_available_providers(
            self.company.id, self.partner.id, self.amount, currency_id=currency
        )
        self.assertIn(self.provider, available_providers)

    def test_provider_available_when_payment_below_maximum_amount(self):
        self.provider.maximum_amount = self.amount + 10.0
        currency = self.provider.main_currency_id.id

        available_providers = self.env["payment.provider"]._find_available_providers(
            self.company.id, self.partner.id, self.amount, currency_id=currency
        )
        self.assertIn(self.provider, available_providers)

    def test_provider_not_available_when_payment_above_maximum_amount(self):
        self.provider.maximum_amount = self.amount - 10.0
        currency = self.provider.main_currency_id.id

        available_providers = self.env["payment.provider"]._find_available_providers(
            self.company.id, self.partner.id, self.amount, currency_id=currency
        )
        self.assertNotIn(self.provider, available_providers)

    def test_provider_available_for_available_currencies(self):
        available_providers = self.provider._find_available_providers(
            self.company.id, self.partner.id, self.amount, currency_id=self.currency_euro.id
        )
        self.assertIn(self.provider, available_providers)

    def test_provider_not_available_for_unavailable_currencies(self):
        # Make sure the list of available currencies is not empty.
        self.provider.available_currency_ids = [Command.unlink(self.currency_usd.id)]
        available_providers = self.provider._find_available_providers(
            self.company.id, self.partner.id, self.amount, currency_id=self.currency_usd.id
        )
        self.assertNotIn(self.provider, available_providers)

    def test_provider_available_when_no_available_currencies_set(self):
        self.provider.available_currency_ids = [Command.clear()]
        available_providers = self.provider._find_available_providers(
            self.company.id, self.partner.id, self.amount, currency_id=self.currency_euro.id
        )
        self.assertIn(self.provider, available_providers)

    def test_provider_available_when_tokenization_forced(self):
        self.provider.allow_tokenization = True
        available_providers = self.provider._find_available_providers(
            self.company.id, self.partner.id, self.amount, force_tokenization=True
        )
        self.assertIn(self.provider, available_providers)

    def test_provider_not_available_when_tokenization_forced(self):
        self.provider.allow_tokenization = False
        available_providers = self.provider._find_available_providers(
            self.company.id, self.partner.id, self.amount, force_tokenization=True
        )
        self.assertNotIn(self.provider, available_providers)

    def test_provider_available_when_tokenization_required(self):
        self.provider.allow_tokenization = True
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._is_tokenization_required",
            return_value=True,
        ):
            available_providers = self.provider._find_available_providers(
                self.company.id, self.partner.id, self.amount
            )
        self.assertIn(self.provider, available_providers)

    def test_provider_not_available_when_tokenization_required(self):
        self.provider.allow_tokenization = False
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._is_tokenization_required",
            return_value=True,
        ):
            available_providers = self.provider._find_available_providers(
                self.company.id, self.partner.id, self.amount
            )
        self.assertNotIn(self.provider, available_providers)

    def test_provider_available_for_express_checkout(self):
        self.provider.allow_express_checkout = True
        available_providers = self.provider._find_available_providers(
            self.company.id, self.partner.id, self.amount, is_express_checkout=True
        )
        self.assertIn(self.provider, available_providers)

    def test_provider_not_available_for_express_checkout(self):
        self.provider.allow_express_checkout = False
        available_providers = self.provider._find_available_providers(
            self.company.id, self.partner.id, self.amount, is_express_checkout=True
        )
        self.assertNotIn(self.provider, available_providers)

    def test_provider_availability_report_covers_all_reasons(self):
        # Prepare a base provider.
        self.provider.write({"allow_express_checkout": True, "allow_tokenization": True})

        # Prepare a provider with an unavailable country.
        invalid_country_provider = self.provider.copy()
        belgium = self.env.ref("base.be")
        invalid_country_provider.write({"available_country_ids": [Command.set([belgium.id])]})
        france = self.env.ref("base.fr")
        self.partner.country_id = france

        # Prepare a provider with a minimum amount higher than the payment amount.
        below_min_provider = self.provider.copy()
        below_min_provider.write({"minimum_amount": self.amount + 10.0})

        # Prepare a provider with a maximum amount lower than the payment amount.
        exceeding_max_provider = self.provider.copy()
        exceeding_max_provider.write({"maximum_amount": self.amount - 10.0})

        # Prepare a provider with an unavailable currency.
        invalid_currency_provider = self.provider.copy()
        invalid_currency_provider.write({
            "available_currency_ids": [Command.unlink(self.currency_usd.id)]
        })

        # Prepare a provider without tokenization support.
        no_tokenization_provider = self.provider.copy()
        no_tokenization_provider.write({"allow_tokenization": False})

        # Prepare a provider without express checkout support.
        no_express_checkout_provider = self.provider.copy()
        no_express_checkout_provider.write({"allow_express_checkout": False})

        # Get available providers to generate their availability report.
        report = {}
        self.env["payment.provider"]._find_available_providers(
            self.company_id,
            self.partner.id,
            self.amount,
            currency_id=self.currency_usd.id,
            force_tokenization=True,
            is_express_checkout=True,
            report=report,
        )

        # Compare the generated providers report with the expected one.
        providers_report = report["providers"]
        self.assertDictEqual(providers_report[self.provider], {"available": True, "reason": ""})
        self.assertDictEqual(
            providers_report[invalid_country_provider],
            {"available": False, "reason": REPORT_REASONS_MAPPING["incompatible_country"]},
        )
        self.assertDictEqual(
            providers_report[below_min_provider],
            {"available": False, "reason": REPORT_REASONS_MAPPING["exceed_min_or_max_amount"]},
        )
        self.assertDictEqual(
            providers_report[exceeding_max_provider],
            {"available": False, "reason": REPORT_REASONS_MAPPING["exceed_min_or_max_amount"]},
        )
        self.assertDictEqual(
            providers_report[invalid_currency_provider],
            {"available": False, "reason": REPORT_REASONS_MAPPING["incompatible_currency"]},
        )
        self.assertDictEqual(
            providers_report[no_tokenization_provider],
            {"available": False, "reason": REPORT_REASONS_MAPPING["tokenization_not_supported"]},
        )
        self.assertDictEqual(
            providers_report[no_express_checkout_provider],
            {
                "available": False,
                "reason": REPORT_REASONS_MAPPING["express_checkout_not_supported"],
            },
        )

    def test_payment_method_available_when_active(self):
        self.payment_method.active = True
        available_pms = self.provider._find_available_payment_methods(self.partner.id)
        self.assertIn(self.payment_method, available_pms)

    def test_payment_method_not_available_when_inactive(self):
        self.payment_method.active = False
        available_pms = self.provider._find_available_payment_methods(self.partner.id)
        self.assertNotIn(self.payment_method, available_pms)

    def test_payment_method_not_available_when_provider_is_not_installed(self):
        self.provider._remove_provider("none")
        available_pms = self.provider._find_available_payment_methods(self.partner.id)
        self.assertNotIn(self.payment_method, available_pms)

    def test_brand_payment_method_not_available(self):
        brand_payment_method = self.payment_method.copy({"code": "dummy_brand"})
        brand_payment_method.primary_payment_method_id = self.payment_method_id  # Make it a brand
        available_pms = self.provider._find_available_payment_methods(self.partner.id)
        self.assertNotIn(brand_payment_method, available_pms)

    def test_payment_method_available_in_supported_countries(self):
        belgium = self.env.ref("base.be")
        self.payment_method.supported_country_ids = [Command.set([belgium.id])]
        self.partner.country_id = belgium
        available_pms = self.provider._find_available_payment_methods(self.partner.id)
        self.assertIn(self.payment_method, available_pms)

    def test_payment_method_not_available_in_unsupported_countries(self):
        belgium = self.env.ref("base.be")
        self.payment_method.supported_country_ids = [Command.set([belgium.id])]
        france = self.env.ref("base.fr")
        self.partner.country_id = france
        available_pms = self.provider._find_available_payment_methods(self.partner.id)
        self.assertNotIn(self.payment_method, available_pms)

    def test_payment_method_available_when_no_supported_countries_set(self):
        self.payment_method.supported_country_ids = [Command.clear()]
        belgium = self.env.ref("base.be")
        self.partner.country_id = belgium
        available_pms = self.provider._find_available_payment_methods(self.partner.id)
        self.assertIn(self.payment_method, available_pms)

    def test_payment_method_available_for_supported_currencies(self):
        self.payment_method.supported_currency_ids = [Command.set([self.currency_euro.id])]
        available_pms = self.provider._find_available_payment_methods(
            self.partner.id, currency_id=self.currency_euro.id
        )
        self.assertIn(self.payment_method, available_pms)

    def test_payment_method_not_available_for_unsupported_currencies(self):
        self.payment_method.supported_currency_ids = [Command.set([self.currency_euro.id])]
        available_pms = self.provider._find_available_payment_methods(
            self.partner.id, currency_id=self.currency_usd.id
        )
        self.assertNotIn(self.payment_method, available_pms)

    def test_payment_method_available_when_no_supported_currencies_set(self):
        self.payment_method.supported_currency_ids = [Command.clear()]
        available_pms = self.provider._find_available_payment_methods(
            self.partner.id, currency_id=self.currency_euro.id
        )
        self.assertIn(self.payment_method, available_pms)

    def test_payment_method_available_when_tokenization_forced(self):
        self.payment_method.support_tokenization = True
        available_pms = self.provider._find_available_payment_methods(
            self.partner.id, force_tokenization=True
        )
        self.assertIn(self.payment_method, available_pms)

    def test_payment_method_not_available_when_tokenization_forced(self):
        self.payment_method.support_tokenization = False
        available_pms = self.provider._find_available_payment_methods(
            self.partner.id, force_tokenization=True
        )
        self.assertNotIn(self.payment_method, available_pms)

    def test_payment_method_available_for_express_checkout(self):
        self.payment_method.support_express_checkout = True
        available_pms = self.provider._find_available_payment_methods(
            self.partner.id, is_express_checkout=True
        )
        self.assertIn(self.payment_method, available_pms)

    def test_payment_method_not_available_for_express_checkout(self):
        self.payment_method.support_express_checkout = False
        available_pms = self.provider._find_available_payment_methods(
            self.partner.id, is_express_checkout=True
        )
        self.assertNotIn(self.payment_method, available_pms)

    def test_payment_method_availability_report_covers_all_reasons(self):
        # Disable all payment methods.
        pms = self.env["payment.method"].search([("is_primary", "=", True)])
        pms.active = False

        # Prepare a base payment method.
        self.payment_method.write({
            "active": True,
            "support_express_checkout": True,
            "support_tokenization": True,
        })

        # Prepare the report with a provider to allow checking provider availability.
        report = {}
        payment_utils.add_to_report(report, self.provider)

        # Prepare a payment method with an unavailable country.
        invalid_country_pm = self.payment_method.copy({"code": "unknown_country"})
        belgium = self.env.ref("base.be")
        invalid_country_pm.supported_country_ids = [Command.set([belgium.id])]
        france = self.env.ref("base.fr")
        self.partner.country_id = france

        # Prepare a payment method with an unavailable currency.
        invalid_currency_pm = self.payment_method.copy({"code": "unknown_currency"})
        invalid_currency_pm.supported_currency_ids = [Command.set([self.currency_euro.id])]

        # Prepare a payment method without support for tokenization.
        no_tokenization_pm = self.payment_method.copy({"code": "unknown_no_token"})
        no_tokenization_pm.support_tokenization = False

        # Prepare a payment method without support for express checkout.
        no_express_checkout_pm = self.payment_method.copy({"code": "unknown_no_express"})
        no_express_checkout_pm.support_express_checkout = False

        # Get available payment methods to generate their availability report.
        self.provider._find_available_payment_methods(
            self.partner.id,
            currency_id=self.currency_usd.id,
            force_tokenization=True,
            is_express_checkout=True,
            report=report,
        )

        # Compare the generated payment methods report with the expected one.
        expected_pms_report = {
            self.payment_method: {"available": True, "reason": ""},
            invalid_country_pm: {
                "available": False,
                "reason": REPORT_REASONS_MAPPING["incompatible_country"],
            },
            invalid_currency_pm: {
                "available": False,
                "reason": REPORT_REASONS_MAPPING["incompatible_currency"],
            },
            no_tokenization_pm: {
                "available": False,
                "reason": REPORT_REASONS_MAPPING["tokenization_not_supported"],
            },
            no_express_checkout_pm: {
                "available": False,
                "reason": REPORT_REASONS_MAPPING["express_checkout_not_supported"],
            },
        }
        self.maxDiff = None
        self.assertDictEqual(report["payment_methods"], expected_pms_report)

    def test_validation_currency_is_supported(self):
        """Test that only currencies supported by both the provider and the payment method can be
        used in validation operations."""
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

    @mute_logger("odoo.addons.payment.models.payment_provider")
    def test_parsing_non_json_response_falls_back_to_text_response(self):
        """Test that a non-JSON response is smoothly parsed as a text response."""
        with (
            MockHTTPClient(
                return_status=502, return_body=b"<html><body>Cloudflare Error</body></html>"
            ),
            patch.object(
                self.env.registry["payment.provider"],
                "_build_request_url",
                return_value="https://example.com/dummy",
            ),
            patch(
                "odoo.addons.payment.models.payment_provider.PaymentProvider._parse_response_error",
                new=lambda _self, response_: response_.json(),
            ),
        ):
            try:
                self.provider._send_api_request("GET", "/dummy")
            except Exception as e:  # noqa: BLE001
                self.assertNotIsInstance(e, requests.exceptions.JSONDecodeError)
                self.assertIsInstance(e, ValidationError)
                self.assertIn("Cloudflare Error", e.args[0])
