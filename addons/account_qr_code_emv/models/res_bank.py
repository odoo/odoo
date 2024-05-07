# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import _, api, fields, models
from odoo.tools.misc import remove_accents
from odoo.addons.account_qr_code_emv.const import CURRENCY_MAPPING


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    display_qr_setting = fields.Boolean(compute='_compute_display_qr_setting')
    include_reference = fields.Boolean(string="Include Reference", help="Include the reference in the QR code.")
    proxy_type = fields.Selection([('none', 'None')], string="Proxy Type", default='none')
    proxy_value = fields.Char(string="Proxy Value")

    @api.model
    def _serialize(self, header, value):
        if value is not None and value != '':
            return f'{header:02}{len(str(value)):02}{value}'
        else:
            return ''

    @api.model
    def _remove_accents(self, string):
        return remove_accents(string).replace('đ', 'd').replace('Đ', 'D')

    @api.depends('country_code')
    def _compute_display_qr_setting(self):
        self.display_qr_setting = False

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

    def _get_merchant_account_info(self):
        return None, None

    def _get_additional_data_field(self, comment):
        return None

    def _get_qr_code_vals_list(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        tag, merchant_account_info = self._get_merchant_account_info()
        currency_code = CURRENCY_MAPPING[currency.name]
        if not currency.is_zero(amount):
            amount = amount.is_integer() and int(amount) or amount
        else:
            amount = None
        merchant_name = self.partner_id.name and self._remove_accents(self.partner_id.name)[:25] or 'NA'
        merchant_city = self.partner_id.city and self._remove_accents(self.partner_id.city)[:15] or ''
        comment = structured_communication or free_communication or ''
        comment = re.sub(r'/[^ A-Za-z0-9_@.\/#&+-]+/g', '', remove_accents(comment))
        additional_data_field = self._get_additional_data_field(comment) if self.include_reference else None
        return [
            (0, '01'),                                                              # Payload Format Indicator
            (1, '12'),                                                              # Dynamic QR Codes
            (tag, merchant_account_info),                                           # Merchant Account Information
            (52, '0000'),                                                           # Merchant Category Code
            (53, currency_code),                                                    # Transaction Currency
            (54, amount),                                                           # Transaction Amount
            (58, self.country_code),                                                # Country Code
            (59, merchant_name),                                                    # Merchant Name
            (60, merchant_city),                                                    # Merchant City
            (62, additional_data_field),                                            # Additional Data Field
        ]

    def _get_qr_vals(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == 'emv_qr':
            qr_code_vals = self._get_qr_code_vals_list(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)
            qr_code_str = ''.join([self._serialize(*val) for val in qr_code_vals])
            qr_code_str += '6304'                                                   # CRC16
            crc = self._get_crc16(bytes(qr_code_str, 'utf-8'))
            qr_code_str += format(crc, '04x').upper()
            return qr_code_str

        return super()._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _get_qr_code_generation_params(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == 'emv_qr':
            return {
                'barcode_type': 'QR',
                'width': 128,
                'height': 128,
                'humanreadable': 1,
                'value': self._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication),
            }
        return super()._get_qr_code_generation_params(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _check_for_qr_code_errors(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == 'emv_qr':
            if not self._get_merchant_account_info():
                return _("Missing Merchant Account Information.")
            if not self.partner_id.city:
                return _("Missing Merchant City.")
            if not self.proxy_type:
                return _("Missing Proxy Type.")
            if not self.proxy_value:
                return _("Missing Proxy Value.")
        return super()._check_for_qr_code_errors(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    @api.model
    def _get_available_qr_methods(self):
        rslt = super()._get_available_qr_methods()
        rslt.append(('emv_qr', _("EMV Merchant-Presented QR-code"), 30))
        return rslt

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        """ Return an error for emv_qr if the account's country does no match any methods found in inheriting modules."""
        if qr_method == 'emv_qr':
            if not self:
                return _("A bank account is required for EMV QR Code generation.")
            return _("No EMV QR Code is available for the country of the account %(account_number)s.", account_number=self.acc_number)

        return super()._get_error_messages_for_qr(qr_method, debtor_partner, currency)
