from functools import wraps
from lxml import etree
import math
import re


from odoo.tools.misc import file_path

DEFAULT_BIT_WORD_SIZE = 8
LSBF = 'little'
MSBF = 'big'
DEFAULT_ENDIAN = MSBF
LOOKUP_TABLE_PATH = file_path('gs1_epc_nomenclature/data/epc_lookup_table.xml')

__all__ = [
    'get_uri_body_elements',
    'get_uri_header',
    '_get_lookup_table',
    '_get_partition_table',
    '_search_partition_table',
    '_parse_xml_as_dict',
    'write_bits',
    'extract_bits',
    '_parse_ascii_string',
    'ascii_to_bits',
    'bits_to_ascii',
]

def xml_to_dict(func):
    @wraps(func)
    def wrapper_func(*args, **kwargs):
        as_dict = kwargs.pop('as_dict', False)
        xml_element = func(*args, **kwargs)
        if as_dict:
            return _parse_xml_as_dict(xml_element)
        return xml_element
    return wrapper_func


def get_uri_body_elements(uri):
    """
    Extract the body's elements of a given GS1 URI as a list.
    Example : 'urn:epc:id:sgln:123.456.789' => ['123', '456', '789']

    Parameters:
        uri (str): The URI to be processed.

    Returns:
        list: A list of strings representing the URI body elements.
    """
    uri_body = uri.split(':')[-1]
    return uri_body.split('.')

def get_uri_header(uri):
    """
    Extract the header of a given GS1 URI as a string.
    Example : 'urn:epc:id:sgln:123.456.789' => 'sgln''

    Parameters:
        uri (str): The URI to be processed.

    Returns:
        string: The header of the URI.
    """
    return uri.split(':')[-2]


def _get_lookup_table():
    return etree.parse(LOOKUP_TABLE_PATH)


@xml_to_dict
def _get_partition_table(table_name):
    tree = _get_lookup_table()
    return tree.xpath(f"//lookup_table/partition/{table_name}/")


@xml_to_dict
def _search_partition_table(table_name, value=None, left_bit=None, left_digit=None, right_bit=None, right_digit=None):
    tree = _get_lookup_table()
    xpath_query = f"//lookup_table/partition/{table_name}/key"
    conditions = []
    if value is not None:
        conditions.append(f"@value='{value}'")
    if left_bit is not None:
        conditions.append(f"@left_bit='{left_bit}'")
    if left_digit is not None:
        conditions.append(f"@left_digit='{left_digit}'")
    if right_bit is not None:
        conditions.append(f"@right_bit='{right_bit}'")
    if right_digit is not None:
        conditions.append(f"@right_digit='{right_digit}'")

    if conditions:
        xpath_query += "[" + " and ".join(conditions) + "]"

    return tree.xpath(xpath_query)


def _parse_xml_as_dict(element):
    """Return a list of dicts"""
    def _element_to_dict(elem):
        node = {}
        # Process element's attributes
        if elem.attrib:
            node.update((k, v) for k, v in elem.attrib.items())
        # Process element's children
        for child in elem:
            child_dict = _element_to_dict(child)
            if child.tag not in node:
                node[child.tag] = child_dict
            else:
                if not isinstance(node[child.tag], list):
                    node[child.tag] = [node[child.tag]]
                node[child.tag].append(child_dict)
        # Process element's text content
        if elem.text and elem.text.strip():
            text = elem.text.strip()
            if node:
                node['text'] = text
            else:
                node = text
        return node

    if isinstance(element, list):
        return [_element_to_dict(elem) for elem in element]
    return _element_to_dict(element)


