from odoo.addons.barcodes.tests.test_barcode_nomenclature import TestBarcodeNomenclature
from odoo.exceptions import ValidationError


class TestBarcodeGS1Nomenclature(TestBarcodeNomenclature):
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

    def test_gs1_extanded_barcode_1(self):
        barcode_nomenclature = self.env['barcode.nomenclature'].browse(self.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature'))
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

    def test_gs1_extanded_barcode_2_decimal(self):
        """ Parses multiples barcode with (or without) a decimal value and
        checks for each of them the value is correctly parsed.
        """
        # Configures a barcode GS1 nomenclature...
        barcode_nomenclature = self.env['barcode.nomenclature'].create({
            'name': "GS1 Nomenclature - Test",
            'is_gs1_nomenclature': True,
        })
        default_barcode_rule_vals = {
            'default_encoding': 'gs1-128',
            'default_barcode_nomenclature_id': barcode_nomenclature.id,
            'default_type': 'quantity',
            'default_gs1_content_type': 'measure',
        }
        # Creates a rule who don't take any decimal.
        barcode_rule = self.env['barcode.rule'].with_context(default_barcode_rule_vals).create({
            'name': "GS1 Rule Test - No Decimal",
            'pattern': r'(300)(\d{5,8})',
            'gs1_decimal_usage': False,
        })
        # Creates a rule to take the four last digit as decimals.
        barcode_rule_decimal = self.env['barcode.rule'].with_context(default_barcode_rule_vals).create({
            'name': "GS1 Rule Test - Four Decimals",
            'pattern': r'(304)(\d{5,8})',
            'gs1_decimal_usage': True,
        })

        # Checks barcodes without decimals.
        res = barcode_nomenclature.gs1_decompose_extanded('30000000')
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['string_value'], '00000')
        self.assertEqual(res[0]['value'], 0)

        res = barcode_nomenclature.gs1_decompose_extanded('30018789')
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['string_value'], '18789')
        self.assertEqual(res[0]['value'], 18789)

        res = barcode_nomenclature.gs1_decompose_extanded('3001515000')
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['string_value'], '1515000')
        self.assertEqual(res[0]['value'], 1515000)

        # Checks barcodes with decimals.
        res = barcode_nomenclature.gs1_decompose_extanded('30400000')
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['string_value'], '00000')
        self.assertEqual(res[0]['value'], 0.0)

        res = barcode_nomenclature.gs1_decompose_extanded('30418789')
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['string_value'], '18789')
        self.assertEqual(res[0]['value'], 1.8789)

        res = barcode_nomenclature.gs1_decompose_extanded('3041515000')
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['string_value'], '1515000')
        self.assertEqual(res[0]['value'], 151.5)

        # Checks wrong configs will raise an exception.
        barcode_rule_decimal.pattern = r'()(\d{0,4})'
        # Barcode rule uses decimals but AI doesn't precise what is the decimal position.
        with self.assertRaises(ValidationError):
            res = barcode_nomenclature.gs1_decompose_extanded('1234')

        # The pattern is too permissive and can catch something which can't be casted as measurement
        barcode_rule.pattern = r'(300)(.*)'
        with self.assertRaises(ValidationError):
            res = barcode_nomenclature.gs1_decompose_extanded('300bilou4000')
