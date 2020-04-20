import logging
import re
import datetime
import calendar

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

FNC1_CHAR = '\x1D'

UPC_EAN_CONVERSIONS = [
    ('none','Never'),
    ('ean2upc','EAN-13 to UPC-A'),
    ('upc2ean','UPC-A to EAN-13'),
    ('always','Always'),
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

    def get_barcode_check_digit(self, numeric_barcode):
        """This algorithm is identical for all fixed length numeric GS1 data structures.

        It is also valid for ean8,12(upca),13 check digit after sanatizing.
        https://www.gs1.org/sites/default/files/docs/barcodes/GS1_General_Specifications.pdf

        `numeric_barcode` need to have a length of 18, and the last numeric char is the checksum (or '0')
        """
        code = list(numeric_barcode)
        if len(code) != 18:
            return -1

        # Multiply value of each position by
        # N1  N2  N3  N4  N5  N6  N7  N8  N9  N10 N11 N12 N13 N14 N15 N16 N17 N18
        # x3  X1  x3  x1  x3  x1  x3  x1  x3  x1  x3  x1  x3  x1  x3  x1  x3  CHECKSUM
        oddsum = evensum = total = 0
        code = code[:-1]  # Remove checksum
        for i in range(len(code)):
            if i % 2 == 0:
                evensum += int(code[i])
            else:
                oddsum += int(code[i])
        total = evensum * 3 + oddsum
        return int((10 - total % 10) % 10)

    # Returns true if the barcode string is encoded with the provided encoding.
    def check_encoding(self, barcode, encoding):
        if encoding == 'ean13':
            return len(barcode) == 13 and re.match(r"^\d+$", barcode) and self.get_barcode_check_digit("0" * 5 + barcode) == int(barcode[-1])
        elif encoding == 'upca':
            return len(barcode) == 12 and re.match(r"^\d+$", barcode) and self.get_barcode_check_digit("0" * 6 + barcode) == int(barcode[-1])
        elif encoding == 'ean8':
            return len(barcode) == 8 and re.match(r"^\d+$", barcode) and self.get_barcode_check_digit("0" * 10 + barcode) == int(barcode[-1])
        elif encoding == 'any':
            return True
        else:
            return False

    # Returns a valid zero padded ean13 from an ean prefix. the ean prefix must be a string.
    def sanitize_ean(self, ean):
        ean = ean[0:13]
        ean = ean + (13-len(ean))*'0'
        return ean[0:12] + str(self.get_barcode_check_digit("0" * 5 + ean))

    # Returns a valid zero padded UPC-A from a UPC-A prefix. the UPC-A prefix must be a string.
    def sanitize_upc(self, upc):
        return self.sanitize_ean('0'+upc)[1:]

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
            "value": 0,
            "base_code": barcode,
            "match": False,
        }

        barcode = barcode.replace("\\", "\\\\").replace("{", '\{').replace("}", "\}").replace(".", "\.")
        numerical_content = re.search("[{][N]*[D]*[}]", pattern) # look for numerical content in pattern

        if numerical_content: # the pattern encodes a numerical content
            num_start = numerical_content.start() # start index of numerical content
            num_end = numerical_content.end() # end index of numerical content
            value_string = barcode[num_start:num_end-2] # numerical content in barcode

            whole_part_match = re.search("[{][N]*[D}]", numerical_content.group()) # looks for whole part of numerical content
            decimal_part_match = re.search("[{N][D]*[}]", numerical_content.group()) # looks for decimal part
            whole_part = value_string[:whole_part_match.end()-2] # retrieve whole part of numerical content in barcode
            decimal_part = "0." + value_string[decimal_part_match.start():decimal_part_match.end()-1] # retrieve decimal part
            if whole_part == '':
                whole_part = '0'
            match['value'] = int(whole_part) + float(decimal_part)

            match['base_code'] = barcode[:num_start] + (num_end-num_start-2)*"0" + barcode[num_end-2:] # replace numerical content by 0's in barcode
            match['base_code'] = match['base_code'].replace("\\\\", "\\").replace("\{", "{").replace("\}","}").replace("\.",".")
            pattern = pattern[:num_start] + (num_end-num_start-2)*"0" + pattern[num_end:] # replace numerical content by 0's in pattern to match

        match['match'] = re.match(pattern, match['base_code'][:len(pattern)])

        return match

    # Attempts to interpret an barcode (string encoding a barcode)
    # It will return an object containing various information about the barcode.
    # most importantly : 
    #  - code    : the barcode
    #  - type   : the type of the barcode: 
    #  - value  : if the id encodes a numerical value, it will be put there
    #  - base_code : the barcode code with all the encoding parts set to zero; the one put on
    #                the product in the backend
    def parse_barcode(self, barcode):
        parsed_result = {
            'encoding': '', 
            'type': 'error', 
            'code': barcode, 
            'base_code': barcode, 
            'value': 0,
        }

        if self.is_gs1_nomenclature:
            return self.gs1_decompose_extanded(barcode)

        rules = []
        for rule in self.rule_ids:
            rules.append({'type': rule.type, 'encoding': rule.encoding, 'sequence': rule.sequence, 'pattern': rule.pattern, 'alias': rule.alias})

        for rule in rules:
            cur_barcode = barcode
            if rule['encoding'] == 'ean13' and self.check_encoding(barcode,'upca') and self.upc_ean_conv in ['upc2ean','always']:
                cur_barcode = '0'+cur_barcode
            elif rule['encoding'] == 'upca' and self.check_encoding(barcode,'ean13') and barcode[0] == '0' and self.upc_ean_conv in ['ean2upc','always']:
                cur_barcode = cur_barcode[1:]

            if not self.check_encoding(barcode,rule['encoding']):
                continue

            match = self.match_pattern(cur_barcode, rule['pattern'])
            if match['match']:
                if rule['type'] == 'alias':
                    barcode = rule['alias']
                    parsed_result['code'] = barcode
                else:
                    parsed_result['encoding'] = rule['encoding']
                    parsed_result['type'] = rule['type']
                    parsed_result['value'] = match['value']
                    parsed_result['code'] = cur_barcode
                    if rule['encoding'] == "ean13":
                        parsed_result['base_code'] = self.sanitize_ean(match['base_code'])
                    elif rule['encoding'] == "upca":
                        parsed_result['base_code'] = self.sanitize_upc(match['base_code'])
                    else:
                        parsed_result['base_code'] = match['base_code']
                    return parsed_result

        return parsed_result