def write_bits(value, length, pad_side='left', pad_char='0', word_size_write=DEFAULT_BIT_WORD_SIZE, word_size_read=DEFAULT_BIT_WORD_SIZE, word_pad_side='left', word_pad_char='0'):  # in_word_size, out_word_size
    """
    Converts an integer value to its binary representation with a specified length and padding side.

    Args:
        value (int): The integer value to be converted.
        length (int): The desired length of the binary representation.
        pad_side (str, optional): The side on which to pad the final binary representation ('left' or 'right'). Default is 'left'.
        pad_char (str, optional): The character to use for padding. Default is '0'.
        word_size (int, optional): The fixed size of the binary representation of each word. Default is 8. Must be in [1,7].
        N.B. Actually, EPC nomenclature rely on 8-bit words encoding on inputs (ASCII, ...).
        word_pad_side (str, optional): The side on which to pad the final binary representation of each word ('left' or 'right'). Default is 'left'.
        word_pad_char (str, optional): The character to use for word padding. Default is '0'.
    Returns:
        str: The binary representation of the value with the specified length.
            If the length is less than the actual length of the binary representation,
            leading or trailing zeros are added to make it the desired length.

    Raises:
        ValueError: If the value cannot be represented with the specified length.

    Example:
        write_bits(5, 8) -> '00000101'
        write_bits(5, 8, pad_side='right') -> '10100000'
    """
    if length <= 0:
        raise ValueError("Length must be a positive integer")
    if  word_size_write <= 0 :
        raise ValueError("Word size must be a positive integer")
    tot_bits = value.bit_length()
    if tot_bits > length:
        raise ValueError(f"Value {value} cannot be represented with {length} bits")
    if pad_side not in ['left', 'right']:
        raise ValueError(f"Invalid pad_side '{pad_side}'. Use 'left' or 'right'.")
    if word_pad_side not in ['left', 'right']:
        raise ValueError(f"Invalid word_pad_side '{word_pad_side}'. Use 'left' or 'right'.")
    if pad_char not in ['0', '1']:
        raise ValueError(f"Invalid pad_char '{pad_char}'. Use '0' or '1'.")
    if word_pad_char not in ['0', '1']:
        raise ValueError(f"Invalid word_pad_char '{word_pad_char}'. Use '0' or '1'.")
    if not isinstance(value, int):
        raise ValueError(f"Value '{value}' must be an integer")


    if length <= word_size_write or word_size_write == word_size_read:
        bit_string = f"{value:{pad_char}{length}b}"
    else:
        smaller = word_size_write < word_size_read
        word_number = math.ceil(tot_bits / word_size_read)
        normalized_bits = word_number * word_size_read
        default_bit_string = f"{value:{0}{normalized_bits}b}"
        bit_array = []
        for i in range(word_number):
            word = default_bit_string[word_size_read*i:word_size_read*(i+1)]
            if smaller:
                if int(word[:word_size_read-word_size_write], 2) != 0:
                    raise ValueError(f"Binary value {word} cannot be represented with {word_size_write} bits")
                bit_array.append(word[word_size_read-word_size_write:])
            elif word_pad_side == 'left':
                bit_array.append(word.rjust(word_size_write, word_pad_char))
            else:
                bit_array.append(word.ljust(word_size_write, word_pad_char))
        bit_string = ''.join(bit_array)

    if pad_side == 'left':
        padded_bit_string = bit_string.rjust(length, pad_char)  # May seem confusing but rjust = right justify, it so means that the string is padded on the left
    else:  # pad_side == 'right':
        padded_bit_string = bit_string.ljust(length, pad_char)

    return padded_bit_string


def extract_bits(value, length, offset = 0):
    tot_bits = value.bit_length()
    if offset > tot_bits:
        raise ValueError("Offset cannot be greater than the total number of bits")
    if length == 0:
        return 0
    shift = tot_bits - length - offset
    res = value >> shift
    res &= (1 << length) - 1
    return res


def _parse_ascii_string(input_string):
    """
    A function that decodes '%xx' encoded characters in an input string and transforms it into a byte literal.
    Example : '32a%2Fb' => b'32a\x2Fb'

    Args:
        input_string (str): The input string containing '%xx' encoded characters.

    Returns:
        bytes: The transformed byte string with decoded characters.
    """
    # Define the pattern to match '%xx' where xx is a two-digit hex number
    pattern = r"%([0-9A-Fa-f]{2})"

    def decode_match(match):
        hex_value = match.group(1)
        return chr(int(hex_value, 16))

    # Replace all '%xx' with their corresponding characters
    decoded_string = re.sub(pattern, decode_match, input_string)
    return int.from_bytes(decoded_string.encode('ascii'), byteorder=DEFAULT_ENDIAN)

def ascii_to_bits(input_string):
    return int.from_bytes(input_string.encode('ascii'), byteorder=DEFAULT_ENDIAN)

def bits_to_ascii(input_bitstring):
    return int(input_bitstring, 2).to_bytes((len(input_bitstring) + 7) // 8, byteorder=DEFAULT_ENDIAN).decode('ascii', errors="replace").replace("\x00", "")
