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
        def check_vies(vat_number, timeout=10):
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

    def test_missing_company_country(self):
        company = self.env['res.company'].create({
            'name': 'Test Company',
            'country_id': False,
            'vat_check_vies': True,
        })
        partner = self.env['res.partner'].create({
            'name': 'Customer BE',
            'country_id': self.env.ref('base.be').id,
            'vat': 'DE123456788',
            'company_id': company.id,
        })
        valid = partner._get_vat_required_valid(company=company)
        self.assertEqual(valid, True)
        partner.vat = False
        invalid = partner._get_vat_required_valid(company=company)
        self.assertEqual(invalid, False)

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
            with self.assertRaises(ValidationError):
                company.vat = "BE0987654321"  # VIES refused, don't fallback on other check
            company.vat = "BE0477472701"
            self.assertEqual(company.vies_valid, True)

    def test_vat_syntactic_validation(self):
        """ Tests VAT validation (both successes and failures), with the different country
        detection cases possible.
        """
        test_partner = self.env['res.partner'].create({'name': "John Dex"})

        # VAT starting with country code: use the starting country code
        test_partner.write({'vat': 'BE0477472701', 'country_id': self.env.ref('base.fr').id})
        test_partner.write({'vat': 'BE0477472701', 'country_id': None})

        with self.assertRaises(ValidationError):
            # A French VAT with a BE prefix that is not a valid BE number should raise
            test_partner.write({'vat': 'BE23334175221', 'country_id': self.env.ref('base.fr').id})

        # No country code in VAT: use the partner's country
        test_partner.write({'vat': '0477472701', 'country_id': self.env.ref('base.be').id})

        with self.assertRaises(ValidationError):
            test_partner.write({'vat': '42', 'country_id': self.env.ref('base.be').id})

        # If no country set on the partner: VAT number should always be considered valid
        test_partner.write({'vat': 'BE42', 'country_id': None})  # Invalid in BE
        test_partner.write({'vat': '0477472701', 'country_id': None})
        test_partner.write({'vat': 'BE0477472701', 'country_id': None})  # Even with BE prefix, it should not be checked
        test_partner.write({'vat': 'BE0477472702', 'country_id': None})  # also invalid in BE

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

    def test_no_vies_revalidation_when_creating_company_from_contact(self):
        # Test that we don't revalidate the VAT when create a company from a contact where it's already validated
        self.env.user.company_id.vat_check_vies = True
        with patch('odoo.addons.base_vat.models.res_partner.check_vies', type(self)._vies_check_func):
            partner = self.env["res.partner"].create({
                'name': 'Dummy Partner',
                'company_name': 'My Company',
                'vat': 'BE0477472701',
                'country_id': self.env.ref("base.be").id,
            })
            self.assertEqual(partner.vies_valid, True)

        with patch('odoo.addons.base_vat.models.res_partner.check_vies',
                   side_effect=Exception('should not call check_vies()')):
            partner.create_company()
            self.assertEqual(partner.vies_valid, True)
            self.assertEqual(partner.parent_id.name, 'My Company')
            self.assertEqual(partner.parent_id.vies_valid, True)

    def test_rut_uy(self):
        test_partner = self.env["res.partner"].create({"name": "UY Company", "country_id": self.env.ref("base.uy").id})
        # Set a valid Number
        test_partner.write({"vat": "215521750017"})
        test_partner.write({"vat": "220018800014"})
        test_partner.write({"vat": "21-55217500-17"})
        self.assertEqual(test_partner.vat, '215521750017')
        test_partner.write({"vat": "21 55217500 17"})
        self.assertEqual(test_partner.vat, '215521750017')
        test_partner.write({"vat": "UY215521750017"})
        self.assertEqual(test_partner.vat, '215521750017')

        # Test invalid VAT (should raise a ValidationError)
        msg = "The VAT number.*does not seem to be valid"
        with self.assertRaisesRegex(ValidationError, msg):
            test_partner.vat = "215521750018"
        with self.assertRaisesRegex(ValidationError, msg):
            test_partner.vat = "21.55217500.17"
        with self.assertRaisesRegex(ValidationError, msg):
            test_partner.vat = "2155 ABC 21750017"

    def test_company_changes(self):
        ro_country = self.env.ref('base.ro').id
        test_partner_1 = self.env['res.company'].create({'name': 'Roman', 'country_id': self.env.ref('base.es').id})
        test_partner_2 = self.env['res.company'].create({'name': 'Roman2', 'country_id': ro_country, 'vat': '1234567897'})
        companies = test_partner_1 + test_partner_2
        companies.write({'country_id': ro_country})

    def test_cl_hyphen(self):
        cl_country = self.env.ref('base.cl').id
        test_partner_1 = self.env['res.partner'].create({'name': 'Roman', 'country_id': cl_country, 'vat': 'CL 760864285'})
        self.assertEqual(test_partner_1.vat, '76086428-5')

    def test_co_hyphen(self):
        co_country = self.env.ref('base.co').id
        test_partner_1 = self.env['res.partner'].create({'name': 'Roman', 'country_id': co_country, 'vat': '213.123.4321'})
        self.assertEqual(test_partner_1.vat, '213123432-1')

    def test_xi_works(self):
        uk_country = self.env.ref('base.uk').id
        test_partner_1 = self.env['res.partner'].create({'name': 'Roman', 'country_id': uk_country, 'vat': 'XI123456782'})
        self.assertEqual(test_partner_1.vat, 'XI123456782')

    def test_gr_changes(self):
        """ As GR is not associated to another country, it can change magically to EL"""
        gr_country = self.env.ref('base.gr').id
        test_partner_1 = self.env['res.partner'].create({'name': 'Roman', 'country_id': gr_country, 'vat': 'GR123456783'})
        self.assertEqual(test_partner_1.vat, 'EL123456783')
        test_partner_1 = self.env['res.partner'].create({'name': 'Roman', 'country_id': gr_country, 'vat': 'EL123456783'})
        self.assertEqual(test_partner_1.vat, 'EL123456783')

    def test_weird_roro_input(self):
        be_country = self.env.ref('base.be').id
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({'name': 'Roman', 'country_id': be_country, 'vat': 'RORORORO1234567897'})

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

    def test_vat_tw(self):
        test_partner = self.env["res.partner"].create({"name": "TW Company", "country_id": self.env.ref("base.tw").id})

        for ubn in ['88117254', '12345601', '90183275']:
            test_partner.vat = ubn

        for ubn in ['88117250', '12345600', '90183272']:
            with self.assertRaises(ValidationError):
                test_partner.vat = ubn

    def test_vat_notEU_with_EU_vat(self):
        test_partner = self.env["res.partner"].create({"name": "CN Company", "country_id": self.env.ref("base.cn").id})
        # Valid Chinese or French (European Vat)
        test_partner.write({"vat": "123456789012345678"})
        test_partner.write({"vat": "FR17698800935"})
        # Test australian VAT (should raise a ValidationError)
        with self.assertRaises(ValidationError):
            test_partner.write({"vat": "83914571673"})
        test_partner.write({"vat": "BE0477.47.27.01"})
        self.assertEqual(test_partner.vat, 'BE0477472701')

    def test_vat_th(self):
        test_partner = self.env["res.partner"].create({
            "name": "TH Company",
            "country_id": self.env.ref("base.th").id,
        })

        for tin in ['1234545678781', '1-2345-45678-78-1', '0-99-4-000-61772-1']:
            test_partner.vat = tin

        for tin in ['1234545678782', '1-2345-45678-78-2', '0-99-4-000-61772-2', 'X-99-4-000-61772-1']:
            with self.assertRaises(ValidationError):
                test_partner.vat = tin

    def test_vat_do(self):
        test_partner = self.env["res.partner"].create({"name": "DO Company", "country_id": self.env.ref("base.do").id})
        # Valid do vat
        test_partner.write({"vat": "152-0000706-8"})
        test_partner.write({"vat": "4-01-00707-1"})
        # Test invalid VAT (should raise a ValidationError)
        msg = "The VAT number.*does not seem to be valid"
        with self.assertRaisesRegex(ValidationError, msg):
            test_partner.write({'vat': '152-0000706-7'})
        with self.assertRaisesRegex(ValidationError, msg):
            test_partner.write({'vat': '10123457890'})
        with self.assertRaisesRegex(ValidationError, msg):
            test_partner.write({'vat': '152-0000706-99'})


@tagged('-standard', 'external')
class TestStructureVIES(TestStructure):
    allow_inherited_tests_method = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.company_id.vat_check_vies = True
        cls._vies_check_func = stdnum.eu.vat.check_vies
