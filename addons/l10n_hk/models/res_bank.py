# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import single_email_re
from odoo.addons.l10n_hk.const import CURRENCY_MAPPING


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    country_code = fields.Char(related='partner_id.country_code', string="Country Code")
    l10n_hk_fps_type = fields.Selection([('id', "FPS ID"), ('mobile', "Mobile Number"), ('email', "Email Address")], string='FPS Type')
    l10n_hk_fps_identifier = fields.Char(string="FPS ID/Mobile Number/Email Address")

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

    # CRC16 calculation with polynomial 0x1021 and initial value 0xFFFF
    def _get_crc16(self, data, poly=0x1021, init=0xFFFF):
        crc = init
        for byte in data:
            crc = crc ^ (byte << 8)
            for __ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ poly
                else:
                    crc = crc << 1
        return crc & 0xFFFF

    def _get_qr_vals(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == 'emv_qr':
            merchant_account_info = self._get_merchant_account_info()
            currency_code = CURRENCY_MAPPING[currency.name]
            merchant_name = self.partner_id.name and self.partner_id.name[:25] or 'NA'
            merchant_city = self.partner_id.city and self.partner_id.city[:15] or ''

            qr_code_vals = [
                '000201',                                                           # Payload Format Indicator
                '010212',                                                           # Dynamic QR Codes
                f'26{len(merchant_account_info):02}{merchant_account_info}',        # Merchant Account Information
                '52040000',                                                         # Merchant Category Code
                f'5303{currency_code}',                                             # Transaction Currency
                f'54{len(str(amount)):02}{amount}',                                 # Transaction Amount
                f'5802{self.partner_id.country_code}',                              # Country Code
                f'59{len(merchant_name):02}{merchant_name}',                        # Merchant Name
                f'60{len(merchant_city):02}{merchant_city}',                        # Merchant City
                '6304',                                                             # CRC16
            ]
            crc = self._get_crc16(bytes(''.join(qr_code_vals), 'utf-8'))
            qr_code_vals.append(format(crc, '04x').upper())
            return qr_code_vals
        return super()._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _get_qr_code_generation_params(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == 'emv_qr':
            return {
                'barcode_type': 'QR',
                'width': 128,
                'height': 128,
                'humanreadable': 1,
                'value': ''.join(self._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)),
            }
        return super()._get_qr_code_generation_params(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    @api.model
    def _get_available_qr_methods(self):
        rslt = super()._get_available_qr_methods()
        rslt.append(('emv_qr', _("EMV Merchant-Presented QR-code"), 30))
        return rslt

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

    def _eligible_for_qr_code(self, qr_method, debtor_partner, currency, raises_error=True):
        if qr_method == 'emv_qr' and self.country_code == 'HK':
            return currency.name in ['HKD', 'CNY']

        return super()._eligible_for_qr_code(qr_method, debtor_partner, currency)

    def _check_for_qr_code_errors(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == 'emv_qr':
            if not self._get_merchant_account_info():
                return _("Missing Merchant Account Information.")
            if not self.partner_id.city:
                return _("Missing Merchant City.")

        if qr_method == 'emv_qr' and self.country_code == 'HK' and not self.l10n_hk_fps_type or not self.l10n_hk_fps_identifier:
            return _("The account receiving the payment must have a FPS type and a FPS identifier set.")

        return super()._check_for_qr_code_errors(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)
