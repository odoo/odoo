from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import common


class TestBarcodeNomenclature(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Creates an empty nomenclature (rules will be added in the tests).
        cls.nomenclature = cls.env['barcode.nomenclature'].create({
            'name': 'Barcode Nomenclature Test',
        })

    def test_barcode_nomenclature_parse_barcode_ean8_01(self):
        """ Parses some barcodes with a simple EAN-8 barcode rule and checks the result.
        """
        self.env['barcode.rule'].create({
            'name': 'Rule Test #1',
            'barcode_nomenclature_id': self.nomenclature.id,
            'encoding': 'ean8',
            'rule_part_ids': [Command.create({
                'pattern': r'(\d{8})',
                'type': 'product',
            })]
        })

        # Must fail because too short.
        res = self.nomenclature.parse_barcode('0002')
        self.assertEqual(res, [])

        # Must fail because wrong checksum (last digit).
        res = self.nomenclature.parse_barcode('12345678')
        self.assertEqual(res, [])

        # Must pass (right number of digits, right checksum).
        res = self.nomenclature.parse_barcode('12345670')
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['base_code'], '12345670')
        self.assertEqual(res[0]['type'], 'product')
        self.assertEqual(res[0]['encoding'], 'ean8')
        self.assertEqual(res[0]['value'], '12345670')

        # Must pass (right number of digits, right checksum).
        res = self.nomenclature.parse_barcode('02003405')
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['base_code'], '02003405')
        self.assertEqual(res[0]['type'], 'product')
        self.assertEqual(res[0]['encoding'], 'ean8')
        self.assertEqual(res[0]['value'], '02003405')

    def test_barcode_nomenclature_parse_barcode_ean8_02_validation_error(self):
        """ Try to parse a barcode with a wrong barcode rule.
        """
        barcode_rule = self.env['barcode.rule'].create({
            'name': 'Rule Test #1',
            'barcode_nomenclature_id': self.nomenclature.id,
            'encoding': 'ean8',
        })

        with self.assertRaises(ValidationError), self.cr.savepoint():
            # Must fail because no catching groups.
            self.env['barcode.rule.part'].create({
                'rule_id': barcode_rule.id,
                'pattern': r'abc'
            })
        with self.assertRaises(ValidationError), self.cr.savepoint():
            # Must fail because too many catching groups.
            self.env['barcode.rule.part'].create({
                'rule_id': barcode_rule.id,
                'pattern': r'(abc)(123)'
            })
        with self.assertRaises(ValidationError), self.cr.savepoint():
            # Must fail because not a valid regex.
            self.env['barcode.rule.part'].create({
                'rule_id': barcode_rule.id,
                'pattern': r'abc)(123'
            })

        with self.assertRaises(ValidationError), self.cr.savepoint():
            # Must fail because '**' isn't even a valid regular expression.
            barcode_rule.pattern = '**>>>{ND}'
        # Allowed since it leads to a valid regular expression.
        barcode_rule.pattern = '..>>>{ND}'

    def test_barcode_nomenclature_parse_barcode_ean8_03_value(self):
        """ Parses some barcodes with a EAN-8 barcode rule who convert the
        barcode into value and checks the result.
        """
        self.env['barcode.rule'].create({
            'name': 'Rule Test #2',
            'barcode_nomenclature_id': self.nomenclature.id,
            'encoding': 'ean8',
            'rule_part_ids': [Command.create({
                'type': 'measure',
                'pattern': r'(\d{8})',
            })]
        })

        res = self.nomenclature.parse_barcode('0002')
        self.assertEqual(res, [], "Must fail because the barcode is too short")

        res = self.nomenclature.parse_barcode('12345678')
        self.assertEqual(res, [], "Must fail because the checksum digit is wrong")

        # Must pass (right number of digits, right checksum).
        res = self.nomenclature.parse_barcode('12345670')
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['base_code'], '12345670')
        self.assertEqual(res[0]['type'], 'measure')
        self.assertEqual(res[0]['encoding'], 'ean8')
        self.assertEqual(res[0]['value'], 12345670, "The barcode must be converted into value")

        # Must pass (right number of digits, right checksum).
        res = self.nomenclature.parse_barcode('02003405')
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['base_code'], '02003405')
        self.assertEqual(res[0]['type'], 'measure')
        self.assertEqual(res[0]['encoding'], 'ean8')
        self.assertEqual(res[0]['value'], 2003405, "The barcode must be converted into value")

    def test_barcode_nomenclature_parse_barcode_ean8_04_multiple_rules(self):
        """ Parses some barcodes with a nomenclature containing multiple EAN-8
        barcode rule and checks the right one is took depending of the pattern.
        """
        self.env['barcode.rule'].create({
            'name': 'Rule Test #1',
            'sequence': 1,
            'barcode_nomenclature_id': self.nomenclature.id,
            'encoding': 'ean8',
            'rule_part_ids': [
                Command.create({
                    'type': 'product',
                    'sequence': 1,
                    'encoding': 'ean8',
                    'pattern': r'(11\d{5})',
                }),
                Command.create({
                    'type': 'measure',
                    'sequence': 1,
                    'pattern': r'(\d)',
                })],
        })
        self.env['barcode.rule'].create({
            'name': 'Rule Test #2',
            'sequence': 2,
            'barcode_nomenclature_id': self.nomenclature.id,
            'encoding': 'ean8',
            'rule_part_ids': [
                Command.create({
                    'type': 'product',
                    'sequence': 1,
                    'pattern': r'(66\d{4})',
                }),
                Command.create({
                    'type': 'measure',
                    'sequence': 2,
                    'pattern': r'(\d{2})',
                })],
        })

        # Only fits the first barcode rule.
        res = self.nomenclature.parse_barcode('11012344')
        self.assertEqual(len(res), 2)
        product_data, quantity_data = res
        self.assertEqual(product_data['base_code'], '11012344')
        self.assertEqual(product_data['type'], 'product')
        self.assertEqual(product_data['encoding'], 'ean8')
        self.assertEqual(product_data['value'], '11012344')
        self.assertEqual(quantity_data['base_code'], '11012344')
        self.assertEqual(quantity_data['type'], 'measure')
        self.assertEqual(quantity_data['encoding'], 'any')
        self.assertEqual(quantity_data['value'], 4)

        # Only fits the second barcode rule.
        res = self.nomenclature.parse_barcode('66012344')
        self.assertEqual(len(res), 2)
        product_data, quantity_data = res
        self.assertEqual(product_data['base_code'], '66012344')
        self.assertEqual(product_data['type'], 'product')
        self.assertEqual(product_data['encoding'], 'ean8')
        self.assertEqual(product_data['value'], '66012306')
        self.assertEqual(quantity_data['base_code'], '66012344')
        self.assertEqual(quantity_data['type'], 'measure')
        self.assertEqual(quantity_data['encoding'], 'any')
        self.assertEqual(quantity_data['value'], 44)

        # Doesn't fit any barcode rule.
        res = self.nomenclature.parse_barcode('16012344')
        self.assertEqual(res, [])

    def test_barcode_nomenclature_parse_barcode_ean13_01(self):
        """ Parses some barcodes with a EAN-13 barcode rule who contains a value
        and checks the result.
        """
        barcode_rule = self.env['barcode.rule'].create({
            'name': 'Rule Test #3',
            'barcode_nomenclature_id': self.nomenclature.id,
            'encoding': 'ean13',
            'rule_part_ids': [
                Command.create({
                    'sequence': 1,
                    'pattern': r'(1\d{8})',
                    'type': 'product',
                }),
                Command.create({
                    'sequence': 2,
                    'pattern': r'(\d{3})\d',
                    'type': 'measure',
                    'decimal_position': 1,
                })],
        })
        self.assertEqual(barcode_rule.pattern, r'(1\d{8})(\d{3})\d')

        # Must fail because too short.
        res = self.nomenclature.parse_barcode('0002')
        self.assertEqual(res, [], "Must fail because the barcode is too short")

        # Must fail because wrong checksum (last digit).
        res = self.nomenclature.parse_barcode('12345678')
        self.assertEqual(res, [], "Must fail because the checksum digit is wrong")

        # Must pass (right number of digits, right checksum).
        res = self.nomenclature.parse_barcode('1020034051259')
        self.assertEqual(len(res), 2)
        product_data, quantity_data = res
        self.assertEqual(product_data['base_code'], '1020034051259')
        self.assertEqual(product_data['encoding'], 'ean13')
        self.assertEqual(product_data['type'], 'product')
        self.assertEqual(product_data['value'], '1020034050009')
        self.assertEqual(quantity_data['base_code'], '1020034051259')
        self.assertEqual(quantity_data['encoding'], 'any')
        self.assertEqual(quantity_data['type'], 'measure')
        self.assertEqual(quantity_data['value'], 12.5, "The '125' part should be converted into a measure with one decimal")

    def test_barcode_nomenclature_parse_barcode_ean13_02_sequence(self):
        """ Parses some barcodes with a nomenclature containing two EAN-13
        barcode rule and checks the good one is took depending of its sequence.
        """
        first_created_rule = self.env['barcode.rule'].create({
            'name': 'Rule Test #1',
            'barcode_nomenclature_id': self.nomenclature.id,
            'encoding': 'ean13',
            'pattern': '.....{NNNDDDD}.',
            'sequence': 3,
            'rule_part_ids': [
                Command.create({
                    'sequence': 1,
                    'pattern': r'(\d{5})',
                    'type': 'product',
                }),
                Command.create({
                    'sequence': 1,
                    'pattern': r'(\d{7})\d',
                    'type': 'measure',
                    'decimal_position': 4,
                }),
            ],
        })
        self.env['barcode.rule'].create({
            'name': 'Rule Test #2',
            'barcode_nomenclature_id': self.nomenclature.id,
            'encoding': 'ean13',
            'pattern': '22......{NNDD}.',
            'sequence': 2,
            'rule_part_ids': [
                Command.create({
                    'sequence': 1,
                    'pattern': r'(22\d{6})',
                    'type': 'product',
                }),
                Command.create({
                    'sequence': 1,
                    'pattern': r'(\d{4})\d',
                    'type': 'measure',
                    'decimal_position': 2,
                }),
            ],
        })

        # Invalids the cache to reset the nomenclature barcode rules' order.
        self.nomenclature.invalidate_recordset(['rule_ids'])

        # Only fits the second barcode rule.
        res = self.nomenclature.parse_barcode('2012345610255')
        self.assertEqual(len(res), 2)
        product_data, quantity_data = res
        self.assertEqual(product_data['base_code'], '2012345610255')
        self.assertEqual(product_data['type'], 'product')
        self.assertEqual(product_data['encoding'], 'ean13')
        self.assertEqual(product_data['value'], '2012300000008')
        self.assertEqual(quantity_data['base_code'], '2012345610255')
        self.assertEqual(quantity_data['type'], 'measure')
        self.assertEqual(quantity_data['encoding'], 'any')
        self.assertEqual(quantity_data['value'], 456.1025)

        # Fits the two barcode rules, but should take the second one (lower sequence).
        res = self.nomenclature.parse_barcode('2212345610259')
        self.assertEqual(len(res), 2)
        product_data, quantity_data = res
        self.assertEqual(product_data['base_code'], '2212345610259')
        self.assertEqual(product_data['type'], 'product')
        self.assertEqual(product_data['encoding'], 'ean13')
        self.assertEqual(product_data['value'], '2212345600007')
        self.assertEqual(quantity_data['base_code'], '2212345610259')
        self.assertEqual(quantity_data['type'], 'measure')
        self.assertEqual(quantity_data['encoding'], 'any')
        self.assertEqual(quantity_data['value'], 10.25)

        first_created_rule.sequence = 1
        # Invalids the cache to reset the nomenclature barcode rules' order.
        self.nomenclature.invalidate_recordset(['rule_ids'])

        # Should take the first one now (lower sequence).
        res = self.nomenclature.parse_barcode('2212345610259')
        self.assertEqual(len(res), 2)
        product_data, quantity_data = res
        self.assertEqual(product_data['base_code'], '2212345610259')
        self.assertEqual(product_data['type'], 'product')
        self.assertEqual(product_data['encoding'], 'ean13')
        self.assertEqual(product_data['value'], '2212300000002')
        self.assertEqual(quantity_data['base_code'], '2212345610259')
        self.assertEqual(quantity_data['type'], 'measure')
        self.assertEqual(quantity_data['encoding'], 'any')
        self.assertEqual(quantity_data['value'], 456.1025)

    def test_barcode_uri_conversion(self):
        """ This test ensures URIs are correctly converted into barcode data."""

        uri = 'urn:epc:class:lgtin : 4012345.012345.998877'
        barcode_data = self.nomenclature.parse_barcode(uri)
        self.assertEqual(len(barcode_data), 2)
        product_part, lot_part = barcode_data
        self.assertEqual(product_part['type'], 'product')
        self.assertEqual(product_part['value'], '04012345123456')
        self.assertEqual(lot_part['type'], 'lot')
        self.assertEqual(lot_part['value'], '998877')

        uri = 'urn:epc:id:sgtin:9521141.012345.4711'
        barcode_data = self.nomenclature.parse_barcode(uri)
        self.assertEqual(len(barcode_data), 2)
        product_part, serial_part = barcode_data
        self.assertEqual(product_part['type'], 'product')
        self.assertEqual(product_part['value'], '09521141123454')
        self.assertEqual(serial_part['type'], 'lot')
        self.assertEqual(serial_part['value'], '4711')

        uri = 'urn:epc:tag:sgtin-96 : 1.358378.0728089.620776'
        barcode_data = self.nomenclature.parse_barcode(uri)
        self.assertEqual(len(barcode_data), 2)
        product_part, serial_part = barcode_data
        self.assertEqual(product_part['type'], 'product')
        self.assertEqual(product_part['value'], '03583787280898')
        self.assertEqual(serial_part['type'], 'lot')
        self.assertEqual(serial_part['value'], '620776')

        uri = 'urn:epc:id:sscc:952656789012.03456'
        barcode_data = self.nomenclature.parse_barcode(uri)
        self.assertEqual(len(barcode_data), 1)
        self.assertEqual(barcode_data[0]['type'], 'package')
        self.assertEqual(barcode_data[0]['value'], '095265678901234568')
