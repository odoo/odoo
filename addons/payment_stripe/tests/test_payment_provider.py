# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.payment_stripe import const
from odoo.addons.payment_stripe.tests.common import StripeCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(StripeCommon):
    def test_onboarding_action_redirect_to_url(self):
        """Test that the action generate and return an URL when the provider is disabled."""
        if country := self.env["res.country"].search(
            [("code", "in", list(const.SUPPORTED_COUNTRIES))], limit=1
        ):
            self.env.company.country_id = country
        else:
            self.skipTest("Unable to find a country supported by both odoo and stripe")

        with (
            patch.object(
                self.env.registry["payment.provider"],
                "_stripe_fetch_or_create_connected_account",
                return_value={"id": "dummy"},
            ),
            patch.object(
                self.env.registry["payment.provider"],
                "_stripe_create_account_link",
                return_value="https://dummy.url",
            ),
        ):
            onboarding_url = self.stripe.action_start_onboarding()
        self.assertEqual(onboarding_url["url"], "https://dummy.url")

    def test_only_create_webhook_if_webhook_secret_is_not_already_set(self):
        """Test that a webhook is created only if the webhook secret is not already set."""
        self.stripe.stripe_webhook_secret = False
        with self._mock_send_api_request() as mock:
            self.stripe.action_stripe_create_webhook()
            self.assertEqual(mock.call_count, 1)

    def test_do_not_create_webhook_if_webhook_secret_is_already_set(self):
        """Test that no webhook is created if the webhook secret is already set."""
        self.stripe.stripe_webhook_secret = "dummy"
        with self._mock_send_api_request() as mock:
            self.stripe.action_stripe_create_webhook()
            self.assertEqual(mock.call_count, 0)

    def test_country_mapping_stripe_connect(self):
        """Test that La Réunion (and other french territories) is supported by Stripe Connect."""
        mapped_country_company = self.env["res.company"].create({"name": "Mapped Company"})
        with (
            self._mock_send_api_request(return_value={"url": "https://dummy.url"}) as mock,
            patch.object(
                self.env.registry["payment.provider"],
                "_stripe_fetch_or_create_connected_account",
                return_value={"id": "dummy"},
            ),
        ):
            for country_code in const.COUNTRY_MAPPING:
                country = self.env["res.country"].search([("code", "=", country_code)], limit=1)
                mapped_country_company.country_id = country
                self.stripe.with_company(mapped_country_company).action_start_onboarding(
                    menu_id="dummy"
                )
            self.assertEqual(mock.call_count, len(const.COUNTRY_MAPPING))

    def test_create_account_link_pass_required_parameters(self):
        """Test that the generation of an account link includes all the required parameters."""
        with self._mock_send_api_request(return_value={"url": "https://dummy.url"}) as mock:
            self.stripe._stripe_create_account_link("dummy", "dummy")
            mock.assert_called_once()
            call_args = mock.call_args.kwargs["json"]["payload"].keys()
            for payload_param in ("account", "return_url", "refresh_url", "type"):
                self.assertIn(payload_param, call_args)
