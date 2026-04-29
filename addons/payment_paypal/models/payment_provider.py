# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import urls

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_paypal import const
from odoo.addons.payment_paypal.controllers.main import PaypalController

_logger = get_payment_logger(__name__)


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("paypal", "PayPal")], ondelete={"paypal": "set default"}
    )

    paypal_email_account = fields.Char(
        string="PayPal Email",
        help="The public business email solely used to identify the account with PayPal",
        default=lambda self: self.env.company.email,
        copy=False,
    )
    paypal_account_id = fields.Char(string="PayPal Seller Account ID", copy=False)
    paypal_client_id = fields.Char(string="PayPal Client ID", copy=False)
    paypal_client_secret = fields.Char(
        string="PayPal Client Secret", copy=False, groups="base.group_system"
    )
    paypal_webhook_id = fields.Char(string="PayPal Webhook ID", copy=False)

    paypal_seller_nonce = fields.Char(copy=False)
    paypal_is_oauth_onboarded = fields.Boolean(copy=False)
    paypal_payments_receivable = fields.Boolean(copy=False)
    paypal_email_confirmed = fields.Boolean(copy=False)

    paypal_access_token = fields.Char(
        string="PayPal Access Token",
        help="The short-lived token used to access Paypal APIs",
        copy=False,
        groups="base.group_system",
    )
    paypal_access_token_expiry = fields.Datetime(
        string="PayPal Access Token Expiry",
        help="The moment at which the access token becomes invalid.",
        default="1970-01-01",
        copy=False,
        groups="base.group_system",
    )

    # === COMPUTE METHODS === #

    def _get_supported_currencies(self):
        """Override of `payment` to return the supported currencies."""
        supported_currencies = super()._get_supported_currencies()
        if self.code == "paypal":
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    # === CONSTRAINT METHODS === #

    @api.constrains("is_published")
    def _check_paypal_credentials_are_set_if_published(self):
        """Check that the PayPal credentials are valid when the provider is set to published mode.

        :rtype: None
        :raise ValidationError: If the PayPal credentials are not valid.
        """
        for provider in self.filtered(lambda p: p.code == "paypal" and p.is_published):
            if not (
                provider.paypal_client_id
                and provider.paypal_client_secret
                and provider.paypal_account_id
            ):
                raise ValidationError(
                    provider.env._(
                        'PayPal credentials are missing. Please click the "Connect" button or'
                        " fill them manually to set up your account."
                    )
                )

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        self.ensure_one()
        if self.code != "paypal":
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === ACTION METHODS === #

    def action_start_onboarding(self, menu_id=None):
        """Override of `payment` to start the OAuth onboarding in the client."""
        self.ensure_one()

        if self.code != "paypal":
            return super().action_start_onboarding(menu_id=menu_id)

        return {
            "type": "ir.actions.client",
            "tag": "paypal_onboarding_client_action",
            "params": {"provider_id": self.id},
        }

    def action_reset_credentials(self):
        """Override of `payment` to trigger a hard reload on the page when credentials are reset.

        This is necessary because the PayPal SDK is single-use and must be loaded again.

        :return: The action to reload the page.
        :rtype: dict
        """
        res = super().action_reset_credentials()
        if self.code != "paypal":
            return res
        return {"type": "ir.actions.client", "tag": "reload"}

    def _get_reset_values(self):
        """Override of `payment` to supply the provider-specific credential values to reset."""
        if self.code != "paypal":
            return super()._get_reset_values()

        return {
            "paypal_email_account": None,
            "paypal_account_id": None,
            "paypal_client_id": None,
            "paypal_client_secret": None,
            "paypal_webhook_id": None,
            "paypal_is_oauth_onboarded": False,
            "paypal_seller_nonce": None,
            "paypal_payments_receivable": False,
            "paypal_email_confirmed": False,
            "paypal_access_token": None,
            "paypal_access_token_expiry": None,
        }

    def action_paypal_update_onboarding_status(self):
        """Update the providers with the status of their merchant account.

        :return: True
        :rtype: bool
        :raise UserError: If the merchant account id of a provider is missing.
        """
        for provider in self:
            provider._paypal_update_onboarding_status()
        return True

    def action_paypal_create_webhook(self):
        """Create a new webhook.

        Note: This action only works for instances using a public URL.

        :return: None
        :raise UserError: If the base URL is not in HTTPS.
        """
        base_url = self.get_base_url()
        webhook_events = const.CHECKOUT_WEBHOOK_EVENTS + const.MERCHANT_WEBHOOK_EVENTS
        data = {
            "url": urls.urljoin(base_url, PaypalController._webhook_url),
            "event_types": [{"name": event_type} for event_type in webhook_events],
        }
        webhook_data = self._send_api_request("POST", "/v1/notifications/webhooks", json=data)
        self.paypal_webhook_id = webhook_data.get("id")

    # === BUSINESS METHODS === #

    def _paypal_update_onboarding_status(self):
        """Fetch the status of the merchant account and update the provider accordingly.

        Note: `self.ensure_one()`

        :return: The status of the merchant account.
        :rtype: dict
        :raise UserError: If the merchant account id is missing.
        """
        self.ensure_one()

        if not self.paypal_account_id:
            raise UserError(self.env._("Missing Account ID. Cannot check onboarding status."))

        # Fetch the status of the merchant account
        endpoint = (
            f"/v1/customer/partners/{const.OAUTH_ODOO_PARTNER_ID}"
            f"/merchant-integrations/{self.paypal_account_id}"
        )
        response_content = self._send_api_request("GET", endpoint)

        # Update the provider with the details of the merchant account
        self.write({
            "paypal_email_account": response_content.get("primary_email"),
            "paypal_payments_receivable": response_content.get("payments_receivable"),
            "paypal_email_confirmed": response_content.get("primary_email_confirmed"),
        })

        return response_content

    def _paypal_get_inline_form_values(self, currency=None):
        """Return a serialized JSON of the required values to render the inline form.

        Note: `self.ensure_one()`

        :param res.currency currency: The transaction currency.
        :return: The JSON serial of the required values to render the inline form.
        :rtype: str
        """
        inline_form_values = {
            "provider_id": self.id,
            "client_id": self.paypal_client_id,
            "currency_code": currency and currency.name,
        }
        return json.dumps(inline_form_values)

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, **kwargs):
        """Override of `payment` to build the request URL."""
        if self.code != "paypal":
            return super()._build_request_url(endpoint, **kwargs)
        return self._paypal_get_api_url() + endpoint

    def _paypal_get_api_url(self):
        """Return the API URL according to the provider state.

        Note: self.ensure_one()

        :return: The API URL
        :rtype: str
        """
        self.ensure_one()

        if self.is_live:
            return "https://api-m.paypal.com"
        return "https://api-m.sandbox.paypal.com"

    def _build_request_headers(
        self,
        *args,
        idempotency_key=None,
        is_refresh_token_request=False,
        paypal_onboarding_shared_id=None,
        paypal_onboarding_access_token=None,
        **kwargs,
    ):
        """Override of `payment` to build the request headers."""
        if self.code != "paypal":
            return super()._build_request_headers(
                *args,
                idempotency_key=idempotency_key,
                is_refresh_token_request=is_refresh_token_request,
                paypal_onboarding_shared_id=paypal_onboarding_shared_id,
                paypal_onboarding_access_token=paypal_onboarding_access_token,
                **kwargs,
            )

        headers = {
            # PayPal requires a reference specific to Odoo to be able to track Odoo customers.
            "PayPal-Partner-Attribution-Id": "ODOO_SP_DIRECT"
        }

        if paypal_onboarding_shared_id or paypal_onboarding_access_token:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            headers["Content-Type"] = "application/json"

        if paypal_onboarding_access_token:
            headers["Authorization"] = f"Bearer {paypal_onboarding_access_token}"
        elif not is_refresh_token_request and not paypal_onboarding_shared_id:
            headers["Authorization"] = f"Bearer {self._paypal_fetch_access_token()}"

        if idempotency_key:
            headers["PayPal-Request-Id"] = idempotency_key

        return headers

    def _paypal_fetch_access_token(self):
        """Generate a new access token if it's expired, otherwise return the existing access token.

        :return: A valid access token.
        :rtype: str
        :raise ValidationError: If the access token can not be fetched.
        """
        if (
            not self.paypal_access_token_expiry
            or fields.Datetime.now() > self.paypal_access_token_expiry - timedelta(minutes=5)
        ):
            response_content = self._send_api_request(
                "POST",
                "/v1/oauth2/token",
                data={"grant_type": "client_credentials"},
                is_refresh_token_request=True,
            )
            access_token = response_content["access_token"]
            if not access_token:
                raise ValidationError(self.env._("Could not generate a new access token."))
            self.write({
                "paypal_access_token": access_token,
                "paypal_access_token_expiry": fields.Datetime.now()
                + timedelta(seconds=response_content["expires_in"]),
            })
        return self.paypal_access_token

    def _parse_response_error(self, response):
        """Override of `payment` to parse the error message."""
        if self.code != "paypal":
            return super()._parse_response_error(response)
        return response.json().get("message", "")

    def _build_request_auth(
        self, *, is_refresh_token_request=False, paypal_onboarding_shared_id=None, **kwargs
    ):
        """Override of `payment` to build the request Auth."""
        if self.code != "paypal" or not (is_refresh_token_request or paypal_onboarding_shared_id):
            return super()._build_request_auth(
                is_refresh_token_request=is_refresh_token_request,
                paypal_onboarding_shared_id=paypal_onboarding_shared_id,
                **kwargs,
            )

        if is_refresh_token_request:
            return self.paypal_client_id, self.paypal_client_secret
        if paypal_onboarding_shared_id:
            return paypal_onboarding_shared_id, ""
