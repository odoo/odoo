# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import secrets
from datetime import timedelta

from odoo import _, api, fields, models
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
    paypal_client_id = fields.Char(string="PayPal Client ID", copy=False)
    paypal_client_secret = fields.Char(
        string="PayPal Client Secret", copy=False, groups="base.group_system"
    )
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
    paypal_webhook_id = fields.Char(string="PayPal Webhook ID", copy=False)
    paypal_account_id = fields.Char(string="Paypal Seller Account ID", copy=False)
    paypal_seller_nonce = fields.Char(string="Paypal Seller Nonce", copy=False)

    paypal_is_oauth_onboarded = fields.Boolean(string="Onboarded via OAuth button", copy=False)
    paypal_payments_receivable = fields.Boolean(copy=False)
    paypal_email_confirmed = fields.Boolean(copy=False)

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

        :raise ValidationError: If the PayPal credentials are not valid.
        """
        for provider in self.filtered(lambda p: p.code == "paypal" and p.is_published):
            if (
                not provider.paypal_client_id
                or not provider.paypal_client_secret
                or not provider.paypal_account_id
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

    def action_paypal_create_webhook(self):
        """Create a new webhook.

        Note: This action only works for instances using a public URL.

        :return: None
        :raise UserError: If the base URL is not in HTTPS.
        """
        base_url = self._paypal_get_base_url()
        data = {
            "url": urls.urljoin(base_url, PaypalController._webhook_url),
            "event_types": [
                {"name": event_type}
                for event_type in const.CHECKOUT_WEBHOOK_EVENTS + const.MERCHANT_WEBHOOK_EVENTS
            ],
        }
        webhook_data = self._send_api_request("POST", "/v1/notifications/webhooks", json=data)
        self.paypal_webhook_id = webhook_data.get("id")

    def action_start_onboarding(self, menu_id=None):
        """Override of `payment` to redirect to the PayPal OAuth URL.

        Note: `self.ensure_one()`

        :param int menu_id: The menu from which the onboarding is started, as an `ir.ui.menu` id.
        :return: An URL action to redirect to the PayPal OAuth URL.
        :rtype: dict
        """
        self.ensure_one()

        if self.code != "paypal":
            return super().action_start_onboarding(menu_id=menu_id)

        self.paypal_seller_nonce = secrets.token_urlsafe(32)

        return {
            "type": "ir.actions.client",
            "tag": "paypal_onboarding_client_action",
            "params": {"provider_id": self.id},
        }

    def action_paypal_check_onboarding_status(self):
        for provider in self:
            provider._paypal_check_onboarding_status()
        return True

    # === BUSINESS METHODS === #

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

    def _get_reset_values(self):
        """Override of `payment` to supply the provider-specific credential values to reset."""
        if self.code != "paypal":
            return super()._get_reset_values()

        return {
            "paypal_access_token": None,
            "paypal_access_token_expiry": None,
            "paypal_email_account": None,
            "paypal_client_id": None,
            "paypal_client_secret": None,
            "paypal_webhook_id": None,
            "paypal_account_id": None,
            "paypal_is_oauth_onboarded": False,
            "paypal_seller_nonce": None,
        }

    def _paypal_request_onboarding_token(self, auth_code, shared_id):
        self.ensure_one()
        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "code_verifier": self.paypal_seller_nonce,
        }
        response_content = self._send_api_request(
            "POST", "/v1/oauth2/token", data=data, paypal_onboarding_shared_id=shared_id
        )
        if not (paypal_onboarding_access_token := response_content.get("access_token")):
            raise ValidationError(_("Failed to retrieve access token."))
        return paypal_onboarding_access_token

    def _paypal_check_onboarding_status(self):
        self.ensure_one()
        if not self.paypal_account_id:
            raise ValidationError(_("Missing Account ID. Cannot check onboarding status."))
        endpoint = (
            f"/v1/customer/partners/{const.ONBOARDING_REFERENCE['partner_id']}"
            f"/merchant-integrations/{self.paypal_account_id}"
        )
        response_content = self._send_api_request("GET", endpoint)
        self.paypal_email_account = response_content.get("primary_email")
        self.paypal_payments_receivable = response_content.get("payments_receivable")
        self.paypal_email_confirmed = response_content.get("primary_email_confirmed")
        return response_content

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

    def _paypal_get_base_url(self):
        base_url = self.get_base_url()
        if "localhost" in base_url:
            raise UserError(
                "PayPal: " + self.env._("You must have an HTTPS connection to generate a webhook.")
            )
        return base_url

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
            "Content-Type": "application/json",
            # PayPal requires a reference specific to Odoo to be able to track Odoo customers.
            "PayPal-Partner-Attribution-Id": "ODOO_SP_DIRECT",
        }
        if paypal_onboarding_shared_id or paypal_onboarding_access_token:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if paypal_onboarding_access_token:
            headers["Authorization"] = f"Bearer {paypal_onboarding_access_token}"
        if idempotency_key:
            headers["PayPal-Request-Id"] = idempotency_key
        if (
            not is_refresh_token_request
            and not paypal_onboarding_shared_id
            and not paypal_onboarding_access_token
        ):
            headers["Authorization"] = f"Bearer {self._paypal_fetch_access_token()}"
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
