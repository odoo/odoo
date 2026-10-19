# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.payment_mercado_pago.tests.common import MercadoPagoCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(MercadoPagoCommon):
    def test_allow_setting_live_if_credentials_are_set(self):
        """Test that setting live a Mercado Pago provider with credentials succeeds."""
        self._assert_does_not_raise(ValidationError, self.provider.write({"is_live": True}))

    def test_prevent_setting_live_if_credentials_are_not_set(self):
        """Test that setting live a Mercado Pago provider without credentials raises a
        ValidationError."""
        # Reset the state and credentials together to avoid triggering the constraint outside of the
        # 'assertRaises'.
        self.provider.module_state = "installed"
        self.provider.action_reset_credentials()
        with self.assertRaises(ValidationError):
            self.provider.is_live = True

    def test_not_available_for_unsupported_currencies(self):
        available_providers = self.env["payment.provider"]._find_available_providers(
            self.company_id, self.partner.id, self.amount, currency_id=self.env.ref("base.AFN").id
        )
        self.assertNotIn(self.provider, available_providers)

    def test_locale_resolves_from_website_language(self):
        """Test that a supported website language maps to its country's locale."""
        for lang, expected in [("pt_BR", "pt-BR"), ("es_AR", "es-AR"), ("es_MX", "es-MX")]:
            with self.subTest(lang=lang):
                locale = self.provider.with_context(lang=lang)._mercado_pago_get_locale()
                self.assertEqual(locale, expected)

    def test_locale_falls_back_to_company_country_for_es_419(self):
        """Test that es_419, which carries no country, resolves via the company's country."""
        self.env["res.lang"]._activate_lang("es_419")
        self.provider.company_id.country_id = self.env.ref("base.mx")
        locale = self.provider.with_context(lang="es_419")._mercado_pago_get_locale()
        self.assertEqual(locale, "es-MX")

    def test_locale_defaults_for_unsupported_language(self):
        """Test that an unsupported website language falls back to the default locale."""
        locale = self.provider.with_context(lang="fr_FR")._mercado_pago_get_locale()
        self.assertEqual(locale, "en-US")

    def test_locale_defaults_for_missing_language(self):
        """Test that an absent website language falls back to the default locale."""
        locale = self.provider.with_context(lang=None)._mercado_pago_get_locale()
        self.assertEqual(locale, "en-US")
