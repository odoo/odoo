import re

from odoo import models, fields, api


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
    upc_ean_conv = fields.Selection(
        UPC_EAN_CONVERSIONS, string='UPC/EAN Conversion', required=True, default='always',
        help="UPC Codes can be converted to EAN by prefixing them with a zero. This setting determines if a UPC/EAN barcode should be automatically converted in one way or another when trying to match a rule with the other encoding.")

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
        # Multiply value of each position by
        # N1  N2  N3  N4  N5  N6  N7  N8  N9  N10 N11 N12 N13 N14 N15 N16 N17 N18
        # x3  X1  x3  x1  x3  x1  x3  x1  x3  x1  x3  x1  x3  x1  x3  x1  x3  CHECKSUM
        oddsum = evensum = total = 0
        code = numeric_barcode[-2::-1]  # Remove the check digit and reverse the barcode.
        # The CHECKSUM digit is removed because it will be recomputed and it must not interfer with
        # the computation. Also, the barcode is inverted, so the barcode length doesn't matter.
        # Otherwise, the digits' group (even or odd) could be different according to the barcode length.
        for i, digit in enumerate(code):
            if i % 2 == 0:
                evensum += int(digit)
            else:
                oddsum += int(digit)
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
                    if rule.encoding == "ean13":
                        parsed_result['base_code'] = self.sanitize_ean(match['base_code'])
                    elif rule.encoding == "upca":
                        parsed_result['base_code'] = self.sanitize_upc(match['base_code'])
                    else:
                        parsed_result['base_code'] = match['base_code']
                    return parsed_result

        return parsed_result
