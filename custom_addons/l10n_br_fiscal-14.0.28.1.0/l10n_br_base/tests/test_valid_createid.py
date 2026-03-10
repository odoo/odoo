# @ 2017 Akretion - www.akretion.com.br -
#   Clément Mombereau <clement.mombereau@akretion.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import ValidationError
from odoo.tests import SavepointCase


class ValidCreateIdTest(SavepointCase):
    """Test if ValidationError is raised well during create({})"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_valid = {
            "name": "Company Test 1",
            "legal_name": "Company Testc 1 Ltda",
            "cnpj_cpf": "02.960.895/0001-31",
            "inscr_est": "081.981.37-6",
            "street": "Rod BR-101 Norte Contorno",
            "street_number": "955",
            "street2": "Portão 1",
            "district": "Jardim da Saudade",
            "state_id": cls.env.ref("base.state_br_es").id,
            "city_id": cls.env.ref("l10n_br_base.city_3205002").id,
            "country_id": cls.env.ref("base.br").id,
            "city": "Serra",
            "zip": "29161-695",
            "phone": "+55 27 2916-1695",
            "email": "contact@companytest.com.br",
            "website": "www.companytest.com.br",
        }

        cls.company_invalid_cnpj = {
            "name": "Company Test 2",
            "legal_name": "Company Testc 2 Ltda",
            "cnpj_cpf": "14.018.406/0001-93",
            "inscr_est": "385.611.86-2",
            "street": "Rod BR-101 Norte Contorno",
            "street_number": "955",
            "street2": "Portão 1",
            "district": "Jardim da Saudade",
            "state_id": cls.env.ref("base.state_br_es").id,
            "city_id": cls.env.ref("l10n_br_base.city_3205002").id,
            "country_id": cls.env.ref("base.br").id,
            "city": "Serra",
            "zip": "29161-695",
            "phone": "+55 27 2916-1695",
            "email": "contact@companytest.com.br",
            "website": "www.companytest.com.br",
        }

        cls.company_invalid_inscr_est = {
            "name": "Company Test 3",
            "legal_name": "Company Testc 3 Ltda",
            "cnpj_cpf": "31.295.101/0001-60",
            "inscr_est": "924.511.27-0",
            "street": "Rod BR-101 Norte Contorno",
            "street_number": "955",
            "street2": "Portão 1",
            "district": "Jardim da Saudade",
            "state_id": cls.env.ref("base.state_br_es").id,
            "city_id": cls.env.ref("l10n_br_base.city_3205002").id,
            "country_id": cls.env.ref("base.br").id,
            "city": "Serra",
            "zip": "29161-695",
            "phone": "+55 27 2916-1695",
            "email": "contact@companytest.com.br",
            "website": "www.companytest.com.br",
        }

        cls.partner_valid = {
            "name": "Partner Test 1",
            "legal_name": "Partner Testc 1 Ltda",
            "cnpj_cpf": "734.419.622-06",
            "inscr_est": "176.754.07-5",
            "street": "Rod BR-101 Norte Contorno",
            "street_number": "955",
            "street2": "Portão 1",
            "district": "Jardim da Saudade",
            "state_id": cls.env.ref("base.state_br_es").id,
            "city_id": cls.env.ref("l10n_br_base.city_3205002").id,
            "country_id": cls.env.ref("base.br").id,
            "city": "Serra",
            "zip": "29161-695",
            "phone": "+55 27 2916-1695",
            "email": "contact@partnertest.com.br",
            "website": "www.partnertest.com.br",
        }

        cls.partner_invalid_cpf = {
            "name": "Partner Test 2",
            "legal_name": "Partner Testc 2 Ltda",
            "cnpj_cpf": "734.419.622-07",
            "inscr_est": "538.759.92-5",
            "street": "Rod BR-101 Norte Contorno",
            "street_number": "955",
            "street2": "Portão 1",
            "district": "Jardim da Saudade",
            "state_id": cls.env.ref("base.state_br_es").id,
            "city_id": cls.env.ref("l10n_br_base.city_3205002").id,
            "country_id": cls.env.ref("base.br").id,
            "city": "Serra",
            "zip": "29161-695",
            "phone": "+55 27 2916-1695",
            "email": "contact@partnertest.com.br",
            "website": "www.partnertest.com.br",
        }

        cls.partner_outside_br = {
            "name": "Partner Test 3",
            "legal_name": "Partner Tesc 3 Ltda",
            "vat": "123456789",
            "street": "Street Company",
            "street_number": "955",
            "street2": "Street2 Company",
            "district": "Company District",
            "state_id": cls.env.ref("base.state_us_2").id,
            "country_id": cls.env.ref("base.us").id,
            "city": "Nome",
            "zip": "99762",
            "phone": "+1 (907) 443-5796",
            "email": "contact@companytest.com.br",
            "website": "www.companytest.com.br",
        }

    # Tests on companies

    def test_comp_valid(self):
        """Try do create id with correct CNPJ and correct Inscricao Estadual"""
        try:
            company = (
                self.env["res.company"]
                .with_context(tracking_disable=True)
                .create(self.company_valid)
            )
        except Exception:
            assert company, "Error when using .create() even with valid \
                             and Inscricao Estadual"

    def test_comp_invalid_cnpj(self):
        """Test if ValidationError raised during .create() with invalid CNPJ
        and correct Inscricao Estadual"""
        with self.assertRaises(ValidationError):
            self.env["res.company"].with_context(tracking_disable=True).create(
                self.company_invalid_cnpj
            )

    def test_comp_invalid_inscr_est(self):
        """Test if ValidationError raised with correct CNPJ
        and invalid Inscricao Estadual"""
        with self.assertRaises(ValidationError):
            self.env["res.company"].with_context(tracking_disable=True).create(
                self.company_invalid_inscr_est
            )

    # Tests on partners

    def test_part_valid(self):
        """Try do create id with correct CPF and correct Inscricao Estadual"""
        try:
            partner = (
                self.env["res.partner"]
                .with_context(tracking_disable=True)
                .create(self.partner_valid)
            )
        except Exception:
            assert partner, "Error when using .create() even with valid CPF \
                         and Inscricao Estadual"

    def test_part_invalid_cpf(self):
        """Test if ValidationError raised during .create() with invalid CPF
        and correct Inscricao Estadual"""
        with self.assertRaises(ValidationError):
            self.env["res.partner"].with_context(tracking_disable=True).create(
                self.partner_invalid_cpf
            )

    def test_vat_computation_with_cnpj(self):
        """Test VAT computation for a br partner with CNPJ"""
        partner = (
            self.env["res.partner"]
            .with_context(tracking_disable=True)
            .create(self.partner_valid)
        )
        partner._compute_vat_from_cnpj_cpf()
        self.assertEqual(
            partner.vat,
            self.partner_valid["cnpj_cpf"],
            "VAT should be equal to CNPJ for a br partner",
        )

    def test_vat_computation_without_cnpj(self):
        """Test VAT computation for a br partner without CNPJ"""
        partner_data = self.partner_valid.copy()
        partner_data.pop("cnpj_cpf")
        partner = (
            self.env["res.partner"]
            .with_context(tracking_disable=True)
            .create(partner_data)
        )
        partner._compute_vat_from_cnpj_cpf()
        self.assertFalse(
            partner.vat, "VAT should be False for a br partner without CNPJ"
        )

    def test_vat_computation_outside_company_with_vat(self):
        """Test VAT computation for a outside br partner with VAT"""
        partner = (
            self.env["res.partner"]
            .with_context(tracking_disable=True)
            .create(self.partner_outside_br)
        )
        partner._compute_vat_from_cnpj_cpf()
        self.assertEqual(
            partner.vat,
            "123456789",
            "The VAT must be the same as what was registered",
        )

    def test_vat_computation_outside_company_without_vat(self):
        """Test VAT computation for a outside br partner without VAT"""
        partner_data = self.partner_outside_br.copy()
        partner_data.pop("vat")
        partner = (
            self.env["res.partner"]
            .with_context(tracking_disable=True)
            .create(partner_data)
        )
        partner._compute_vat_from_cnpj_cpf()
        self.assertFalse(partner.vat, "VAT should be False as registered")

    def test_vat_computation_with_company_name_and_vat(self):
        """Test VAT computation for a br partner with company_name and vat"""
        partner_data = self.partner_valid.copy()
        partner_data.update(
            {
                "company_name": "Company Partner",
                "vat": "93.429.799/0001-17",
            }
        )
        partner = (
            self.env["res.partner"]
            .with_context(tracking_disable=True)
            .create(partner_data)
        )
        partner._compute_vat_from_cnpj_cpf()
        self.assertEqual(
            partner.vat,
            "93.429.799/0001-17",
            "The VAT must be the same as what was registered",
        )

    def test_create_company_in_brazil(self):
        """Test the creation of a company in Brazil"""
        partner_data = self.partner_valid.copy()
        partner_data.update(
            {
                "company_name": "Company Partner",
                "vat": "93.429.799/0001-17",
            }
        )
        partner = (
            self.env["res.partner"]
            .with_context(tracking_disable=True)
            .create(partner_data)
        )
        partner.create_company()
        company = partner.parent_id
        self.assertTrue(company, "The company was not created")
        self.assertEqual(
            company.legal_name,
            company.name,
            "The legal name must be the same as the company name",
        )
        self.assertEqual(
            company.cnpj_cpf,
            company.vat,
            "The company CNPJ_CPF must be the same as the company VAT",
        )
        self.assertEqual(
            company.cnpj_cpf,
            partner.vat,
            "The company CNPJ_CPF must be the same as the partner VAT",
        )
        self.assertEqual(
            company.inscr_est,
            partner.inscr_est,
            "The company INSCR_EST must be the same as the partner INSCR_EST",
        )
        self.assertEqual(
            company.inscr_mun,
            partner.inscr_mun,
            "The company INSCR_MUN must be the same as the partner INSCR_MUN",
        )

    def test_create_company_outside_brazil(self):
        """Test the creation of a company outside Brazil"""
        partner_data = self.partner_outside_br.copy()
        partner_data.update(
            {
                "company_name": "Company Partner",
            }
        )
        partner = (
            self.env["res.partner"]
            .with_context(tracking_disable=True)
            .create(partner_data)
        )
        partner.create_company()
        company = partner.parent_id
        self.assertTrue(company, "The company was not created")
        self.assertEqual(
            company.vat,
            partner.vat,
            "The company CNPJ_CPF must be the same as the partner VAT",
        )
        self.assertFalse(company.cnpj_cpf, "CNPJ_CPF should be False")


# No test on Inscricao Estadual for partners with CPF
# because they haven't Inscricao Estadual
