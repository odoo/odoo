# -*- coding: utf-8 -*-
from odoo.tests import common


class TestBarcodeNomenclature(common.TransactionCase):

    def test_gs1_extanded_barcode_1(self):
        barcode_nomenclature = self.env['barcode.nomenclature'].browse(self.ref('barcodes.default_gs1_nomenclature'))
        # (01)94019097685457(10)33650100138(3102)002004(15)131018
        code128 = "01940190976854571033650100138\x1D310200200415131018"
        res = barcode_nomenclature.gs1_decompose_extanded(code128)
        self.assertEqual(len(res), 4)
        self.assertEqual(res[0]["ai"], "01")

        self.assertEqual(res[1]["ai"], "10")

        self.assertEqual(res[2]["ai"], "3102")
        self.assertEqual(res[2]["value"], 20.04)

        self.assertEqual(res[3]["ai"], "15")
        self.assertEqual(res[3]["value"].year, 2013)
        self.assertEqual(res[3]["value"].day, 18)
        self.assertEqual(res[3]["value"].month, 10)

        # (01)94019097685457(13)170119(30)17
        code128 = "0194019097685457131701193017"
        res = barcode_nomenclature.gs1_decompose_extanded(code128)
        self.assertEqual(len(res), 3)
        self.assertEqual(res[0]["ai"], "01")

        self.assertEqual(res[1]["ai"], "13")
        self.assertEqual(res[1]["value"].year, 2017)
        self.assertEqual(res[1]["value"].day, 19)
        self.assertEqual(res[1]["value"].month, 1)

        self.assertEqual(res[2]["ai"], "30")
        self.assertEqual(res[2]["value"], 17)
