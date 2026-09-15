import hashlib

from odoo import fields, models

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_aps import const

_logger = get_payment_logger(__name__)


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("aps", "Amazon Payment Services")],
        ondelete={"aps": "set default"},
    )
    aps_merchant_identifier = fields.Char(
        string="APS Merchant Identifier",
        copy=False,
        required_if_provider="aps",
        help="The code of the merchant account to use with this provider.",
    )
    aps_access_code = fields.Char(
        string="APS Access Code",
        copy=False,
        required_if_provider="aps",
        groups="base.group_system",
        help="The access code associated with the merchant account.",
    )
    aps_sha_request = fields.Char(
        string="APS SHA Request Phrase",
        copy=False,
        required_if_provider="aps",
        groups="base.group_system",
    )
    aps_sha_response = fields.Char(
        string="APS SHA Response Phrase",
        copy=False,
        required_if_provider="aps",
        groups="base.group_system",
    )

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        self.check_singleton()
        if self.code != "aps":
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === BUSINESS METHODS === #

    def _aps_get_api_url(self):
        if self.state == "enabled":
            return "https://checkout.payfort.com/FortAPI/paymentPage"
        else:  # 'test'
            return "https://sbcheckout.payfort.com/FortAPI/paymentPage"

    def _get_aps_signature(self, data, incoming=True):
        """Compute the signature for the provided data according to the APS documentation.

        :param dict data: The data to sign.
        :param bool incoming: Whether the signature must be generated for an incoming (APS to Odoo)
                              or outgoing (Odoo to APS) communication.
        :return: The calculated signature.
        :rtype: str
        """
        sign_data = "".join(
            [f"{k}={v}" for k, v in sorted(data.items()) if k != "signature"]
        )
        key = self.aps_sha_response if incoming else self.aps_sha_request
        signing_string = key + sign_data + key
        return hashlib.sha256(signing_string.encode()).hexdigest()
