# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import urls

from odoo.addons.payment import utils as payment_utils
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

    def _compute_feature_support_fields(self):
        """Override of `payment` to enable additional features."""
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == "paypal").update({"support_tokenization": True})

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
        webhook_events = (
            const.CHECKOUT_WEBHOOK_EVENTS
            + const.CAPTURE_WEBHOOK_EVENTS
            + const.VAULT_WEBHOOK_EVENTS
            + const.MERCHANT_WEBHOOK_EVENTS
        )
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
            "allow_tokenization": any(
                capability.get("name") == const.VAULTING_CAPABILITY
                and capability.get("status") == "ACTIVE"
                for capability in response_content.get("capabilities", [])
            ),
        })

        return response_content

    def _find_available_payment_methods(
        self,
        partner_id,
        *,
        currency_id=None,
        force_tokenization=False,
        is_express_checkout=False,
        report=None,
        amount=0.0,
        **kwargs,
    ):
        """Override of `payment` to filter out payment methods that PayPal deems ineligible.

        PayPal's own eligibility rules (based on the customer's country, the seller account, etc.)
        are not necessarily reflected in the local configuration of the payment methods. The
        `find-eligible-methods` endpoint is called to refine the availability of PayPal's payment
        methods for the given payment context.

        :param float amount: The amount to pay (`0` for validation transactions)

        """
        payment_methods = super()._find_available_payment_methods(
            partner_id,
            currency_id=currency_id,
            force_tokenization=force_tokenization,
            is_express_checkout=is_express_checkout,
            report=report,
            amount=amount,
            **kwargs,
        )
        for provider in self.filtered(lambda p: p.code == "paypal"):
            if not provider.paypal_client_id or not provider.paypal_client_secret:
                continue
            if not currency_id:
                continue  # PayPal assesses eligibility per purchase; skip it for validations.
            eligible_method_keys = provider._paypal_get_eligible_payment_method_keys(
                partner_id,
                amount,
                currency_id=currency_id,
                user_agent=kwargs.get("paypal_customer_user_agent"),
            )
            if eligible_method_keys is None:
                continue
            ineligible_pms = payment_methods.filtered(
                lambda pm: (
                    pm.code in const.PAYMENT_METHODS_MAPPING
                    and const.PAYMENT_METHODS_MAPPING[pm.code] not in eligible_method_keys
                )
            )
            payment_utils.add_to_report(
                report,
                ineligible_pms,
                available=False,
                reason=self.env._("Not eligible according to PayPal"),
            )
            payment_methods -= ineligible_pms
        return payment_methods

    def _paypal_get_eligible_payment_method_keys(
        self, partner_id, amount, currency_id=None, user_agent=None
    ):
        """Return the PayPal payment source keys that are eligible for the given context.

        Note: `self.ensure_one()`

        :param int partner_id: The partner making the payment, as a `res.partner` id.
        :param float amount: The amount to pay (`0` for validation transactions)
        :param int currency_id: The payment currency, as a `res.currency` id.
        :param str user_agent: The customer's browser user agent string, forwarded to PayPal to
                               derive the browser, OS, and device type for eligibility assessment.
        :return: The eligible PayPal payment source keys (e.g., `{'paypal', 'venmo'}`), or `None`
                 if the eligibility could not be determined.
        :rtype: set|None
        """
        self.ensure_one()

        partner = self.env["res.partner"].browse(partner_id)
        currency = self.env["res.currency"].browse(currency_id)
        payload = {
            "customer": {"country_code": partner.country_code, "email": partner.email},
            "purchase_units": [
                {
                    "amount": {"currency_code": currency.name, "value": amount},
                    "payee": {
                        "email_address": self.paypal_email_account,
                        "merchant_id": self.paypal_account_id,
                    },
                }
            ],
            "preferences": {"intent": "CAPTURE"},
        }
        try:
            response_content = self._send_api_request(
                "POST",
                "/v2/payments/find-eligible-methods",
                json=payload,
                paypal_customer_user_agent=user_agent,
            )
        except ValidationError:
            _logger.warning("Could not fetch eligible payment methods from PayPal.")
            return None
        return set(response_content.get("eligible_methods", {}))

    def _paypal_get_inline_form_values(self, currency=None, partner_id=None, payment_method=None):
        """Return a serialized JSON of the required values to render the inline form.

        Note: `self.ensure_one()`

        :param res.currency currency: The transaction currency.
        :param int partner_id: The partner making the payment, as a `res.partner` id.
        :param payment.method payment_method: The payment method the form is rendered for.
        :return: The JSON serial of the required values to render the inline form.
        :rtype: str
        """
        partner = self.env["res.partner"].browse(partner_id).exists()
        # Validation operations have no currency, but the SDK requires a supported one.
        currency = currency or self.with_context(
            validation_pm=payment_method
        )._get_validation_currency()
        inline_form_values = {
            "provider_id": self.id,
            "client_id": self.paypal_client_id,
            "currency_code": currency and currency.name,
            "country_code": partner and partner.country_code,
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
        paypal_customer_user_agent=None,
        **kwargs,
    ):
        """Override of `payment` to build the request headers."""
        if self.code != "paypal":
            return super()._build_request_headers(*args, idempotency_key=idempotency_key, **kwargs)
        is_onboarding_request = paypal_onboarding_shared_id or paypal_onboarding_access_token
        headers = {
            # PayPal requires a reference specific to Odoo to be able to track Odoo customers.
            "PayPal-Partner-Attribution-Id": "ODOO_SP_DIRECT"
        }
        if is_onboarding_request:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            headers["Content-Type"] = "application/json"

        if paypal_onboarding_access_token:
            headers["Authorization"] = f"Bearer {paypal_onboarding_access_token}"
        elif not is_refresh_token_request and not paypal_onboarding_shared_id:
            headers["Authorization"] = f"Bearer {self._paypal_fetch_access_token()}"

        if idempotency_key:
            headers["PayPal-Request-Id"] = idempotency_key

        if paypal_customer_user_agent:
            headers["User-Agent"] = paypal_customer_user_agent

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
        response_content = response.json()
        descriptions = [
            detail["description"]
            for detail in response_content.get("details", [])
            if detail.get("description")
        ]
        return "\n".join(descriptions) or response_content.get("message", "")

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
