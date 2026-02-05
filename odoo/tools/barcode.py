# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

try:
    from reportlab.graphics.barcode.ecc200datamatrix import ECC200DataMatrix
except ImportError:
    ECC200DataMatrix = None


def datamatrix_encode_ascii(value):
    """Encode ASCII data in a list of integer of ASCII value + 1.
    Digit pairs are encoded as 130 + numeric value.
    https://en.wikipedia.org/wiki/Data_Matrix#Encoding
    https://www.icao.int/publications/Documents/9303_p13_cons_en.pdf

    :param str value: the value to encode
    :yield int: encoded codeword
    """
    i = 0
    while i < len(value):
        c = value[i]
        if c.isdigit() and i + 1 < len(value) and value[i + 1].isdigit():
            yield 130 + int(value[i : i + 2])
            i += 2
        else:
            yield ord(c) + 1
            i += 1


def _encode_c40(self, value):
    encoded = []
    for c in value:
        c40_char = self._encode_c40_char(c)
        encoded.extend(c40_char)

    # First codeword is to Switch to C40 encodation
    codewords = [230]

    # C40 encode chunks of 3 alphanumeric characters into 2 bytes.
    # When the last chunk is not 3 bytes wide, it must be encoded in ASCII mode.
    length, remaining = divmod(len(encoded), 3)
    for i in range(length):
        total = encoded[i * 3] * 1600 + encoded[i * 3 + 1] * 40 + encoded[i * 3 + 2] + 1
        codewords.extend(divmod(total, 256))

    codewords.append(254)  # Switch to ASCII encodation
    if remaining:
        index = 1 if remaining == len(c40_char) == 2 else remaining
        # encode remaining data in ASCII mode
        codewords.extend(datamatrix_encode_ascii(value[-index:]))

    if len(codewords) > self.cw_data:
        raise Exception("Too much data to fit into a data matrix of this size")

    if len(codewords) < self.cw_data:
        codewords.append(129)  # End of data
        # Add padding to fill the datamatrix entirely
        while len(codewords) < self.cw_data:
            r = ((149 * (len(codewords) + 1)) % 253) + 1
            codewords.append((129 + r) % 254)

    return codewords


if ECC200DataMatrix is not None:
    ECC200DataMatrix._encode_c40 = _encode_c40


def get_barcode_check_digit(numeric_barcode):
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
    oddsum = evensum = 0
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


def check_barcode_encoding(barcode, encoding):
    """ Checks if the given barcode is correctly encoded.
    :return: True if the barcode string is encoded with the provided encoding.
    :rtype: bool
    """
    encoding = encoding.lower()
    if encoding == "any":
        return True
    barcode_sizes = {
        'ean8': 8,
        'ean13': 13,
        'gtin14': 14,
        'upca': 12,
        'sscc': 18,
    }
    barcode_size = barcode_sizes[encoding]
    return (encoding != 'ean13' or barcode[0] != '0') \
           and len(barcode) == barcode_size \
           and re.match(r"^\d+$", barcode) \
           and get_barcode_check_digit(barcode) == int(barcode[-1])
