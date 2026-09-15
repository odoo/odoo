from hashlib import new as hashnew

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_asiapay import const


class PaymentProvider(models.Model):
    _inherit = "payment.provider"
    _CREDENTIAL_FIELDS = {
        "asiapay_secure_hash_secret": "asiapay_secure_hash_secret",
    }

    code = fields.Selection(
        selection_add=[("asiapay", "AsiaPay")],
        ondelete={"asiapay": "set default"},
    )
    asiapay_brand = fields.Selection(
        selection=[
            ("paydollar", "PayDollar"),
            ("pesopay", "PesoPay"),
            ("siampay", "SiamPay"),
            ("bimopay", "BimoPay"),
        ],
        default="paydollar",
        copy=False,
        required_if_provider="asiapay",
        help="The brand associated to your AsiaPay account.",
    )
    asiapay_merchant_id = fields.Char(
        string="AsiaPay Merchant ID",
        copy=False,
        required_if_provider="asiapay",
        help="The Merchant ID solely used to identify your AsiaPay account.",
    )
    asiapay_secure_hash_secret = fields.Char(
        string="AsiaPay Secure Hash Secret",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        required_if_provider="asiapay",
        groups="base.group_system",
    )
    asiapay_secure_hash_function = fields.Selection(
        selection=[("sha1", "SHA1"), ("sha256", "SHA256"), ("sha512", "SHA512")],
        string="AsiaPay Secure Hash Function",
        default="sha1",
        copy=False,
        required_if_provider="asiapay",
        help="The secure hash function associated to your AsiaPay account.",
    )

    # ==== CONSTRAINT METHODS ===#

    @api.constrains("available_currency_ids", "state")
    def _limit_available_currency_ids(self):
        allowed_codes = set(const.CURRENCY_MAPPING.keys())
        for provider in self.filtered(lambda p: p.code == "asiapay"):
            if (
                len(provider.available_currency_ids) > 1
                and provider.state != "disabled"
            ):
                raise ValidationError(
                    _("Only one currency can be selected by AsiaPay account.")
                )

            unsupported_currency_codes = [
                currency.name
                for currency in provider.available_currency_ids
                if currency.name not in allowed_codes
            ]
            if provider.available_currency_ids.filtered(
                lambda c: c.name not in allowed_codes
            ):
                raise ValidationError(
                    _(
                        "AsiaPay does not support the following currencies: %(currencies)s.",
                        currencies=", ".join(unsupported_currency_codes),
                    )
                )

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        self.check_singleton()
        if self.code != "asiapay":
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === BUSINESS METHODS ===#

    def _asiapay_get_api_url(self):
        """Return the URL of the API corresponding to the provider's state.

        :return: The API URL.
        :rtype: str
        """
        self.check_singleton()

        environment = "production" if self.state == "enabled" else "test"
        api_urls = const.API_URLS[environment]
        return api_urls.get(self.asiapay_brand, api_urls["paydollar"])

    def _get_asiapay_signature(self, data, incoming=True):
        """Compute the signature for the provided data according to the AsiaPay documentation.

        :param dict data: The data to sign.
        :param bool incoming: Whether the signature must be generated for an incoming (AsiaPay to
                              Odoo) or outgoing (Odoo to AsiaPay) communication.
        :return: The calculated signature.
        :rtype: str
        """
        signature_keys = const.SIGNATURE_KEYS["incoming" if incoming else "outgoing"]
        data_to_sign = [str(data[k]) for k in signature_keys] + [
            self.asiapay_secure_hash_secret
        ]
        signing_string = "|".join(data_to_sign)
        shasign = hashnew(self.asiapay_secure_hash_function)
        shasign.update(signing_string.encode())
        return shasign.hexdigest()
