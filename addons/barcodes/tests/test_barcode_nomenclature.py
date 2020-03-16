# -*- coding: utf-8 -*-
from odoo.tests import common


class TestBarcodeNomenclature(common.TransactionCase):

    def test_barcode_check_digit(self):
        barcode_nomenclature = self.env['barcode.nomenclature']
        ean8 = "87111125"
        self.assertEqual(barcode_nomenclature.get_barcode_check_digit("0" * 10 + ean8), int(ean8[-1]))
        ean13 = "1234567891231"
        self.assertEqual(barcode_nomenclature.get_barcode_check_digit("0" * 5 + ean13), int(ean13[-1]))
