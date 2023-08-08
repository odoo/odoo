# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.tools import check_barcode_encoding, get_barcode_check_digit


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
