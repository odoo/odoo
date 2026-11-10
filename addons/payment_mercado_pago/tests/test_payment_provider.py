# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.payment_mercado_pago.tests.common import MercadoPagoCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(MercadoPagoCommon):
    def test_switching_is_live_while_connected_is_blocked(self):
        with self.assertRaises(UserError):
            self.provider.is_live = True
        self.assertFalse(self.provider.is_live)

    def test_disconnecting_resets_is_live(self):
        self.provider.write({"is_live": True, "mercado_pago_access_token": "LIVE-TOKEN"})
        self.provider.action_reset_credentials()
        self.assertFalse(self.provider.is_live)

    def test_onboarding_sends_is_live_to_the_proxy(self):
        self.provider.company_id.country_id = self.env.ref("base.mx")
        with patch("odoo.addons.payment_mercado_pago.models.payment_provider.request", Mock()):
            action = self.provider.action_start_onboarding()
        self.assertEqual(parse_qs(urlsplit(action["url"]).query)["is_live"], ["False"])

    def test_token_refresh_sends_is_live_to_the_proxy(self):
        self.provider.write({
            "is_live": True,
            "mercado_pago_access_token": "LIVE-TOKEN",
            "mercado_pago_access_token_expiry": fields.Datetime.now() - timedelta(days=1),
        })
        token_data = {"access_token": "NEW-TOKEN", "refresh_token": "R", "expires_in": 15552000}
        with patch.object(
            self.registry["payment.provider"], "_send_api_request", return_value=token_data
        ) as request_mock:
            self.provider._mercado_pago_fetch_access_token()
        self.assertIs(request_mock.call_args.kwargs["json"]["is_live"], True)

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
