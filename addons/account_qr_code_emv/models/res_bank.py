# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import _, api, models

from odoo.addons.account_qr_code_emv.const import CURRENCY_MAPPING


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

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
        return False

    def _get_additional_data_field(self, comment):
        return False

    def _get_qr_vals(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == 'emv_qr':
            merchant_account_info = self._get_merchant_account_info()
            currency_code = CURRENCY_MAPPING[currency.name]
            merchant_name = self.partner_id.name and self.partner_id.name[:25] or 'NA'
            merchant_city = self.partner_id.city and self.partner_id.city[:15] or ''
            comment = structured_communication or free_communication or ''
            comment = re.sub(r'/[^ A-Za-z0-9_@.\/#&+-]+/g', '', comment)
            additional_data_field = self._get_additional_data_field(comment)

            qr_code_vals = [
                '000201',                                                                           # Payload Format Indicator
                '010212',                                                                           # Dynamic QR Codes
                f'26{len(merchant_account_info):02}{merchant_account_info}',                        # Merchant Account Information
                '52040000',                                                                         # Merchant Category Code
                f'5303{currency_code}',                                                             # Transaction Currency
                f'54{len(str(amount)):02}{amount}',                                                 # Transaction Amount
                f'5802{self.partner_id.country_code}',                                              # Country Code
                f'59{len(merchant_name):02}{merchant_name}',                                        # Merchant Name
                f'60{len(merchant_city):02}{merchant_city}',                                        # Merchant City
            ]

            if additional_data_field:
                qr_code_vals.append(f'62{len(additional_data_field):02}{additional_data_field}')    # Additional Data Field

            qr_code_vals.append('6304')                                                             # CRC16
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

    def _check_for_qr_code_errors(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == 'emv_qr':
            if not self._get_merchant_account_info():
                return _("Missing Merchant Account Information.")
            if not self.partner_id.city:
                return _("Missing Merchant City.")
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
