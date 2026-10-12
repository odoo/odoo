# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    proxy_type = fields.Selection(
        selection_add=[('merchant_id', "Merchant ID")],
        ondelete={'merchant_id': 'set default'},
    )
    l10n_mm_terminal_id = fields.Char(
        string="Terminal ID",
        help="Distinctive value associated to a terminal in the store. "
             "Keep it empty if the merchant has no terminal ID.",
    )
    l10n_mm_merchant_name = fields.Char(
        string="Merchant Name (Myanmar Unicode)",
        help="Merchant name in Myanmar Unicode, as displayed by the payer's mobile application.",
    )
    l10n_mm_merchant_city = fields.Char(
        string="Merchant City (Myanmar Unicode)",
        help="City in which the merchant transacts, in Myanmar Unicode. "
             "Defaults to the city of the account holder if not set.",
    )

    @api.constrains('proxy_type', 'proxy_value', 'l10n_mm_terminal_id')
    def _check_mm_proxy(self):
        for bank in self.filtered(lambda b: b.country_code == 'MM'):
            if bank.proxy_type not in ('merchant_id', 'none', False):
                raise ValidationError(_("The account identifier type of an MMQR code must be a Merchant ID."))
            if bank.proxy_type == 'merchant_id' and not (bank.proxy_value or '').isdigit():
                raise ValidationError(_("The Merchant ID of an MMQR code must only contain digits."))
            if bank.proxy_type == 'merchant_id' and len(bank.proxy_value) != 16:
                raise ValidationError(_(
                    "The Merchant ID of an MMQR code must be 16 digits long."
                ))
            if bank.l10n_mm_terminal_id and not re.fullmatch(r'\d{1,25}', bank.l10n_mm_terminal_id):
                raise ValidationError(_("The Terminal ID of an MMQR code must be at most 25 digits long."))

    @api.model
    def _get_emv_qr_code_names(self):
        return {**super()._get_emv_qr_code_names(), 'MM': _("MMQR Code")}

    @api.depends('country_code')
    def _compute_country_proxy_keys(self):
        bank_mm = self.filtered(lambda b: b.country_code == 'MM')
        bank_mm.country_proxy_keys = 'merchant_id'
        super(ResPartnerBank, self - bank_mm)._compute_country_proxy_keys()

    @api.depends('country_code')
    def _compute_display_qr_setting(self):
        bank_mm = self.filtered(lambda b: b.country_code == 'MM')
        bank_mm.display_qr_setting = True
        super(ResPartnerBank, self - bank_mm)._compute_display_qr_setting()

    # Follow the documentation of the Myanmar QR Code Standard [1]
    # [1]: https://myanmarpay.com.mm/frontend/assets/files/MyanmarQRSpecification.pdf
    def _get_merchant_account_info(self):
        if self.country_code == 'MM' and self.proxy_type == 'merchant_id':
            # The Merchant ID is assigned as 16 digits, but only its first 15 digits are populated in the QR code.
            merchant_account_vals = [
                (0, 'com.mmqrpay.www'),                                     # Globally Unique Identifier
                (1, self.proxy_value[:15]),                                 # Merchant ID
                (2, self.l10n_mm_terminal_id or '000000'),                  # Terminal ID
            ]
            return (26, ''.join(self._serialize(*val) for val in merchant_account_vals))
        return super()._get_merchant_account_info()

    def _get_additional_data_field(self, comment):
        if self.country_code == 'MM':
            return self._serialize(5, comment[:25])                         # Reference Label
        return super()._get_additional_data_field(comment)

    def _get_qr_code_vals_list(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        vals_list = super()._get_qr_code_vals_list(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)
        if self.country_code == 'MM':
            # The Merchant Information - Language Template
            merchant_info_vals = [
                (0, 'MY'),                                                             # Language Preference
                (1, (self.l10n_mm_merchant_name or '')[:25]),                          # Merchant Name - Myanmar Unicode
                (2, (self.l10n_mm_merchant_city or self.partner_id.city or '')[:15]),  # Merchant City - Myanmar Unicode
            ]
            vals_list.append((64, ''.join(self._serialize(*val) for val in merchant_info_vals)))
        return vals_list

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        if qr_method == 'emv_qr' and self.country_code == 'MM':
            if currency.name != 'MMK':
                return _("Can't generate an MMQR code with a currency other than MMK.")
            return None

        return super()._get_error_messages_for_qr(qr_method, debtor_partner, currency)

    def _check_for_qr_code_errors(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == 'emv_qr' and self.country_code == 'MM':
            if self.proxy_type != 'merchant_id':
                return _("The account identifier type of an MMQR code must be a Merchant ID.")
            if not self.l10n_mm_merchant_name:
                return _("Missing Merchant Name (Myanmar Unicode).")

        return super()._check_for_qr_code_errors(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)
