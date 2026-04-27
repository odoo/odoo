# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models, _

from odoo.exceptions import ValidationError


# Regular expression used to parse the creditor identifiers in SDD scheme.
SDD_CREDITOR_IDENTIFIER_REGEX_PATTERN = r"(?P<country_code>[A-Z]{2})(?P<check_digits>\d{2})(?P<business_code>.{3})(?P<country_identifier>.{1,28})"

class ResCompany(models.Model):
    _inherit = 'res.company'

    sdd_creditor_identifier = fields.Char(string='SDD creditor identifier', help="SEPA Direct Debit creditor identifier of the company, given by the bank.")

    @api.constrains('sdd_creditor_identifier')
    def validate_sdd_creditor_identifier(self):
        for record in self:
            if not record.sdd_creditor_identifier:  # Allows resetting the creditor identifier to an empty field.
                continue

            if len(record.sdd_creditor_identifier) > 35:
                raise ValidationError(_("The creditor identifier exceeds the maximum length of 35 characters."))

            matcher = re.match(SDD_CREDITOR_IDENTIFIER_REGEX_PATTERN, record.sdd_creditor_identifier.upper())
            if matcher:
                country_code = matcher.group('country_code')
                check_digits = matcher.group('check_digits')
                country_identifier = matcher.group('country_identifier')

                test_str = re.sub('[^A-Z0-9]', '', country_identifier) + country_code + '00'
                converted_test_str = self._convert_sdd_test_str(test_str)

                if (98 - int(converted_test_str) % 97) != int(check_digits):  # Mod 97-10 validation test
                    raise ValidationError(_("Invalid creditor identifier. Make sure you made no typo."))
            else:
                raise ValidationError(_("Invalid creditor identifier. Wrong format."))

    @api.model
    def _convert_sdd_test_str(self, test_str):
        """ Returns a version of the string passed in parameters where all the letters
        have been replaced by numbers.
        """
        # Accordingly to the SEPA Direct Debit rulebook, letters are numbered from 10 (A) to 35 (Z)
        ascii_value_shift = 55  # ord('A') - ascii_value_shift = 10
        rslt = ''
        for char in test_str:
            if re.match('[A-Z]', char):
                # using the ascii value of the char to get its number for SDD
                rslt += str(ord(char) - ascii_value_shift)
            else:
                rslt += char
        return rslt
