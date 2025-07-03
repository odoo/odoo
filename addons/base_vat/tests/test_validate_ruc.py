# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import TransactionCase, tagged
from odoo._monkeypatches.stdnum import new_get_soap_client
from odoo.exceptions import ValidationError
from unittest.mock import patch

import stdnum.eu.vat
from lxml import etree
from zeep import Client, Transport
from zeep.wsdl import Document


class TestStructure(TransactionCase):
    @classmethod
    def setUpClass(cls):
        def check_vies(vat_number):
            return {'valid': vat_number == 'BE0477472701'}

        super().setUpClass()
        cls.env.user.company_id.vat_check_vies = False
        cls._vies_check_func = check_vies

    def test_peru_ruc_format(self):
        """Only values that has the length of 11 will be checked as RUC, that's what we are proving. The second part
        will check for a valid ruc and there will be no problem at all.
        """
        partner = self.env['res.partner'].create({'name': "Dummy partner", 'country_id': self.env.ref('base.pe').id})

        with self.assertRaises(ValidationError):
            partner.vat = '11111111111'
        partner.vat = '20507822470'

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
        with patch('odoo.addons.base_vat.models.res_partner.check_vies', type(self)._vies_check_func):
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
        test_partner.write({'vat': 'BE0477472701', 'country_id': None})

        with self.assertRaises(ValidationError):
            test_partner.write({'vat': 'BE42', 'country_id': self.env.ref('base.fr').id})

        with self.assertRaises(ValidationError):
            test_partner.write({'vat': 'BE42', 'country_id': None})

        # No country code in VAT: use the partner's country
        test_partner.write({'vat': '0477472701', 'country_id': self.env.ref('base.be').id})

        with self.assertRaises(ValidationError):
            test_partner.write({'vat': '42', 'country_id': self.env.ref('base.be').id})

        # If no country can be guessed: VAT number should always be considered valid
        # (for technical reasons due to ORM and res.company making related fields towards res.partner for country_id and vat)
        test_partner.write({'vat': '0477472701', 'country_id': None})

    def test_vat_eu(self):
        """ Foreign companies that trade with non-enterprises in the EU may have a VATIN starting with "EU" instead of
        a country code.
        """
        test_partner = self.env['res.partner'].create({'name': "Turlututu", 'country_id': self.env.ref('base.fr').id})
        test_partner.write({'vat': "EU528003646", 'country_id': None})

        test_partner.write({'vat': "EU528003646", 'country_id': self.env.ref('base.ca').id})

        with self.assertRaises(ValidationError):
            test_partner.write({'vat': 'EU528003646', 'country_id': self.env.ref('base.be').id})

    def test_nif_de(self):
        test_partner = self.env['res.partner'].create({'name': "Mein Company", 'country_id': self.env.ref('base.de').id})
        # Set a valid VAT
        test_partner.write({'vat': "DE123456788"})
        # Set a valid German tax ID (steuernummer)
        test_partner.write({'vat': "201/123/12340"})
        # Test invalid VAT (should raise a ValidationError)
        with self.assertRaises(ValidationError):
            test_partner.write({'vat': "136695978"})

    def test_soap_client_for_vies_loads(self):
        # Test of stdnum get_soap_client monkeypatch. This test is mostly to
        # see that no unexpected import errors are thrown and not caught.
        with patch.object(Document, '_get_xml_document', return_value=etree.Element("root")), \
                patch.object(Client, 'service', return_value=None):
            doc = Document(location=None, transport=Transport())
            new_get_soap_client(doc, 30)

    def test_rut_uy(self):
        test_partner = self.env["res.partner"].create({"name": "UY Company", "country_id": self.env.ref("base.uy").id})
        # Set a valid Number
        test_partner.write({"vat": "215521750017"})
        test_partner.write({"vat": "220018800014"})
        test_partner.write({"vat": "21-55217500-17"})
        test_partner.write({"vat": "21 55217500 17"})
        test_partner.write({"vat": "UY215521750017"})

        # Test invalid VAT (should raise a ValidationError)
        msg = "The VAT number.*does not seem to be valid"
        with self.assertRaisesRegex(ValidationError, msg):
            test_partner.vat = "215521750018"
        with self.assertRaisesRegex(ValidationError, msg):
            test_partner.vat = "21.55217500.17"
        with self.assertRaisesRegex(ValidationError, msg):
            test_partner.vat = "2155 ABC 21750017"

    def test_vat_vn(self):
        test_partner = self.env['res.partner'].create({'name': "DuongDepTrai", 'country_id': self.env.ref('base.vn').id})
        # Valid vn vat
        test_partner.vat = "000012345679"  # individual
        test_partner.vat = "0123457890"  # enterprise
        test_partner.vat = "0123457890-111"  # branch

        # Test invalid VAT (should raise a ValidationError)
        msg = "The VAT number.*does not seem to be valid"
        with self.assertRaisesRegex(ValidationError, msg):
            test_partner.write({'vat': '00001234567912'})
        with self.assertRaisesRegex(ValidationError, msg):
            test_partner.write({'vat': '10123457890'})
        with self.assertRaisesRegex(ValidationError, msg):
            test_partner.write({'vat': '0123457890-11134'})


@tagged('-standard', 'external')
class TestStructureVIES(TestStructure):
    allow_inherited_tests_method = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.company_id.vat_check_vies = True
        cls._vies_check_func = stdnum.eu.vat.check_vies
