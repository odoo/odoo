import urllib.parse

from odoo.addons.gs1_epc_nomenclature.models.gs1_epc_utils import _search_partition_table, write_bits, ascii_to_bits, bits_to_ascii
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class Gs1EpcTemplateField(models.Model):
    _name = 'gs1.epc.template.field'
    _description = 'Electronic Product Code Field Template'
    _order = 'sequence asc, id'

    name = fields.Char(string='Field Name', required=True, help='EPC Scheme Field Name')
    sequence = fields.Integer(string='Sequence', required=True, help='Used to order fields in the Scheme Template')
    scheme_template_ids = fields.Many2many(string='Scheme', comodel_name='gs1.epc.template.scheme', required=False)  # Not required for 'header' field
    bit_size_min = fields.Integer(string='Minimal Size in Bits', required=True, default=0)
    bit_size_max = fields.Integer(string='Maximal Size in Bits', required=True, default=0)
    padding = fields.Selection(string='Padding', default='none', selection=[
        ('none', 'None'),
        ('left', 'Left'),
        ('right', 'Right')],)
    encoding = fields.Selection(
        string='Encoding Method', required=True, default='integer', selection=[
            ('integer', 'Integer'),
            ('string', 'String'),
            ('partition_table', 'Partition Table'),
            ('unpadded_partition_table', 'Unpadded Partition Table'),
            ('string_partition_table', 'String Partition Table'),
            ('numeric_string', 'Numeric String'),
            ('6bit', '6-bit CAGE/DODAAC'),
            ('6bit_var_string', '6-bit Variable String'),
            ('6bit_var_string_partition_table', '6-bit Variable String Partition Table'),
            ('fixed_width_integer', 'Fixed Width Integer'),
            #  >= TDS 2.0
            ('aidc_toggle_bit', '+AIDC Toggle Bit'),
            ('fixed_bit_len_integer', 'Fixed-Bit-Length Integer'),
            ('prioritised_date', 'Prioritised Date'),
            ('fixed_len_numeric', 'Fixed-Length Numeric'),
            ('delimited_numeric', 'Delimited/Terminated Numeric'),
            ('var_len_alphanumeric', 'Variable-Length Alphanumeric'),
            ('single_data_bit', 'Single Data Bit'),
            ('6digit_date', '6-Digit Date YYMMDD'),
            ('10digit_datetime', '10-Digit Datetime YYMMDDhhmm'),
            ('var_format_date', 'Variable-Format Date / Date Range'),
            ('var_precision_datetime', 'Variable-Precision Datetime'),
            ('country_code', 'Country Code ISO 3166-1 Alpha-2'),
            ('var_len_integer_no_indicator', 'Variable-Length Integer Without Encoding Indicator'),
            ('opt_minus_bit', 'Optional Minus Sign In Bit'),
            #  Non-official, technical
            ('blank', 'Blank Filler'),
            ('aidc_header', 'AIDC Header'),  # TODO : May be replace by a special case 'Partition Table'
            ('sub_encoding', 'Sub-Encoding'),  # Some fields encoding is only known at runtime
        ], help='Encoding/Decoding method used to parse the field.')
    uri_portion = fields.Char(string='EPC Tag URI Portion', required=False)

    def _process_field(self, field, operation):
        """
        Process the given field using the specified operation method.

        Args:
            field (object): The field to be processed.
            operation (str): The operation to perform ('encode' or 'decode').

        Raises:
            Exception: If an error occurs while processing the field.
            AttributeError: If the specified operation method does not exist.

        Returns:
            None
        """
        method_name = f'_{operation}_{field.encoding}'
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            try:
                method(field)
            except Exception as e:
                raise Exception(f"An error occurred while {operation} with method '{method_name}': {e}")
        else:
            raise AttributeError(f"The {operation} method '{method_name}' does not exist.")

    def decode(self, field):
        """
        Decode the given field.

        Args:
            field (object): The field to be decoded.

        Raises:
            Exception: If an error occurs while decoding the field.
            AttributeError: If the specified encoding method does not exist.

        Returns:
            None
        """
        self._process_field(field, 'decode')

    def encode(self, field):
        """
        Encode the given field.

        Args:
            field: The field to encode.

        Raises:
            AttributeError: If the _encode_<encoding> method does not exist.
            Exception: If an error occurs during the execution of the encoding method.
        """
        self._process_field(field, 'encode')


    def _encode_integer(self, field):
        field.raw_value = write_bits(int(field.value), field.bit_size)

    def _encode_string(self, field):
        formatted_value = ascii_to_bits(urllib.parse.unquote(field.value))
        field.raw_value = write_bits(formatted_value, field.bit_size, word_size_write=7, pad_side='right')  # TODO : compute/inverse : handle in _set method of field

    def _decode_integer(self, field):
        field.value = field.raw_value
        if field.char_size != 0:
            field.value = field.value.rjust(field.char_size, '0')

    def _decode_string(self, field):
        normalized_bits = write_bits(int(field.raw_value), int(field.bit_size/7*8), word_size_write=8, word_size_read=7)
        unescaped_string = bits_to_ascii(normalized_bits)
        field.value = urllib.parse.quote(unescaped_string, safe='')

    # encode & decode methods for partition tables
    def _encode_partition_table(self, field):
        next_fields = field._get_next_field(depth=2, strict=True)
        field_lengths = [len(field.value) for field in next_fields]
        partition_key = _search_partition_table(field.partition_table, left_digit=field_lengths[0], right_digit=field_lengths[1], as_dict=True)[0]
        field.raw_value = write_bits(int(partition_key.get("value")), field.bit_size)
        next_fields[0].bit_size = partition_key.get("left_bit")
        next_fields[1].bit_size = partition_key.get("right_bit")

    def _decode_partition_table(self, field):
        # decode integer => lookup table
        partition_key = _search_partition_table(field.partition_table, value=field.raw_value, as_dict=True)[0]
        next_fields = field._get_next_field(depth=2, strict=True)
        # Set length of the next fields
        next_fields[0].bit_size = partition_key.get("left_bit")
        next_fields[0].char_size = partition_key.get("left_digit")
        next_fields[1].bit_size = partition_key.get("right_bit")
        next_fields[1].char_size = partition_key.get("right_digit")

    def _decode_aidc_header(self, field):
        #  Decode the GS1 AI Code (8 to 16 bits to read)
        #  Lookup Table -> return the encoding method for aidc_data
        pass


    def _encode_blank(self, field):
        field.raw_value = write_bits(0, field.bit_size)

    def _decode_blank(self, field):
        field.value = ''
