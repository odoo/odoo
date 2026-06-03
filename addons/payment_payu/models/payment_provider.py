# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
from urllib.parse import urlencode

from odoo import api, fields, models
from odoo.exceptions import RedirectWarning, ValidationError
from odoo.http import request
from odoo.tools.urls import urljoin

from odoo.addons.payment_payu import const


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(selection_add=[("payu", "PayU")], ondelete={"payu": "set default"})
    payu_key_id = fields.Char(string="PayU Key Id", required_if_provider="payu", copy=False)
    payu_merchant_salt = fields.Char(
        string="PayU Merchant Salt",
        required_if_provider="payu",
        copy=False,
        groups="base.group_system",
    )

    # === CONSTRAINT METHODS === #

    @api.constrains("state")
    def _check_payu_credentials_are_set_before_enabling(self):
        """Check that the PayU credentials are valid when the provider is enabled.

        :raise ValidationError: If the PayU credentials are not set
        """
        for provider in self.filtered(lambda p: p.code == "payu" and p.state != "disabled"):
            if not provider.payu_key_id or not provider.payu_merchant_salt:
                raise ValidationError(
                    self.env._(
                        'PayU credentials are missing. Click the "Connect" button to set up your'
                        " account."
                    )
                )

    # === COMPUTE METHODS === #

    def _get_supported_currencies(self):
        """Override of `payment` to return the supported currencies."""
        supported_currencies = super()._get_supported_currencies()
        if self.code == "payu":
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        self.ensure_one()
        if self.code != "payu":
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === ACTION METHODS === #

    def action_start_onboarding(self, menu_id=None):
        """Override of `payment` to redirect to the PayU OAuth URL.

        Note: `self.ensure_one()`

        :return: An URL action to redirect to the PayU OAuth URL
        :rtype: dict
        :raise RedirectWarning: If the company's currency is not supported
        """
        self.ensure_one()

        if self.code != "payu":
            return super().action_start_onboarding(menu_id=menu_id)

        if self.company_id.currency_id.name not in const.SUPPORTED_CURRENCIES:
            raise RedirectWarning(
                self.env._(
                    "PayU is not available in your country; please use another payment provider."
                ),
                self.env.ref("payment.action_payment_provider").id,
                self.env._("Other Payment Providers"),
            )

        params = {
            "provider_id": self.id,
            "csrf_token": request.csrf_token(),
            "return_url": urljoin(self.get_base_url(), const.OAUTH_RETURN_ROUTE),
        }
        authorization_url = f"{const.OAUTH_URL}/authorize?{urlencode(params)}"
        return {"type": "ir.actions.act_url", "url": authorization_url, "target": "self"}

    def _get_reset_values(self):
        """Override of `payment` to supply the provider-specific credential values to reset."""
        if self.code != "payu":
            return super()._get_reset_values()

        return {"payu_key_id": None, "payu_merchant_salt": None}

    # === BUSINESS METHODS === #

    def _payu_generate_signature(self, payment_data, incoming=False):
        """Generate the signature for the provided payment data.

        See: https://docs.payu.in/docs/hashing-request-and-response

        :param dict payment_data: The payment data to sign
        :param bool incoming: Whether the signature must be generated for an incoming (PayU to Odoo)
                              or for outgoing (Odoo to PayU) communication
        :return: The generated signature
        :rtype: str
        """
        signature_data = {**payment_data, "salt": self.payu_merchant_salt}
        signature_keys = const.SIGNATURE_KEYS["incoming" if incoming else "outgoing"]
        signature_string = "|".join(str(signature_data.get(field, "")) for field in signature_keys)
        return hashlib.sha512(signature_string.encode()).hexdigest().lower()

    # === REQUEST HELPERS === #

    def _build_request_url(
        self, endpoint, *, is_proxy_request=False, payu_access_token=None, **kwargs
    ):
        """Override of `payment` to build the request URL."""
        if self.code != "payu":
            return super()._build_request_url(
                endpoint,
                is_proxy_request=is_proxy_request,
                payu_access_token=payu_access_token,
                **kwargs,
            )

        if is_proxy_request:
            return urljoin(const.OAUTH_URL, endpoint)

        if payu_access_token:
            return urljoin(const.PARTNER_API_URL, endpoint)

        if self.state == "enabled":
            base_url = const.PAYMENT_API_LIVE_URL
        else:  # test
            base_url = const.PAYMENT_API_TEST_URL
        return urljoin(base_url, endpoint)

    def _build_request_headers(self, *args, payu_access_token=None, **kwargs):
        """Override of `payment` to build the request headers."""
        if self.code != "payu":
            return super()._build_request_headers(
                *args, payu_access_token=payu_access_token, **kwargs
            )
        return {"Authorization": f"Bearer {payu_access_token}"}

    def _parse_response_error(self, response):
        """Override of `payment` to parse the error message."""
        if self.code != "payu":
            return super()._parse_response_error(response)
        return response.json().get("error_description")
