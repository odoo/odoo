import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.barcode import check_barcode_encoding, get_barcode_check_digit

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
    _order = 'sequence asc, id'

    sequence = fields.Integer(string='Sequence')
    name = fields.Char(string='Barcode Nomenclature', required=True, help='An internal identification of the barcode nomenclature')
    active = fields.Boolean(default=True, help="Set active to false to not use this nomenclature")
    rule_ids = fields.One2many('barcode.rule', 'barcode_nomenclature_id', string='Rules', help='The list of barcode rules')
    upc_ean_conv = fields.Selection(
        UPC_EAN_CONVERSIONS, string='UPC/EAN Conversion', required=True, default='always',
        help="UPC Codes can be converted to EAN by prefixing them with a zero. This setting determines if a UPC/EAN barcode should be automatically converted in one way or another when trying to match a rule with the other encoding.")
    is_combined = fields.Boolean(
        string="Is Combined",
        help="A combined nomenclature allows to trigger multiple rules in one single barcode. For instance: GS1 and HIBC")
    separator_expr = fields.Char(
        string="FNC1 Separator", trim=False, default=r'(Alt029|#|\x1D)',
        help="Alternative regex delimiter for the FNC1. The separator must not match the begin/end of any related rules pattern.")
    pattern = fields.Char(string='Nomenclature Pattern', help="In addition of the rules, a barcode must match this pattern to be parsed by this nomenclature.")

    @api.constrains('separator_expr')
    def _check_pattern(self):
        for nom in self:
            if nom.is_combined and nom.separator_expr:
                try:
                    re.compile("(?:%s)?" % nom.separator_expr)
                except re.error as error:
                    error_message = _("The FNC1 Separator Alternative is not a valid Regex: ")
                    raise ValidationError(error_message + str(error))

    @api.model
    def sanitize_barcode(self, barcode, encoding):
        """ Ensures the given barcode is encoded with the chosen encoding.

        :param barcode:
        :type barcode: str
        :param encoding:
        :type encoding: str
        :return: the given barcode rightly encoded
        :rtype: str
        """
        barcode_sizes = {
            'ean8': 8,
            'ean13': 13,
            'gtin14': 14,
            'upca': 12,
            'sscc': 18,
        }
        barcode_size = barcode_sizes[encoding]
        barcode = barcode[0:barcode_size].ljust(barcode_size, '0')
        barcode = barcode[0:-1] + str(get_barcode_check_digit(barcode))
        return barcode

    def match_pattern(self, barcode, pattern):
        """Checks barcode matches the pattern and retrieves the optional numeric value in barcode.

        :param barcode:
        :type barcode: str
        :param pattern:
        :type pattern: str
        :return: an object containing:
            - value: the numerical value encoded in the barcode (0 if no value encoded)
            - base_code: the barcode in which numerical content is replaced by 0's
            - match: boolean
        :rtype: dict
        """
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
            if whole_part.isdigit():
                match['value'] = int(whole_part) + float(decimal_part)

                match['base_code'] = barcode[:num_start] + (num_end - num_start - 2) * "0" + barcode[num_end - 2:]  # replace numerical content by 0's in barcode
                match['base_code'] = match['base_code'].replace("\\\\", "\\").replace("\\{", "{").replace("\\}", "}").replace("\\.", ".")
                pattern = pattern[:num_start] + (num_end - num_start - 2) * "0" + pattern[num_end:]  # replace numerical content by 0's in pattern to match
        match['match'] = re.match(pattern, match['base_code'][:len(pattern)])

        return match

    def parse_rule_pattern(self, match, rule):
        decimal_position = 0
        results = []

        if not check_barcode_encoding(match.group(0), rule.encoding):
            # Matched barcode doesn't respect rule's encoding.
            return results

        for i in range(len(rule.rule_part_ids)):
            value = match.group(i + 1)
            rule_part = rule.rule_part_ids[i]
            result = {
                'rule': rule,
                'group': rule_part,
                'string_value': value,
                'encoding': 'any',
                'value': value,
                'base_code': match.group(0),
                'type': rule_part.type,
            }
            # Check if the value matches the rule's or the part's encoding.
            if rule_part.encoding != 'any' and value == self.sanitize_barcode(value, encoding=rule_part.encoding):
                result['encoding'] = rule_part.encoding
            elif rule.encoding != 'any' and value == self.sanitize_barcode(value, encoding=rule.encoding):
                result['encoding'] = rule.encoding

            if rule_part.type == 'decimal_position':
                result['value'] = int(value)
                decimal_position = result['value']
            elif rule_part.type == 'measure':
                if not value.isnumeric():
                    raise ValidationError(_(
                        "There is something wrong with the barcode rule \"%(rule_name)s\" pattern.\n"
                        "Check the possible matched values can only be digits, otherwise the value can't be casted as a measure.",
                        rule_name=rule.name))
                decimal_position = decimal_position or rule_part.decimal_position
                if decimal_position > 0:
                    integral = value[:-decimal_position]
                    decimal = value[-decimal_position:]
                    result['value'] = float(f'{integral}.{decimal}')
                else:
                    result['value'] = int(value)
            elif rule_part.type in {'date', 'expiration_date', 'pack_date', 'use_date'}:
                if len(value) != 6:
                    # TODO: Adapt to more format then only YYMMDD.
                    return None
                result['value'] = self.gs1_date_to_date(value)
            elif rule_part.type == 'product':
                if rule.encoding != 'any':
                    result['value'] = self.sanitize_barcode(value, encoding=rule.encoding)
                    result['encoding'] = rule.encoding
                elif rule.encoding == 'any' and rule_part.encoding != 'any':
                    result['value'] = self.sanitize_barcode(value, encoding=rule_part.encoding)
                    result['encoding'] = rule_part.encoding

            results.append(result)
        return results

    def parse_barcode(self, barcode):
        for nomenclature in self:
            result = []
            separator_group = FNC1_CHAR + "?"
            if nomenclature.separator_expr:
                separator_group = "(?:%s)?" % nomenclature.separator_expr

            while len(barcode) > 0:
                barcode_length = len(barcode)

                for rule in nomenclature.rule_ids:
                    match = re.search("^" + rule.pattern + separator_group, barcode)
                    if match and len(match.groups()) >= 2:
                        parsed_data = nomenclature.parse_rule_pattern(match, rule)
                        if parsed_data:
                            barcode = barcode[match.end():]
                            result += parsed_data
                            if len(barcode) == 0:
                                return result  # Barcode completly parsed, no need to keep looping.
                if len(barcode) == barcode_length:
                    break  # The barcode can't be parsed by this nomenclature.
        return []
