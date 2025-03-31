import re

from odoo import models, fields, api
from odoo.tools.barcode import check_barcode_encoding, get_barcode_check_digit


UPC_EAN_CONVERSIONS = [
    ('none', 'Never'),
    ('ean2upc', 'EAN-13 to UPC-A'),
    ('upc2ean', 'UPC-A to EAN-13'),
    ('always', 'Always'),
]


class BarcodeNomenclature(models.Model):
    _name = 'barcode.nomenclature'
    _description = 'Barcode Nomenclature'

    name = fields.Char(string='Barcode Nomenclature', required=True, help='An internal identification of the barcode nomenclature')
    rule_ids = fields.One2many('barcode.rule', 'barcode_nomenclature_id', string='Rules', help='The list of barcode rules')
    upc_ean_conv = fields.Selection(
        UPC_EAN_CONVERSIONS, string='UPC/EAN Conversion', required=True, default='always',
        help="UPC Codes can be converted to EAN by prefixing them with a zero. This setting determines if a UPC/EAN barcode should be automatically converted in one way or another when trying to match a rule with the other encoding.")

    @api.model
    def sanitize_ean(self, ean):
        """ Returns a valid zero padded EAN-13 from an EAN prefix.

        :type ean: str
        """
        ean = ean[0:13].zfill(13)
        return ean[0:-1] + str(get_barcode_check_digit(ean))

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
            if whole_part.isdigit():
                match['value'] = int(whole_part) + float(decimal_part)

                match['base_code'] = barcode[:num_start] + (num_end - num_start - 2) * "0" + barcode[num_end - 2:]  # replace numerical content by 0's in barcode
                match['base_code'] = match['base_code'].replace("\\\\", "\\").replace("\\{", "{").replace("\\}", "}").replace("\\.", ".")
                pattern = pattern[:num_start] + (num_end - num_start - 2) * "0" + pattern[num_end:]  # replace numerical content by 0's in pattern to match
        match['match'] = re.match(pattern, match['base_code'][:len(pattern)])

        return match

    def parse_barcode(self, barcode):
        if re.match(r'^urn:', barcode):
            return self.parse_uri(barcode)
        return self.parse_nomenclature_barcode(barcode)

    def parse_nomenclature_barcode(self, barcode):
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
            if rule.encoding == 'ean13' and check_barcode_encoding(barcode, 'upca') and self.upc_ean_conv in ['upc2ean', 'always']:
                cur_barcode = '0' + cur_barcode
            elif rule.encoding == 'upca' and check_barcode_encoding(barcode, 'ean13') and barcode[0] == '0' and self.upc_ean_conv in ['ean2upc', 'always']:
                cur_barcode = cur_barcode[1:]

            if not check_barcode_encoding(barcode, rule.encoding):
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

    # RFID/URI stuff.
    @api.model
    def parse_uri(self, barcode):
        """ Convert supported URI format (lgtin, sgtin, sgtin-96, sgtin-198,
        sscc and ssacc-96) into a GS1 barcode.
        :param barcode str: the URI as a string.
        :rtype: str
        """
        if not re.match(r'^urn:', barcode):
            return barcode
        identifier, data = (bc_part.strip() for bc_part in re.split(':', barcode)[-2:])
        data = re.split(r'\.', data)
        match identifier:
            case 'lgtin' | 'sgtin':
                barcode = self._convert_uri_gtin_data_into_tracking_number(barcode, data)
            case 'sgtin-96' | 'sgtin-198':
                # Same as SGTIN but we have to remove the filter.
                barcode = self._convert_uri_gtin_data_into_tracking_number(barcode, data[1:])
            case 'sscc':
                barcode = self._convert_uri_sscc_data_into_package(barcode, data)
            case 'sscc-96':
                # Same as SSCC but we have to remove the filter.
                barcode = self._convert_uri_sscc_data_into_package(barcode, data[1:])
        return barcode

    @api.model
    def _convert_uri_gtin_data_into_tracking_number(self, base_code, data):
        gs1_company_prefix, item_ref_and_indicator, tracking_number = data
        indicator = item_ref_and_indicator[0]
        item_ref = item_ref_and_indicator[1:]
        product_barcode = indicator + gs1_company_prefix + item_ref
        product_barcode += str(get_barcode_check_digit(product_barcode + '0'))
        return [
            {
                'base_code': base_code,
                'code': product_barcode,
                'encoding': '',
                'type': 'product',
                'value': product_barcode,
            },
            {
                'base_code': base_code,
                'code': tracking_number,
                'encoding': '',
                'type': 'lot',
                'value': tracking_number,
            },
        ]

    @api.model
    def _convert_uri_sscc_data_into_package(self, base_code, data):
        gs1_company_prefix, serial_reference = data
        extension = serial_reference[0]
        serial_ref = serial_reference[1:]
        sscc = extension + gs1_company_prefix + serial_ref
        sscc += str(get_barcode_check_digit(sscc + '0'))
        return [{
            'base_code': base_code,
            'code': sscc,
            'encoding': '',
            'type': 'package',
            'value': sscc,
        }]
