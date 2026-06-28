# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.tools import check_barcode_encoding, get_barcode_check_digit
from odoo.tools.barcode import datamatrix_encode_ascii, ECC200DataMatrix


class TestBarcode(TransactionCase):
    def test_barcode_check_digit(self):
        ean8 = "87111125"
        self.assertEqual(get_barcode_check_digit("0" * 10 + ean8), int(ean8[-1]))
        ean13 = "1234567891231"
        self.assertEqual(get_barcode_check_digit("0" * 5 + ean13), int(ean13[-1]))

    def test_barcode_encoding(self):
        self.assertTrue(check_barcode_encoding('20220006', 'ean8'))
        self.assertTrue(check_barcode_encoding('93855341', 'ean8'))
        self.assertTrue(check_barcode_encoding('2022071416014', 'ean13'))
        self.assertTrue(check_barcode_encoding('9745213796142', 'ean13'))

        self.assertFalse(check_barcode_encoding('2022a006', 'ean8'), 'should contains digits only')
        self.assertFalse(check_barcode_encoding('20220000', 'ean8'), 'incorrect check digit')
        self.assertFalse(check_barcode_encoding('93855341', 'ean13'), 'ean13 is a 13-digits barcode')
        self.assertFalse(check_barcode_encoding('9745213796142', 'ean8'), 'ean8 is a 8-digits barcode')
        self.assertFalse(check_barcode_encoding('9745213796148', 'ean13'), 'incorrect check digit')
        self.assertFalse(check_barcode_encoding('2022!71416014', 'ean13'), 'should contains digits only')
        self.assertFalse(check_barcode_encoding('0022071416014', 'ean13'), 'when starting with one zero, it indicates that a 12-digit UPC-A code follows')

    def test_datamatrix_ascii_encoding(self):
        self.assertEqual(list(datamatrix_encode_ascii("2022071416014")), [150, 152, 137, 144, 146, 131, 53])
        self.assertEqual(list(datamatrix_encode_ascii("9745213796142")), [227, 175, 151, 167, 226, 144, 51])
        self.assertEqual(list(datamatrix_encode_ascii("abc123")), [98, 99, 100, 142, 52])

    def test_datamatrix_c40_encoding(self):
        def get_datamatrix(data):
            codewords = ECC200DataMatrix()._encode_c40(data)
            # Ignore the padding, which begins at the value 129 (after 254, the end of data)
            return codewords[: codewords.index(129, codewords.index(254))]

        # Values taken from `echo -n $CODE | dmtxwrite -s 44x44 -ec -c | grep '^d:'`
        self.assertEqual(get_datamatrix("123a"), [230, 32, 56, 254, 98])
        self.assertEqual(get_datamatrix("1234"), [230, 32, 56, 254, 53])
        self.assertEqual(get_datamatrix("1234a"), [230, 32, 56, 50, 82, 254])
        self.assertEqual(get_datamatrix("abc123"), [230, 12, 171, 12, 212, 32, 56, 254])

        self.assertEqual(get_datamatrix("2022071416014"), [230, 38, 39, 38, 44, 32, 134, 63, 38, 254, 53])
        self.assertEqual(get_datamatrix("9745213796142"), [230, 83, 1, 57, 54, 45, 134, 63, 81, 254, 51])
        self.assertEqual(
            get_datamatrix("011234567890510abcde"),
            [230, 25, 206, 38, 161, 57, 220, 77, 13, 57, 13, 12, 171, 12, 212, 13, 35, 254, 102],
        )
