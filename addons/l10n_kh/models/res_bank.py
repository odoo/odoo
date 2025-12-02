# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
import time

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    proxy_type = fields.Selection(
        selection_add=[
            ('bakong_id_solo', "Bakong Account ID (Solo Merchant)"),
            ('bakong_id_merchant', "Bakong Account ID (Corporate Merchant)"),
        ],
        ondelete={'bakong_id_solo': 'set default', 'bakong_id_merchant': 'set default'},
    )
    l10n_kh_merchant_id = fields.Char("Merchant ID")

    @api.constrains('proxy_type', 'proxy_value')
    def _check_kh_proxy(self):
        bakong_id_re = re.compile(r"^[a-zA-Z0-9_].*@[a-zA-Z0-9_].*$")
        for bank in self.filtered(lambda b: b.country_code == 'KH'):
            if bank.proxy_type not in ['bakong_id_solo', 'bakong_id_merchant', 'none', False]:
                raise ValidationError(_("The proxy type must be Bakong Account ID"))
            if bank.proxy_type in ['bakong_id_solo', 'bakong_id_merchant'] and (not bank.proxy_value or not bakong_id_re.match(bank.proxy_value) or len(bank.proxy_value) > 32):
                raise ValidationError(_("Please enter a valid Bakong Account ID."))
            if bank.proxy_type == 'bakong_id_merchant' and not bank.l10n_kh_merchant_id:
                raise ValidationError(_("Merchant ID is missing."))

    def _get_qr_code_vals_list(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        res = super()._get_qr_code_vals_list(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)
        if self.country_code == 'KH':
            # Adds the timestamp. Format is {tag}{len}{str}
            timestamp = str(time.time_ns() // 1000000)
            # The expiry is optional and seems to be mostly for Bakong as it works without it in other bank apps.
            # But it works in all tested apps with it, so we will always include it. We'll make it expire in a month, should be long enough.
            expiry_timestamp = str((time.time_ns() // 1000000) + (1000 * 60 * 60 * 24 * 30))
            res.append(
                (99, f"00{len(timestamp)}{timestamp}01{len(expiry_timestamp)}{expiry_timestamp}"),
            )
        return res

    def _compute_display_qr_setting(self):
        bank_kh = self.filtered(lambda b: b.country_code == 'KH')
        bank_kh.display_qr_setting = self.env.company.qr_code
        super(ResPartnerBank, self - bank_kh)._compute_display_qr_setting()

    @api.depends('country_code')
    def _compute_country_proxy_keys(self):
        bank_kh = self.filtered(lambda b: b.country_code == 'KH')
        bank_kh.country_proxy_keys = 'bakong_id_solo,bakong_id_merchant'
        super(ResPartnerBank, self - bank_kh)._compute_country_proxy_keys()

    def _get_merchant_account_info(self):
        if self.country_code == 'KH':
            if self.proxy_type == 'bakong_id_solo':
                return 29, self._serialize(*(0, self.proxy_value))
            elif self.proxy_type == 'bakong_id_merchant':
                merchant_account_info = ''.join([self._serialize(*val) for val in [
                    (0, self.proxy_value),
                    (1, self.l10n_kh_merchant_id),
                    (2, self.bank_id.name),
                ]])
                return 30, merchant_account_info
        return super()._get_merchant_account_info()

    def _get_additional_data_field(self, comment):
        if self.country_code == 'KH':
            return self._serialize(1, comment)
        return super()._get_additional_data_field(comment)

    def _get_merchant_category_code(self):
        if self.country_code == 'KH':
            return '0001'
        return super()._get_merchant_category_code()

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        if qr_method == 'emv_qr' and self.country_code == 'KH':
            if currency.name not in ['KHR', 'USD']:
                return _("Can't generate a KHQR code with a currency other than KHR or USD.")
            return None

        return super()._get_error_messages_for_qr(qr_method, debtor_partner, currency)

    def _check_for_qr_code_errors(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == 'emv_qr' and self.country_code == 'KH' and self.proxy_type not in ['bakong_id_solo', 'bakong_id_merchant']:
            return _("The proxy type of KHQR must be a Bakong Account ID")

        return super()._check_for_qr_code_errors(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)
