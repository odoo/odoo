import re

from odoo import models, api, _
from odoo.exceptions import ValidationError


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    _IBAN_LENGTHS = {
        'AD': 24, 'AE': 23, 'AL': 28, 'AT': 20, 'AZ': 28, 'BA': 20, 'BE': 16,
        'BG': 22, 'BH': 22, 'BR': 29, 'BY': 28, 'CH': 21, 'CR': 22, 'CY': 28,
        'CZ': 24, 'DE': 22, 'DK': 18, 'DO': 28, 'EE': 20, 'ES': 24, 'FI': 18,
        'FO': 18, 'FR': 27, 'GB': 22, 'GE': 22, 'GI': 23, 'GL': 18, 'GR': 27,
        'GT': 28, 'HR': 21, 'HU': 28, 'IE': 22, 'IL': 23, 'IS': 26, 'IT': 27,
        'JO': 30, 'KW': 30, 'KZ': 20, 'LB': 28, 'LI': 21, 'LT': 20, 'LU': 20,
        'LV': 21, 'MC': 27, 'MD': 24, 'ME': 22, 'MK': 19, 'MR': 27, 'MT': 31,
        'MU': 30, 'NL': 18, 'NO': 15, 'OM': 23, 'PK': 24, 'PL': 28, 'PS': 29,
        'PT': 25, 'QA': 29, 'RO': 24, 'RS': 22, 'SA': 24, 'SE': 24, 'SI': 19,
        'SK': 24, 'SM': 27, 'TN': 24, 'TR': 26, 'UA': 29, 'VG': 24, 'XK': 20,
    }

    @staticmethod
    def _iban_check(iban):
        compact_iban = re.sub(r'[^A-Z0-9]', '', (iban or '').upper())
        rearranged = compact_iban[4:] + compact_iban[:4]
        numeric_iban = ''.join(str(int(char, 36)) if char.isalpha() else char for char in rearranged)

        remainder = 0
        for digit in numeric_iban:
            remainder = (remainder * 10 + int(digit)) % 97
        return remainder == 1

    @staticmethod
    def _normalize_iban(iban):
        return re.sub(r'[^A-Z0-9]', '', (iban or '').upper())

    @staticmethod
    def _pretty_iban(iban):
        compact = re.sub(r'[^A-Z0-9]', '', (iban or '').upper())

        
        if compact.startswith('ES') and len(compact) == 24:
            return f"{compact[:4]}-{compact[4:8]}-{compact[8:12]}-{compact[12:14]}-{compact[14:24]}"

        return '-'.join(compact[i:i + 4] for i in range(0, len(compact), 4))

    @api.constrains('acc_number')
    def _check_iban_validity(self):
        pattern = re.compile(r'^[A-Z]{2}\d{2}[A-Z0-9]+$')
        for bank in self:
            if not bank.acc_number:
                continue

            compact = self._normalize_iban(bank.acc_number)

            if not pattern.fullmatch(compact):
                raise ValidationError(_('El IBAN debe empezar con 2 letras válidas (país), 2 dígitos de control y el resto alfanumérico.'))

            country_code = compact[:2]
            expected_length = self._IBAN_LENGTHS.get(country_code)
            if not expected_length:
                raise ValidationError(_('El código de país del IBAN no es válido: %s') % country_code)

            if len(compact) != expected_length:
                raise ValidationError(_('Longitud de IBAN inválida para %s. Debe tener %s caracteres.') % (country_code, expected_length))

            if not self._iban_check(compact):
                raise ValidationError(_('El IBAN no es válido. Revise los dígitos de control.'))

    @api.model_create_multi
    def create(self, vals_list):
        pattern = re.compile(r'^[A-Z]{2}\d{2}[A-Z0-9]+$')
        for vals in vals_list:
            acc_number = vals.get('acc_number')
            if not acc_number:
                continue

            compact = self._normalize_iban(acc_number)
            country_code = compact[:2] if len(compact) >= 2 else False
            expected_length = self._IBAN_LENGTHS.get(country_code)

            if expected_length and pattern.fullmatch(compact) and len(compact) == expected_length and self._iban_check(compact):
                vals['acc_number'] = self._pretty_iban(compact)

        return super().create(vals_list)

    def write(self, vals):
        acc_number = vals.get('acc_number')
        if acc_number:
            pattern = re.compile(r'^[A-Z]{2}\d{2}[A-Z0-9]+$')
            compact = self._normalize_iban(acc_number)
            country_code = compact[:2] if len(compact) >= 2 else False
            expected_length = self._IBAN_LENGTHS.get(country_code)

            if expected_length and pattern.fullmatch(compact) and len(compact) == expected_length and self._iban_check(compact):
                vals['acc_number'] = self._pretty_iban(compact)

        return super().write(vals)