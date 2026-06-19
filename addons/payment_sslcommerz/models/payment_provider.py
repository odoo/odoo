# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.exceptions import ValidationError
from odoo.tools import urls

from odoo.addons.payment_sslcommerz import const


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("sslcommerz", "SSLCOMMERZ")], ondelete={"sslcommerz": "set default"}
    )
    sslcommerz_store_id = fields.Char(
        string="SSLCOMMERZ Store ID", required_if_provider="sslcommerz", copy=False
    )
    sslcommerz_store_passwd = fields.Char(
        string="SSLCOMMERZ Store Password",
        required_if_provider="sslcommerz",
        copy=False,
        groups="base.group_system",
    )

    # === COMPUTE METHODS === #

    def _get_supported_currencies(self):
        """Override of `payment` to return the supported currencies."""
        supported_currencies = super()._get_supported_currencies()
        if self.code == "sslcommerz":
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name == const.SUPPORTED_CURRENCY
            )
        return supported_currencies

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        self.ensure_one()
        if self.code != "sslcommerz":
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, **kwargs):
        """Override of `payment` to build the request URL."""
        if self.code != "sslcommerz":
            return super()._build_request_url(endpoint, **kwargs)
        if self.is_live:
            api_url = "https://securepay.sslcommerz.com"
        else:
            api_url = "https://sandbox.sslcommerz.com"
        return urls.urljoin(api_url, endpoint)

    def _parse_response_content(self, response, operation=None, **kwargs):
        """Override of `payment` to parse the response content."""
        if self.code != "sslcommerz":
            return super()._parse_response_content(response, operation=operation, **kwargs)

        try:
            response_content = response.json()
        except ValueError:
            raise ValidationError(
                self.env._("SSLCOMMERZ returned an invalid JSON response.")
            ) from None

        if operation == "create_session":
            if response_content.get("status") != "SUCCESS":
                raise ValidationError(
                    response_content.get("failedreason")
                    or self.env._("SSLCOMMERZ rejected the payment session request.")
                )
            if not response_content.get("GatewayPageURL"):
                raise ValidationError(
                    self.env._("SSLCOMMERZ did not return a hosted checkout URL.")
                )
        return response_content

    def _parse_response_error(self, response):
        """Override of `payment` to parse the error message."""
        if self.code != "sslcommerz":
            return super()._parse_response_error(response)

        try:
            response_content = response.json()
        except ValueError:
            return response.text
        return (
            response_content.get("failedreason")
            or response_content.get("errorReason")
            or response_content.get("status")
            or response.text
        )
