from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountTaxSettingsCompany(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company(name="seam_company")
        cls.other_company = cls.company_data_2["company"]
        cls.other_country = cls.env.ref("base.fr")
        cls.other_company.account_config_id.account_fiscal_country_id = (
            cls.other_country
        )

        cls.domestic_fp = cls._domestic_fiscal_position(cls.env.company)
        cls.other_domestic_fp = cls._domestic_fiscal_position(cls.other_company)

    @classmethod
    def _domestic_fiscal_position(cls, company):
        fp = cls.env["account.fiscal.position"].create(
            {
                "name": f"domestic {company.name}",
                "company_id": company.id,
                "country_id": company.country_id.id,
                "sequence": 1,
            }
        )
        company.account_config_id.invalidate_recordset(["domestic_fiscal_position_id"])
        assert company.account_config_id.domestic_fiscal_position_id == fp, (
            f"fixture: {company.name} did not adopt {fp.name} as its domestic "
            f"fiscal position"
        )
        return fp

    def _patch_seam(self, company):
        self.patch(
            self.env.registry["account.tax"],
            "_get_settings_company",
            lambda records, company=company: company,
        )

    def _tax_on_domestic_fp(self):
        return self.env["account.tax"].create(
            {
                "name": "seam tax",
                "type_tax_use": "sale",
                "amount_type": "percent",
                "amount": 10,
                "fiscal_position_ids": [Command.set(self.domestic_fp.ids)],
            }
        )

    def test_is_domestic_follows_the_seam(self):
        tax = self._tax_on_domestic_fp()
        self.assertTrue(
            tax.is_domestic,
            "the tax carries its own company's domestic fiscal position",
        )

        self._patch_seam(self.other_company)
        tax.invalidate_recordset(["is_domestic"])
        self.assertFalse(
            tax.is_domestic,
            "_compute_is_domestic must read the seam, not company_id",
        )

    def test_display_alternative_taxes_follows_the_seam(self):
        tax = self._tax_on_domestic_fp()
        self.assertFalse(
            tax.display_alternative_taxes_field,
            "a tax on its own company's domestic position is not an alternative",
        )

        self._patch_seam(self.other_company)
        tax.invalidate_recordset(["display_alternative_taxes_field"])
        self.assertTrue(
            tax.display_alternative_taxes_field,
            "_compute_display_alternative_taxes_field must read the seam",
        )

    def test_tag_ids_domain_follows_the_seam(self):
        tax = self._tax_on_domestic_fp()
        rep_line = tax.invoice_repartition_line_ids[0]

        def allowed_countries(line):
            (field, _operator, countries) = line.tag_ids_domain[1]
            self.assertEqual(field, "country_id")
            return countries

        self.assertIn(
            self.env.company.account_config_id.account_fiscal_country_id.id,
            allowed_countries(rep_line),
        )
        self.assertNotIn(
            self.other_country.id,
            allowed_countries(rep_line),
            "fixture: the two companies must differ on their fiscal country",
        )

        self._patch_seam(self.other_company)
        rep_line.invalidate_recordset(["tag_ids_domain"])
        self.assertIn(
            self.other_country.id,
            allowed_countries(rep_line),
            "_compute_tag_ids_domain must read the seam, not company_id",
        )
