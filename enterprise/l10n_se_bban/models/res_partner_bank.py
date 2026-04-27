# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from stdnum import luhn

from odoo import api, models, _

PLUSGIRO_ACCOUNT_NUMBER_RE = re.compile(r'^\d{1,7}-\d$')
BANKGIRO_ACCOUNT_NUMBER_RE = re.compile(r'^\d{3,5}-\d{2,5}$')
NOT_DIGIT_RE = re.compile(r'\D')


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    @api.model
    def _get_supported_account_types(self):
        rslt = super()._get_supported_account_types()
        rslt.extend([('plusgiro', _('Plusgiro')), ('bankgiro', _('Bankgiro')), ('bban_se', _('Swedish BBAN'))])
        return rslt

    def retrieve_acc_type(self, acc_number):
        if acc_number:
            if self._se_validate_plusgiro(acc_number):
                return 'plusgiro'
            elif self._se_validate_bankgiro(acc_number):
                return 'bankgiro'
            elif self._se_validate_bban(acc_number):
                return 'bban_se'
        return super().retrieve_acc_type(acc_number)

    def _se_validate_plusgiro(self, acc_number):
        """Validate PlusGiro number: format XXXXXXX-C (2-8 digits total), dash at end, Luhn checksum."""
        return PLUSGIRO_ACCOUNT_NUMBER_RE.match(acc_number.replace(' ', '')) and luhn.is_valid(NOT_DIGIT_RE.sub('', acc_number))

    def _se_validate_bankgiro(self, acc_number):
        """Validate BankGiro number: format XXXX-XXXC (7-8 digits total), dash in the middle, Luhn checksum last."""
        if not BANKGIRO_ACCOUNT_NUMBER_RE.match(acc_number.replace(' ', '')):
            return False
        only_digits = NOT_DIGIT_RE.sub('', acc_number)
        return 7 <= len(only_digits) <= 8 and luhn.is_valid(only_digits)

    def _se_validate_bban(self, acc_number):
        bank_code, account_number, checksum = self._se_get_acc_number_data(acc_number)
        if not all([bank_code, account_number, checksum]):
            return False
        return self._se_validate_domestic_account_format(checksum, bank_code, account_number)

    def _se_get_acc_number_data(self, acc_number):
        cleaned_acc_number = acc_number.replace(' ', '').replace(',', '').replace('-', '')

        if not cleaned_acc_number.isdigit():
            return False, False, False

        clearing_range = self.env['se.bban.clear.range'].search([
            ('min_num', '<=', int(cleaned_acc_number[:4])),
            ('max_num', '>=', int(cleaned_acc_number[:4])),
        ], limit=1)
        if not clearing_range:
            return False, False, False

        bank_code_length = 5 if clearing_range.checksum == 'mod10_max_10_digits_5' else 4
        bank_code = cleaned_acc_number[:bank_code_length]
        account_number = cleaned_acc_number[bank_code_length:]

        return bank_code, account_number, clearing_range.checksum

    def _se_validate_domestic_account_format(self, checksum, bank_code, account_number):
        def mod11_is_valid(number):
            """ Validate number with Mod11 with weights 1-10. It's valid when sum is a multiple of 11."""
            return not sum(int(n) * ((i % 10) + 1) for i, n in enumerate(number[::-1])) % 11

        # Type 1 accounts
        if checksum == 'mod11_10_digits':  # Validate account number with 10 digits using Mod11 checksum
            return len(account_number) == 7 and mod11_is_valid(bank_code[-3:] + account_number)
        elif checksum == 'mod11_11_digits':  # Validate account number with 11 digits using Mod11 checksum
            return len(account_number) == 7 and mod11_is_valid(bank_code + account_number)
        # Type 2 accounts
        elif checksum in {'mod10_max_10_digits', 'mod10_max_10_digits_5'}:  # Validate account number with up to 10 digits using Mod10 checksum
            return len(account_number) <= 10 and luhn.is_valid(account_number)
        elif checksum == 'mod10_10_digits':  # Validate account number with 10 digits using Mod10 checksum
            return len(account_number) == 10 and luhn.is_valid(account_number)
        elif checksum == 'mod11_9_digits':   # Validate account number with 9 digits using Mod11 checksum
            return len(account_number) == 9 and mod11_is_valid(account_number)
        elif checksum == 'mod11_8_9_digits':   # Validate account number with 8 or 9 digits using Mod11 checksum
            return len(account_number) in {8, 9} and mod11_is_valid(account_number)
        return False

    def _se_get_bban_from_iban(self):
        cleaned_acc_number = self.sanitized_acc_number[4:]
        clearing_number = 5 if cleaned_acc_number[0] == '8' else 4
        return cleaned_acc_number[clearing_number:].lstrip('0'), cleaned_acc_number[:clearing_number]
