# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import common
from odoo.exceptions import ValidationError


class TestValidateVat(common.TransactionCase):
    def setUp(self):
        super(TestValidateVat, self).setUp()
        self.partner = self.env['res.partner'].create({
            'country_id': False,
            'name': 'Test valid VAT',
        })

    def test_01_no_country_valid_vat(self):
        self.partner.vat = 'NL000099998B57'

    def test_02_no_country_invalid_vat(self):
        with self.assertRaises(ValidationError):
            self.partner.vat = 'NL000099998B0'

    def test_03_no_country_no_country_code(self):
        with self.assertRaises(ValidationError):
            self.partner.vat = '000099998B57'

    def test_04_different_country_valid_vat(self):
        self.partner.country_id = self.env.ref('base.de')
        self.partner.vat = 'NL000099998B57'

    def test_05_different_country_invalid_vat(self):
        self.partner.country_id = self.env.ref('base.de')
        with self.assertRaises(ValidationError):
            self.partner.vat = 'NL000099998B0'

    def test_06_matching_country_valid_vat(self):
        self.partner.country_id = self.env.ref('base.nl')
        self.partner.vat = 'NL000099998B57'

    def test_07_matching_country_no_country_code_valid_vat(self):
        self.partner.country_id = self.env.ref('base.nl')
        self.partner.vat = '000099998B57'

    def test_08_matching_country_no_country_code_invalid_vat(self):
        self.partner.country_id = self.env.ref('base.nl')
        with self.assertRaises(ValidationError):
            self.partner.vat = '000099998B0'
