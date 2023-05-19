# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import single_email_re


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    country_code = fields.Char(related='partner_id.country_code', string="Country Code")
    l10n_hk_fps_type = fields.Selection([('id', "FPS ID"), ('mobile', "Mobile Number"), ('email', "Email Address")], string='FPS Type')
    l10n_hk_fps_identifier = fields.Char(string="FPS Identifier", help="FPS ID, Mobile Number or Email Address")

    @api.constrains('l10n_hk_fps_type', 'l10n_hk_fps_identifier')
    def _check_l10n_hk_fps_identifier(self):
        auto_mobn_re = re.compile(r"^[+]\d{1,3}-\d{6,12}$")
        for bank in self:
            if bank.country_code != 'HK':
                continue
            if bank.l10n_hk_fps_type == 'id' and (not bank.l10n_hk_fps_identifier or len(bank.l10n_hk_fps_identifier) not in [7, 9]):
                raise ValidationError(_("Invalid FPS ID! Please enter a valid FPS ID with length 7 or 9."))
            if bank.l10n_hk_fps_type == 'mobile' and (not bank.l10n_hk_fps_identifier or not auto_mobn_re.match(bank.l10n_hk_fps_identifier)):
                raise ValidationError(_("Invalid Mobile! Please enter a valid mobile number with format +852-67891234."))
            if bank.l10n_hk_fps_type == 'email' and (not bank.l10n_hk_fps_identifier or not single_email_re.match(bank.l10n_hk_fps_identifier)):
                raise ValidationError(_("Invalid Email! Please enter a valid email address."))

    # Follow the documentation of FPS QR Code Standard [1]
    # [1]: https://www.hkma.gov.hk/media/eng/doc/key-functions/financial-infrastructure/infrastructure/retail-payment-initiatives/Common_QR_Code_Specification.pdf
    def _get_merchant_account_info(self):
        if self.country_code == 'HK':
            fps_type_mapping = {
                'id': '02',
                'mobile': '03',
                'email': '04'
            }
            fps_type_id = fps_type_mapping[self.l10n_hk_fps_type]
            fps_account = f'{fps_type_id}{len(self.l10n_hk_fps_identifier):02}{self.l10n_hk_fps_identifier}'
            return f'0012hk.com.hkicl{fps_account}'
        return super()._get_merchant_account_info()

    def _get_additional_data_field(self, comment):
        return f'05{len(comment):02}{comment}'

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        if qr_method == 'emv_qr' and self.country_code == 'HK':
            if currency.name not in ['HKD', 'CNY']:
                return _("Can't generate a FPS QR code with currency other than HKD or CNY.")
            return None

        return super()._get_error_messages_for_qr(qr_method, debtor_partner, currency)

    def _check_for_qr_code_errors(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == 'emv_qr' and self.country_code == 'HK' and (not self.l10n_hk_fps_type or not self.l10n_hk_fps_identifier):
            return _("The account receiving the payment must have a FPS type and a FPS identifier set.")

        return super()._check_for_qr_code_errors(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)
