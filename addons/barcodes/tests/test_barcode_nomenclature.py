# -*- coding: utf-8 -*-
from odoo.tests import common


class TestBarcodeNomenclature(common.TransactionCase):

    def test_barcode_check_digit(self):
        barcode_nomenclature = self.env['barcode.nomenclature']
        ean8 = "87111125"
        self.assertEqual(barcode_nomenclature.get_barcode_check_digit("0" * 10 + ean8), int(ean8[-1]))
        ean13 = "1234567891231"
        self.assertEqual(barcode_nomenclature.get_barcode_check_digit("0" * 5 + ean13), int(ean13[-1]))

    def test_gs1_date_to_date(self):
        barcode_nomenclature = self.env['barcode.nomenclature']
        # 20/10/2015 -> 151020
        date_gs1 = "151020"
        date = barcode_nomenclature.gs1_date_to_date(date_gs1)
        self.assertEqual(date.day, 20)
        self.assertEqual(date.month, 10)
        self.assertEqual(date.year, 2015)

        # XX/03/2052 -> 520300 -> (if day no set take last day of the month -> 31)
        date_gs1 = "520300"
        date = barcode_nomenclature.gs1_date_to_date(date_gs1)
        self.assertEqual(date.day, 31)
        self.assertEqual(date.month, 3)
        self.assertEqual(date.year, 2052)

        # XX/02/2020 -> 520200 -> (if day no set take last day of the month -> 29)
        date_gs1 = "200200"
        date = barcode_nomenclature.gs1_date_to_date(date_gs1)
        self.assertEqual(date.day, 29)
        self.assertEqual(date.month, 2)
        self.assertEqual(date.year, 2020)
