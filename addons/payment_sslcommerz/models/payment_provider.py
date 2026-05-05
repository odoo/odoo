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
                lambda c: c.name in const.SUPPORTED_CURRENCIES
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
            api_url = const.PAYMENT_API_LIVE_URL
        else:
            api_url = const.PAYMENT_API_TEST_URL
        return urls.urljoin(api_url, endpoint)

    def _parse_response_content(self, response, **kwargs):
        """Override of `payment` to parse the response content."""
        if self.code != "sslcommerz":
            return super()._parse_response_content(response, **kwargs)

        response_content = response.json()

        if failed_reason := response_content.get("failedreason"):
            raise ValidationError(failed_reason)

        return response_content
