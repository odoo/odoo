# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re


__all__ = ['check_barcode_encoding']


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
