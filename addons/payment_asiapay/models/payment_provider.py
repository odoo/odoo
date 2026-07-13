# Part of Odoo. See LICENSE file for full copyright and licensing details.

from hashlib import new as hashnew

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_asiapay import const


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('asiapay', "AsiaPay")], ondelete={'asiapay': 'set default'}
    )
    asiapay_brand = fields.Selection(
        string="Asiapay Brand",
        help="The brand associated to your AsiaPay account.",
        selection=[("paydollar", "PayDollar"), ("pesopay", "PesoPay"),
                    ("siampay", "SiamPay"), ("bimopay", "BimoPay")],
        default='paydollar',
        required_if_provider='asiapay',
    )
    asiapay_merchant_id = fields.Char(
        string="AsiaPay Merchant ID",
        help="The Merchant ID solely used to identify your AsiaPay account.",
        required_if_provider='asiapay',
    )
    asiapay_secure_hash_secret = fields.Char(
        string="AsiaPay Secure Hash Secret",
        required_if_provider='asiapay',
        groups='base.group_system',
    )
    asiapay_secure_hash_function = fields.Selection(
        string="AsiaPay Secure Hash Function",
        help="The secure hash function associated to your AsiaPay account.",
        selection=[('sha1', "SHA1"), ('sha256', "SHA256"), ('sha512', 'SHA512')],
        default='sha1',
        required_if_provider='asiapay',
    )

    @api.depends('code')
    def _compute_view_configuration_fields(self):
        """ Override of payment to make the `available_currency_ids` field required.

        :return: None
        """
        super()._compute_view_configuration_fields()
        self.filtered(lambda p: p.code == 'asiapay').update({
            'require_currency': True,
        })

    # ==== CONSTRAINT METHODS ===#

    @api.constrains('available_currency_ids', 'state')
    def _limit_available_currency_ids(self):
        allowed_codes = set(const.CURRENCY_MAPPING.keys())
        for provider in self.filtered(lambda p: p.code == 'asiapay'):
            if len(provider.available_currency_ids) > 1 and provider.state != 'disabled':
                raise ValidationError(_("Only one currency can be selected by AsiaPay account."))

            unsupported_currency_codes = [
                currency.name
                for currency in provider.available_currency_ids
                if currency.name not in allowed_codes
            ]
            if provider.available_currency_ids.filtered(lambda c: c.name not in allowed_codes):
                raise ValidationError(_(
                    "AsiaPay does not support the following currencies: %(currencies)s.",
                    currencies=", ".join(unsupported_currency_codes),
                ))

    # === BUSINESS METHODS ===#

    def _asiapay_get_api_url(self):
        """ Return the URL of the API corresponding to the provider's state.

        :return: The API URL.
        :rtype: str
        """
        self.ensure_one()

        environment = 'production' if self.state == 'enabled' else 'test'
        api_urls = const.API_URLS[environment]
        return api_urls.get(self.asiapay_brand, api_urls['paydollar'])

    def _asiapay_calculate_signature(self, data, incoming=True):
        """ Compute the signature for the provided data according to the AsiaPay documentation.

        :param dict data: The data to sign.
        :param bool incoming: Whether the signature must be generated for an incoming (AsiaPay to
                              Odoo) or outgoing (Odoo to AsiaPay) communication.
        :return: The calculated signature.
        :rtype: str
        """
        signature_keys = const.SIGNATURE_KEYS['incoming' if incoming else 'outgoing']
        data_to_sign = [str(data[k]) for k in signature_keys] + [self.asiapay_secure_hash_secret]
        signing_string = '|'.join(data_to_sign)
        shasign = hashnew(self.asiapay_secure_hash_function)
        shasign.update(signing_string.encode())
        return shasign.hexdigest()

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'asiapay':
            return default_codes
        return const.DEFAULT_PAYMENT_METHODS_CODES