class BarcodeRule(models.Model):
    _name = 'barcode.rule'
    _description = 'Barcode Rule'
    _order = 'sequence asc'

    name = fields.Char(string='Rule Name', size=32, required=True, help='An internal identification for this barcode nomenclature rule')
    barcode_nomenclature_id = fields.Many2one('barcode.nomenclature', string='Barcode Nomenclature')
    is_gs1_nomenclature = fields.Boolean(related="barcode_nomenclature_id.is_gs1_nomenclature")
    sequence = fields.Integer(string='Sequence', help='Used to order rules such that rules with a smaller sequence match first')
    encoding = fields.Selection([
                ('any', 'Any'),
                ('ean13', 'EAN-13'),
                ('ean8', 'EAN-8'),
                ('upca', 'UPC-A'),
                ('gs1-128', 'GS1-128')
        ], string='Encoding', required=True, default='any', help='This rule will apply only if the barcode is encoded with the specified encoding')
    type = fields.Selection([
            ('alias', 'Alias'),
            ('product', 'Unit Product'),
        ], string='Type', required=True, default='product')
    pattern = fields.Char(string='Barcode Pattern', size=32, help="The barcode matching pattern", required=True, default='.*')

    gs1_content_type = fields.Selection([
        ('date', 'Date'),  # To able to transform YYMMDD date into Odoo datetime
        ('measure', 'Measure'),  # UOM related
        ('identifier', 'Numeric Identifier'),  # When there is a numeric fixed length where there is a check digit ()
        ('alpha', 'Alpha-Numeric name'),
    ], string="GS1 Content Type")
    gs1_decimal_usage = fields.Boolean('Decimal', help="If True, use the last digit of IA to dertermine where the first decimal is")
    associated_uom_id = fields.Many2one('uom.uom')

    alias = fields.Char(string='Alias', size=32, default='0', help='The matched pattern will alias to this barcode', required=True)

    @api.constrains('pattern')
    def _check_pattern(self):
        for rule in self:
            if rule.encoding == 'gs1-128':
                try:
                    # Maybe check that the number of group == 2 ?
                    re.compile(rule.pattern)
                except re.error as error:
                    raise ValidationError(_("The rule pattern is not a valid Regex : ") + str(error))
                continue
            p = rule.pattern.replace("\\\\", "X").replace("\{", "X").replace("\}", "X")
            findall = re.findall("[{]|[}]", p) # p does not contain escaped { or }
            if len(findall) == 2:
                if not re.search("[{][N]*[D]*[}]", p):
                    raise ValidationError(_("There is a syntax error in the barcode pattern ") + rule.pattern + _(": braces can only contain N's followed by D's."))
                elif re.search("[{][}]", p):
                    raise ValidationError(_("There is a syntax error in the barcode pattern ") + rule.pattern + _(": empty braces."))
            elif len(findall) != 0:
                raise ValidationError(_("There is a syntax error in the barcode pattern ") + rule.pattern + _(": a rule can only contain one pair of braces."))
            elif p == '*':
                raise ValidationError(_(" '*' is not a valid Regex Barcode Pattern. Did you mean '.*' ?"))
