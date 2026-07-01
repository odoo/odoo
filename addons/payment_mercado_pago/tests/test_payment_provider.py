# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.payment_mercado_pago import const
from odoo.addons.payment_mercado_pago.tests.common import MercadoPagoCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(MercadoPagoCommon):
    def test_connecting_a_live_account_is_allowed(self):
        """Test that setting live together with credentials (as the callback does) succeeds."""
        self._assert_does_not_raise(
            ValidationError,
            self.provider.write,
            {"is_live": True, "mercado_pago_access_token": "LIVE-TOKEN"},
        )

    def test_switching_to_live_without_reconnecting_is_blocked(self):
        """Test that flipping a test account to live without reconnecting raises.

        The credentials of the test account are dropped (they belong to a different account), which
        leaves the live provider without credentials and trips the constraint.
        """
        with self.assertRaises(ValidationError):
            self.provider.is_live = True  # The provider is connected in test mode.

    def test_switching_mode_resets_credentials(self):
        """Test that changing the connection mode clears the previous account's credentials.

        Test and live use distinct accounts; keeping the credentials across a mode change would make
        the provider appear to be in one mode while still holding the other's keys.
        """
        # Simulate a connected live account (credentials written together with is_live).
        self.provider.write({"is_live": True, "mercado_pago_access_token": "LIVE-TOKEN"})
        self.assertTrue(self.provider.mercado_pago_access_token)
        self.provider.is_live = False  # Switch back to test mode without reconnecting.
        self.assertFalse(self.provider.mercado_pago_access_token)

    def test_disconnecting_while_live_is_allowed(self):
        """Test that disconnecting a live account is not blocked by the live-credentials constraint.

        Resetting the credentials does not touch `is_live`, so the constraint (keyed on `is_live`)
        must not fire.
        """
        self.provider.write({"is_live": True, "mercado_pago_access_token": "LIVE-TOKEN"})
        self._assert_does_not_raise(ValidationError, self.provider.action_reset_credentials)
        self.assertFalse(self.provider.mercado_pago_access_token)

    def test_proxy_url_routes_to_test_proxy_in_test_mode(self):
        """Test that proxy requests of a test provider go to the test proxy."""
        url = self.provider._build_request_url("1/authorize", is_proxy_request=True)
        self.assertTrue(url.startswith(const.SANDBOX_PROXY_URL))

    def test_proxy_url_routes_to_live_proxy_in_live_mode(self):
        """Test that proxy requests of a live provider go to the live proxy."""
        self.provider.write({"is_live": True, "mercado_pago_access_token": "LIVE-TOKEN"})
        url = self.provider._build_request_url("1/authorize", is_proxy_request=True)
        self.assertTrue(url.startswith(const.PROXY_URL))

    def test_proxy_url_follows_the_onboarding_mode(self):
        """Test that the proxy is selected from the onboarding context before the account is set.

        While connecting, `is_live` does not yet reflect the chosen account, so the mode comes from
        the context set by the form buttons.
        """
        url = self.provider.with_context(mercado_pago_test_mode=False)._build_request_url(
            "1/authorize", is_proxy_request=True
        )
        self.assertTrue(url.startswith(const.PROXY_URL))

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
