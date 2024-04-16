from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestBarcodeGS1Nomenclature(TransactionCase):
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
        res = barcode_nomenclature.parse_barcode(code128)
        self.assertEqual(len(res), 9)
        self.assertEqual(res[0]["type"], "prefix")
        self.assertEqual(res[0]["value"], "01")
        self.assertEqual(res[1]["type"], "product")
        self.assertEqual(res[1]["value"], "94019097685457")
        self.assertEqual(res[2]["type"], "prefix")
        self.assertEqual(res[2]["value"], "10")
        self.assertEqual(res[3]["type"], "lot")
        self.assertEqual(res[3]["value"], "33650100138")
        self.assertEqual(res[4]["type"], "prefix")
        self.assertEqual(res[4]["value"], "310")
        self.assertEqual(res[5]["type"], "decimal_position")
        self.assertEqual(res[5]["value"], 2)
        self.assertEqual(res[6]["type"], "measure")
        self.assertEqual(res[6]["value"], 20.04)
        self.assertEqual(res[7]["type"], "prefix")
        self.assertEqual(res[7]["value"], "15")
        self.assertEqual(res[8]["type"], "use_date")
        self.assertEqual(res[8]["value"].year, 2013)
        self.assertEqual(res[8]["value"].month, 10)
        self.assertEqual(res[8]["value"].day, 18)

        # (01)94019097685457(13)170119(30)17
        code128 = "0194019097685457131701193017"
        res = barcode_nomenclature.parse_barcode(code128)
        self.assertEqual(len(res), 6)
        self.assertEqual(res[0]["type"], "prefix")
        self.assertEqual(res[0]["value"], "01")
        self.assertEqual(res[1]["type"], "product")
        self.assertEqual(res[1]["value"], "94019097685457")
        self.assertEqual(res[2]["type"], "prefix")
        self.assertEqual(res[2]["value"], "13")
        self.assertEqual(res[3]["type"], "pack_date")
        self.assertEqual(res[3]["value"].year, 2017)
        self.assertEqual(res[3]["value"].month, 1)
        self.assertEqual(res[3]["value"].day, 19)
        self.assertEqual(res[4]["type"], "prefix")
        self.assertEqual(res[4]["value"], "30")
        self.assertEqual(res[5]["type"], "measure")
        self.assertEqual(res[5]["value"], 17)

    def test_gs1_extanded_barcode_2_decimal(self):
        """ Parses multiples barcode with (or without) a decimal value and
        checks for each of them the value is correctly parsed.
        """
        # Configures a barcode GS1 nomenclature...
        barcode_nomenclature = self.env['barcode.nomenclature'].create({
            'name': "GS1 Nomenclature - Test",
            'is_combined': True,
        })
        # Creates a rule who don't take any decimal.
        barcode_rule = self.env['barcode.rule'].create({
            'name': "GS1 Rule Test - No Decimal",
            'barcode_nomenclature_id': barcode_nomenclature.id,
            'rule_part_ids': [
                Command.create({
                    'type': 'prefix',
                    'pattern': r'(300)',
                }),
                Command.create({
                    'type': 'measure',
                    'pattern': r'(\d{5,8})',
                }),
            ],
        })
        # Creates a rule to take the four last digit as decimals.
        self.env['barcode.rule'].create({
            'name': "GS1 Rule Test - Four Decimals",
            'barcode_nomenclature_id': barcode_nomenclature.id,
            'rule_part_ids': [
                Command.create({
                    'type': 'prefix',
                    'pattern': r'(30)',
                }),
                Command.create({
                    'type': 'decimal_position',
                    'pattern': r'(4)',
                }),
                Command.create({
                    'type': 'measure',
                    'pattern': r'(\d{5,8})',
                }),
            ],
        })

        # Checks barcodes without decimals.
        res = barcode_nomenclature.parse_barcode('30000000')
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]['type'], 'prefix')
        self.assertEqual(res[0]['value'], '300')
        self.assertEqual(res[1]['type'], 'measure')
        self.assertEqual(res[1]['value'], 0)

        res = barcode_nomenclature.parse_barcode('30018789')
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]['type'], 'prefix')
        self.assertEqual(res[0]['value'], '300')
        self.assertEqual(res[1]['type'], 'measure')
        self.assertEqual(res[1]['value'], 18789)

        res = barcode_nomenclature.parse_barcode('3001515000')
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]['type'], 'prefix')
        self.assertEqual(res[0]['value'], '300')
        self.assertEqual(res[1]['type'], 'measure')
        self.assertEqual(res[1]['value'], 1515000)

        # Checks barcodes with decimals.
        res = barcode_nomenclature.parse_barcode('30400000')
        self.assertEqual(len(res), 3)
        self.assertEqual(res[0]['type'], 'prefix')
        self.assertEqual(res[0]['value'], '30')
        self.assertEqual(res[1]['type'], 'decimal_position')
        self.assertEqual(res[1]['value'], 4)
        self.assertEqual(res[2]['type'], 'measure')
        self.assertEqual(res[2]['value'], 0.0)

        res = barcode_nomenclature.parse_barcode('30418789')
        self.assertEqual(len(res), 3)
        self.assertEqual(res[0]['type'], 'prefix')
        self.assertEqual(res[0]['value'], '30')
        self.assertEqual(res[1]['type'], 'decimal_position')
        self.assertEqual(res[1]['value'], 4)
        self.assertEqual(res[2]['type'], 'measure')
        self.assertEqual(res[2]['value'], 1.8789)

        res = barcode_nomenclature.parse_barcode('3041515000')
        self.assertEqual(len(res), 3)
        self.assertEqual(res[0]['type'], 'prefix')
        self.assertEqual(res[0]['value'], '30')
        self.assertEqual(res[1]['type'], 'decimal_position')
        self.assertEqual(res[1]['value'], 4)
        self.assertEqual(res[2]['type'], 'measure')
        self.assertEqual(res[2]['value'], 151.5)

        # Checks wrong configs will raise an exception.
        # The pattern is too permissive and can catch something which can't be casted as measurement
        barcode_rule.rule_part_ids[1].pattern = r'(.*)'
        with self.assertRaises(ValidationError):
            res = barcode_nomenclature.parse_barcode('300bilou4000')
