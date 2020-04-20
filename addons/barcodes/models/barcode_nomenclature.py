import logging
import re
import datetime
import calendar

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

FNC1_CHAR = '\x1D'

UPC_EAN_CONVERSIONS = [
    ('none', 'Never'),
    ('ean2upc', 'EAN-13 to UPC-A'),
    ('upc2ean', 'UPC-A to EAN-13'),
    ('always', 'Always'),
]


class BarcodeNomenclature(models.Model):
    _name = 'barcode.nomenclature'
    _description = 'Barcode Nomenclature'

    name = fields.Char(string='Barcode Nomenclature', size=32, required=True, help='An internal identification of the barcode nomenclature')
    rule_ids = fields.One2many('barcode.rule', 'barcode_nomenclature_id', string='Rules', help='The list of barcode rules')
    upc_ean_conv = fields.Selection(UPC_EAN_CONVERSIONS, string='UPC/EAN Conversion', required=True, default='always',
        help="UPC Codes can be converted to EAN by prefixing them with a zero. This setting determines if a UPC/EAN barcode should be automatically converted in one way or another when trying to match a rule with the other encoding.")
    is_gs1_nomenclature = fields.Boolean(
        string="Is GS1 Nomenclature",
        help="This Nomenclature use the GS1 specification, only gs1-128 encoding rules is accept is this kind of nomenclature.")
    gs1_separator_fnc1 = fields.Char(
        string="FNC1 Seperator",
        help="Alternative regex delimiter for the FNC1 (by default, if not set, it is <GS> ascii 29 char). The seperator must not match the begin/end of any related rules pattern.")

    @api.constrains('gs1_separator_fnc1')
    def _check_pattern(self):
        for nom in self:
            if nom.is_gs1_nomenclature and nom.gs1_separator_fnc1 and nom.gs1_separator_fnc1.trim():
                try:
                    re.compile("(?:%s)?" % nom.gs1_separator_fnc1)
                except re.error as error:
                    raise ValidationError(_("The FNC1 Seperator Alternative is not a valid Regex : ") + str(error))

    @api.model
    def get_barcode_check_digit(self, numeric_barcode):
        """ Computes and returns the barcode check digit. The used algorithm
        follows the GTIN specifications and can be used by all compatible
        barcode nomenclature, like as EAN-8, EAN-12 (UPC-A) or EAN-13.

        https://www.gs1.org/sites/default/files/docs/barcodes/GS1_General_Specifications.pdf
        https://www.gs1.org/services/how-calculate-check-digit-manually

        :param numeric_barcode: the barcode to verify/recompute the check digit
        :type numeric_barcode: str
        :return: the number corresponding to the right check digit
        :rtype: int
        """
        code = list(numeric_barcode)

        # Multiply value of each position by
        # N1  N2  N3  N4  N5  N6  N7  N8  N9  N10 N11 N12 N13 N14 N15 N16 N17 N18
        # x3  X1  x3  x1  x3  x1  x3  x1  x3  x1  x3  x1  x3  x1  x3  x1  x3  CHECKSUM
        oddsum = evensum = total = 0
        code = code[-2::-1]  # Remove the check digit and reverse the barcode.
        # The CHECKSUM digit is removed because it will be recomputed and it must not interfer with
        # the computation. Also, the barcode is inverted, so the barcode length doesn't matter.
        # Otherwise, the digits' group (even or odd) could be different according to the barcode length.
        for i, n in enumerate(code):
            if i % 2 == 0:
                evensum += int(n)
            else:
                oddsum += int(n)
        total = evensum * 3 + oddsum
        return (10 - total % 10) % 10

    @api.model
    def check_encoding(self, barcode, encoding):
        """ Checks if the given barcode is correctly encoded.

        :return: True if the barcode string is encoded with the provided encoding.
        :rtype: bool
        """
        if encoding == "any":
            return True
        barcode_sizes = {
            'ean8': 8,
            'ean13': 13,
            'upca': 12,
        }
        barcode_size = barcode_sizes[encoding]
        return len(barcode) == barcode_size and re.match(r"^\d+$", barcode) and self.get_barcode_check_digit(barcode) == int(barcode[-1])

    @api.model
    def sanitize_ean(self, ean):
        """ Returns a valid zero padded EAN-13 from an EAN prefix.

        :type ean: str
        """
        ean = ean[0:13].zfill(13)
        return ean[0:-1] + str(self.get_barcode_check_digit(ean))

    @api.model
    def sanitize_upc(self, upc):
        """ Returns a valid zero padded UPC-A from a UPC-A prefix.

        :type upc: str
        """
        return self.sanitize_ean('0' + upc)[1:]

    def gs1_date_to_date(self, gs1_date):
        """Convert YYMMDD GS1 date into a datetime.date"""

        # Determination of century
        # https://www.gs1.org/sites/default/files/docs/barcodes/GS1_General_Specifications.pdf#page=474&zoom=100,66,113
        now = datetime.date.today()
        substract_year = int(gs1_date[0:2]) - (now.year % 100)
        century = (51 <= substract_year <= 99 and (now.year // 100) - 1) or (-99 <= substract_year <= -50 and (now.year // 100) + 1) or now.year // 100
        year = century * 100 + int(gs1_date[0:2])

        if gs1_date[-2:] == '00':  # Day is not mandatory, when not set -> last day of the month
            date = datetime.datetime.strptime(str(year) + gs1_date[2:4], '%Y%m')
            date = date.replace(day=calendar.monthrange(year, int(gs1_date[2:4]))[1])
        else:
            date = datetime.datetime.strptime(str(year) + gs1_date[2:4] + gs1_date[-2:], '%Y%m%d')
        return date.date()

    def parse_gs1_rule_pattern(self, match, rule):
        result = {
            'rule': rule,
            'ai': match.group(1),
            'string_value': match.group(2),
        }
        if rule.gs1_content_type == 'measure':
            decimal_position = 0  # Decimal position begin at the end, 0 means no decimal
            if rule.gs1_decimal_usage:
                decimal_position = int(match.group(1)[-1])
            if decimal_position > 0:
                result['value'] = float(match.group(2)[:-decimal_position] + "." + match.group(2)[-decimal_position:])
            else:
                result['value'] = int(match.group(2))
        elif rule.gs1_content_type == 'identifier':
            # Check digit and remove it of the value
            if match.group(2)[-1] != str(self.get_barcode_check_digit("0" * (18 - len(match.group(2))) + match.group(2))):
                return None
            result['value'] = match.group(2)
        elif rule.gs1_content_type == 'date':
            if len(match.group(2)) != 6:
                return None
            result['value'] = self.gs1_date_to_date(match.group(2))
        else:  # when gs1_content_type == 'alpha':
            result['value'] = match.group(2)
        return result

    def gs1_decompose_extanded(self, barcode):
        """Try to decompose the gs1 extanded barcode into several unit of information using gs1 rules.

        Return a ordered list of dict
        """
        self.ensure_one()
        separator_group = FNC1_CHAR + "?"
        if self.gs1_separator_fnc1 and self.gs1_separator_fnc1.trim():
            separator_group = "(?:%s)?" % self.gs1_separator_fnc1
        results = []
        gs1_rules = self.rule_ids.filtered(lambda r: r.encoding == 'gs1-128')

        def find_next_rule(remaining_barcode):
            for rule in gs1_rules:
                # is_variable_length = bool(re.search(r"\{\d?\,\d*\}", rule.pattern))  # TODO: don't catch * or + => maybe a use field or try with lookbehind
                match = re.search("^" + rule.pattern + separator_group, remaining_barcode)
                # If match and contains 2 groups at minimun, the first one need to be the IA and the second the value
                # We can't use regex nammed group because in JS, it is not the same regex syntax (and not compatible in all browser)
                if match and len(match.groups()) >= 2:
                    res = self.parse_gs1_rule_pattern(match, rule)
                    if res:
                        return res, remaining_barcode[match.end():]
            return None

        while len(barcode) > 0:
            res_bar = find_next_rule(barcode)
            # Cannot continue -> Fail to decompose gs1 and return
            if not res_bar or res_bar[1] == barcode:
                return None
            barcode = res_bar[1]
            results.append(res_bar[0])

        return results

    # Checks if barcode matches the pattern
    # Additionaly retrieves the optional numerical content in barcode
    # Returns an object containing:
    # - value: the numerical value encoded in the barcode (0 if no value encoded)
    # - base_code: the barcode in which numerical content is replaced by 0's
    # - match: boolean
    def match_pattern(self, barcode, pattern):
        match = {
            'value': 0,
            'base_code': barcode,
            'match': False,
        }

        barcode = barcode.replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.')
        numerical_content = re.search("[{][N]*[D]*[}]", pattern)  # look for numerical content in pattern

        if numerical_content:  # the pattern encodes a numerical content
            num_start = numerical_content.start()  # start index of numerical content
            num_end = numerical_content.end()  # end index of numerical content
            value_string = barcode[num_start:num_end - 2]  # numerical content in barcode

            whole_part_match = re.search("[{][N]*[D}]", numerical_content.group())  # looks for whole part of numerical content
            decimal_part_match = re.search("[{N][D]*[}]", numerical_content.group())  # looks for decimal part
            whole_part = value_string[:whole_part_match.end() - 2]  # retrieve whole part of numerical content in barcode
            decimal_part = "0." + value_string[decimal_part_match.start():decimal_part_match.end() - 1]  # retrieve decimal part
            if whole_part == '':
                whole_part = '0'
            match['value'] = int(whole_part) + float(decimal_part)

            match['base_code'] = barcode[:num_start] + (num_end - num_start - 2) * "0" + barcode[num_end - 2:]  # replace numerical content by 0's in barcode
            match['base_code'] = match['base_code'].replace("\\\\", "\\").replace("\\{", "{").replace("\\}", "}").replace("\\.", ".")
            pattern = pattern[:num_start] + (num_end - num_start - 2) * "0" + pattern[num_end:]  # replace numerical content by 0's in pattern to match

        match['match'] = re.match(pattern, match['base_code'][:len(pattern)])

        return match

    def parse_barcode(self, barcode):
        """ Attempts to interpret and parse a barcode.

        :param barcode:
        :type barcode: str
        :return: A object containing various information about the barcode, like as:
            - code: the barcode
            - type: the barcode's type
            - value: if the id encodes a numerical value, it will be put there
            - base_code: the barcode code with all the encoding parts set to
              zero; the one put on the product in the backend
        :rtype: dict
        """
        parsed_result = {
            'encoding': '',
            'type': 'error',
            'code': barcode,
            'base_code': barcode,
            'value': 0,
        }

        if self.is_gs1_nomenclature:
            return self.gs1_decompose_extanded(barcode)

        for rule in self.rule_ids:
            cur_barcode = barcode
            if rule.encoding == 'ean13' and self.check_encoding(barcode, 'upca') and self.upc_ean_conv in ['upc2ean', 'always']:
                cur_barcode = '0' + cur_barcode
            elif rule.encoding == 'upca' and self.check_encoding(barcode, 'ean13') and barcode[0] == '0' and self.upc_ean_conv in ['ean2upc', 'always']:
                cur_barcode = cur_barcode[1:]

            if not self.check_encoding(barcode, rule.encoding):
                continue

            match = self.match_pattern(cur_barcode, rule.pattern)
            if match['match']:
                if rule.type == 'alias':
                    barcode = rule.alias
                    parsed_result['code'] = barcode
                else:
                    parsed_result['encoding'] = rule.encoding
                    parsed_result['type'] = rule.type
                    parsed_result['value'] = match['value']
                    parsed_result['code'] = cur_barcode
                    # TODO: Encodings: ean8, ean13 and upca, but only check for ean13 and upca ?
                    # TODO: the sanitizing shouldn't be by the rule instead of the nomenclature ?
                    if rule.encoding == "ean13":
                        parsed_result['base_code'] = self.sanitize_ean(match['base_code'])
                    elif rule.encoding == "upca":
                        parsed_result['base_code'] = self.sanitize_upc(match['base_code'])
                    else:
                        parsed_result['base_code'] = match['base_code']
                    return parsed_result

        return parsed_result
