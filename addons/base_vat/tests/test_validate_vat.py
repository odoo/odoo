# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError
from unittest.mock import patch

import stdnum.eu.vat


class TestStructure(TransactionCase):
    @classmethod
    def setUpClass(cls):
        def check_vies(vat_number):
            return {'valid': vat_number == 'BE0477472701'}

        super().setUpClass()
        cls.env.user.company_id.vat_check_vies = False
        cls._vies_check_func = check_vies

    def test_all_formats(self):
        partner = self.env['res.partner'].create({'name': "Dummy partner"})
        commands = [
            ({'country_id': self.env.ref('base.at').id, 'vat': 'ATU12345674'}, False, 'AT'),
            ({'country_id': self.env.ref('base.at').id, 'vat': 'ATU12345675'}, True, 'AT'),
            ({'country_id': self.env.ref('base.au').id, 'vat': '11 225 459 587'}, False, 'AU'),
            ({'country_id': self.env.ref('base.au').id, 'vat': '11 225 459 588'}, True, 'AU'),
            ({'country_id': self.env.ref('base.ch').id, 'vat': 'CHE-123.456.788'}, False, 'CH'),
            ({'country_id': self.env.ref('base.ch').id, 'vat': 'CHE-123.456.788 IVA'}, True, 'CH'),
            ({'country_id': self.env.ref('base.ec').id, 'vat': 'EC1792060347-001'}, False, 'EC'),
            ({'country_id': self.env.ref('base.ec').id, 'vat': 'EC1792060346-001'}, True, 'EC'),
            ({'country_id': self.env.ref('base.ie').id, 'vat': 'IE1519572B'}, False, 'IE'),
            ({'country_id': self.env.ref('base.ie').id, 'vat': 'IE1519572A'}, True, 'IE'),
            # ({'country_id': self.env.ref('base.in').id, 'vat': '27AAPFU0839F1ZV'}, False, 'IN'),  # TODO should be refused by bchecksum in stdnum but not implemented in Odoo
            ({'country_id': self.env.ref('base.in').id, 'vat': '27AAPFU0939F1ZV'}, True, 'IN'),
            ({'country_id': self.env.ref('base.mx').id, 'vat': 'EKU900317421C9'}, False, 'MX'),
            ({'country_id': self.env.ref('base.mx').id, 'vat': 'EKU9003173C9'}, True, 'MX'),
            ({'country_id': self.env.ref('base.nl').id, 'vat': 'NL264077922B03'}, False, 'NL'),
            ({'country_id': self.env.ref('base.nl').id, 'vat': 'NL264077921B03'}, True, 'NL'),
            ({'country_id': self.env.ref('base.no').id, 'vat': 'NO 987 008 643 MVA'}, False, 'NO'),
            ({'country_id': self.env.ref('base.no').id, 'vat': 'NO 987 008 644 MVA'}, True, 'NO'),
            ({'country_id': self.env.ref('base.pe').id, 'vat': '11111111111'}, False, 'PE'),
            ({'country_id': self.env.ref('base.pe').id, 'vat': '20507822470'}, True, 'PE'),
            ({'country_id': self.env.ref('base.ru').id, 'vat': 'RU123456789046'}, False, 'RU'),
            ({'country_id': self.env.ref('base.ru').id, 'vat': 'RU123456789047'}, True, 'RU'),
            ({'country_id': self.env.ref('base.tr').id, 'vat': 'TR17291716062'}, False, 'TR'),
            ({'country_id': self.env.ref('base.tr').id, 'vat': 'TR17291716060'}, True, 'TR'),
            ({'country_id': self.env.ref('base.ua').id, 'vat': 'UAU1234567511'}, False, 'UA'),
            ({'country_id': self.env.ref('base.ua').id, 'vat': 'UAU12345675'}, True, 'UA'),
            ({'country_id': self.env.ref('base.uk').id, 'vat': 'XI 432525179'}, True, False),
            ({'country_id': self.env.ref('base.uk').id, 'vat': 'XI 432525170'}, False, False),
        ]
        for values, valid, country in commands:
            with self.subTest(values=values, valid=valid, country=country):
                if valid:
                    partner.write(dict(values))
                    self.assertEqual(partner.vat, values['vat'])
                    self.assertEqual(partner.vat_error, False)
                    self.assertEqual(partner.vat_country_id.code, country)
                else:
                    with self.assertRaises(ValidationError, msg=values):
                        partner.write(values)

    def test_vat_country_difference(self):
        """Test the validation when country code is different from vat code"""
        partner = self.env['res.partner'].create({
            'name': "Test",
            'country_id': self.env.ref('base.mx').id,
            'vat': 'RORO790707I47',
        })
        self.assertEqual(partner.vat, 'RORO790707I47', "Partner VAT should not be altered")

    def test_parent_validation(self):
        """Test the validation with company and contact"""

        # set an invalid vat number
        self.env.user.company_id.vat_check_vies = False
        company = self.env["res.partner"].create({
            "name": "World Company",
            "country_id": self.env.ref("base.be").id,
            "vat": "ATU12345675",
            "company_type": "company",
        })

        # reactivate it and correct the vat number
        with patch('odoo.addons.base_vat.models.base_vat_mixin.check_vies', type(self)._vies_check_func):
            self.env.user.company_id.vat_check_vies = True
            with self.assertRaises(ValidationError), self.env.cr.savepoint():
                company.vat = "BE0987654321"  # VIES refused, don't fallback on other check
            company.vat = "BE0477472701"

    def test_vat_syntactic_validation(self):
        """ Tests VAT validation (both successes and failures), with the different country
        detection cases possible.
        """
        test_partner = self.env['res.partner'].create({'name': "John Dex"})

        # VAT starting with country code: use the starting country code
        test_partner.write({'vat': 'BE0477472701', 'country_id': self.env.ref('base.fr').id})
        self.assertEqual(test_partner.vat_country_id.code, 'BE')
        test_partner.write({'vat': 'BE0477472701', 'country_id': None})
        self.assertEqual(test_partner.vat_country_id.code, 'BE')

        with self.assertRaises(ValidationError):
            test_partner.write({'vat': 'BE42', 'country_id': self.env.ref('base.fr').id})

        with self.assertRaises(ValidationError):
            test_partner.write({'vat': 'BE42', 'country_id': None})

        # No country code in VAT: use the partner's country
        test_partner.write({'vat': '0477472701', 'country_id': self.env.ref('base.be').id})
        self.assertEqual(test_partner.vat_country_id.code, 'BE')

        with self.assertRaises(ValidationError):
            test_partner.write({'vat': '42', 'country_id': self.env.ref('base.be').id})

        # If no country can be guessed: VAT number should always be considered valid
        # (for technical reasons due to ORM and res.company making related fields towards res.partner for country_id and vat)
        test_partner.write({'vat': '0477472701', 'country_id': None})
        self.assertEqual(test_partner.vat_country_id.code, False)


@tagged('-standard', 'external')
class TestStructureVIES(TestStructure):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.company_id.vat_check_vies = True
        cls._vies_check_func = stdnum.eu.vat.check_vies
