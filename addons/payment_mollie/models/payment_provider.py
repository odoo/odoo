from odoo import _, fields, models, service
from odoo.tools import urls

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_mollie import const

_logger = get_payment_logger(__name__)


class PaymentProvider(models.Model):
    _inherit = "payment.provider"
    _CREDENTIAL_FIELDS = {
        "mollie_api_key": "mollie_api_key",
    }

    code = fields.Selection(
        selection_add=[("mollie", "Mollie")],
        ondelete={"mollie": "set default"},
    )
    mollie_api_key = fields.Char(
        string="Mollie API Key",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        required_if_provider="mollie",
        groups="base.group_system",
        help="The Test or Live API Key depending on the configuration of the provider",
    )

    # === COMPUTE METHODS === #

    def _get_supported_currencies(self):
        """Override of `payment` to return the supported currencies."""
        supported_currencies = super()._get_supported_currencies()
        if self.code == "mollie":
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        self.check_singleton()

        if self.code != "mollie":
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === REQUEST HELPERS === #

    def _prepare_request_url(self, endpoint, **kwargs):
        """Override of `payment` to build the request URL."""
        if self.code != "mollie":
            return super()._prepare_request_url(endpoint, **kwargs)
        return urls.urljoin("https://api.mollie.com/v2/", endpoint.strip("/"))

    def _prepare_request_headers(self, *args, **kwargs):
        """Override of `payment` to build the request headers."""
        if self.code != "mollie":
            return super()._prepare_request_headers(*args, **kwargs)

        odoo_version = service.common.exp_version()["server_version"]
        module_version = self.env.ref("base.module_payment_mollie").manifest_version
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.mollie_api_key}",
            "Content-Type": "application/json",
            # See https://docs.mollie.com/integration-partners/user-agent-strings
            "User-Agent": f"Odoo/{odoo_version} MollieNativeOdoo/{module_version}",
        }

    def _parse_response_error(self, response):
        """Override of `payment` to parse the error message."""
        if self.code != "mollie":
            return super()._parse_response_error(response)

        return response.json().get("detail", "")
