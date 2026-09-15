import hashlib

from odoo import fields, models

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_nuvei import const

_logger = get_payment_logger(__name__)


class PaymentProvider(models.Model):
    _inherit = "payment.provider"
    _CREDENTIAL_FIELDS = {
        "nuvei_secret_key": "nuvei_secret_key",
    }

    code = fields.Selection(
        selection_add=[("nuvei", "Nuvei")],
        ondelete={"nuvei": "set default"},
    )
    nuvei_merchant_identifier = fields.Char(
        copy=False,
        required_if_provider="nuvei",
        help="The code of the merchant account to use with this provider.",
    )
    nuvei_site_identifier = fields.Char(
        copy=False,
        required_if_provider="nuvei",
        groups="base.group_system",
        help="The site identifier code associated with the merchant account.",
    )
    nuvei_secret_key = fields.Char(
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        required_if_provider="nuvei",
        groups="base.group_system",
    )

    # === COMPUTE METHODS === #

    def _get_supported_currencies(self):
        """Override of `payment` to return the supported currencies."""
        supported_currencies = super()._get_supported_currencies()
        if self.code == "nuvei":
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        self.check_singleton()
        if self.code != "nuvei":
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === BUSINESS METHODS === #

    def _nuvei_get_api_url(self):
        if self.state == "enabled":
            return "https://secure.safecharge.com/ppp/purchase.do"
        else:  # 'test'
            return "https://ppp-test.safecharge.com/ppp/purchase.do"

    def _get_nuvei_signature(self, data, incoming=True):
        """Compute the signature for the provided data according to the Nuvei documentation.

        :param dict data: The data to sign.
        :param bool incoming: If the signature must be generated for an incoming (Nuvei to Odoo) or
                              outgoing (Odoo to Nuvei) communication.
        :return: The calculated signature.
        :rtype: str
        """
        self.check_singleton()
        signature_keys = const.SIGNATURE_KEYS if incoming else data.keys()
        sign_data = "".join([str(data.get(k, "")) for k in signature_keys])
        key = self.nuvei_secret_key
        signing_string = f"{key}{sign_data}"
        return hashlib.sha256(signing_string.encode()).hexdigest()
