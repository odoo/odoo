# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    proxy_type = fields.Selection(selection_add=[('bakong_id_solo', "Bakong Account ID (Solo Merchant)"),
                                                 ('bakong_id_merchant', "Bakong Account ID (Corporate Merchant)")],
                                  ondelete={'bakong_id_solo': 'set default'})
    merchant_id = fields.Char("Merchant ID")

    # Follow the documentation of Bakong QR Code Guideline [1] and the NPM Package bakong-khqr [2]
    # [1]: https://bakong.nbc.gov.kh/download/KHQR%20Guideline.pdf
    # [2]: https://www.npmjs.com/package/bakong-khqr
    # Here we are adopting the "Solo Merchant or Individual" and "Corporate Merchant" standard
    @api.constrains('proxy_type', 'proxy_value', 'partner_id')
    def _check_kh_proxy(self):
        bakong_id_re = re.compile(r"^[a-zA-Z0-9_].*@[a-zA-Z0-9_].*$")
        for bank in self.filtered(lambda b: b.country_code == 'KH'):
            if bank.proxy_type not in ['bakong_id_solo', 'bakong_id_merchant', 'none', False]:
                raise ValidationError(_("The proxy type must Bakong Account ID"))
            if bank.proxy_type in ['bakong_id_solo', 'bakong_id_merchant'] and (not bank.proxy_value or not bakong_id_re.match(bank.proxy_value) or len(bank.proxy_value) > 32):
                raise ValidationError(_("Invalid Bakong Account ID Format. Please enter a valid Bakong Account ID."))
            if bank.proxy_type == 'bakong_id_merchant' and not bank.merchant_id:
                raise ValidationError(_("Merchant ID is missing."))

    @api.depends('country_code')
    def _compute_display_qr_setting(self):
        bank_kh = self.filtered(lambda b: b.country_code == 'KH')
        bank_kh.display_qr_setting = self.env.company.qr_code
        super(ResPartnerBank, self - bank_kh)._compute_display_qr_setting()

    def _get_merchant_account_info(self):
        if self.country_code == 'KH':
            if self.proxy_type == 'bakong_id_solo':
                merchant_account_vals = [
                    (0, self.proxy_value),
                ]
                merchant_account_info = ''.join([self._serialize(*val) for val in merchant_account_vals])
                return (29, merchant_account_info)

            if self.proxy_type == 'bakong_id_merchant':
                merchant_account_vals = [
                    (0, self.proxy_value),
                    (1, self.merchant_id),
                    (2, self.bank_id.name),
                ]
                merchant_account_info = ''.join([self._serialize(*val) for val in merchant_account_vals])
                return (30, merchant_account_info)

        return super()._get_merchant_account_info()

    def _get_additional_data_field(self, comment):
        if self.country_code == 'KH':
            # Return the Bill Number
            return self._serialize(1, comment)

        return super()._get_additional_data_field(comment)

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
