from odoo import Command
from odoo.tests import tagged

from .common import BaseTaxCommon


@tagged("post_install", "-at_install")
class TestTaxSettingsCompany(BaseTaxCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_country = cls.env.ref(
            "base.us" if cls.country != cls.env.ref("base.us") else "base.be"
        )
        cls.other_company = cls.env["res.company"].create(
            {
                "name": "account_tax settings company",
                "country_id": cls.other_country.id,
            }
        )
        if "account_config_id" in cls.env["res.company"]._fields:
            cls.other_company.account_config_id.account_fiscal_country_id = (
                cls.other_country
            )
        cls.cross_country_group = cls.env["account.tax.group"].create(
            {
                "name": "account_tax cross-country group",
                "company_ids": [Command.set(cls.company.ids)],
                "country_id": cls.other_country.id,
            }
        )

    def _patch_seam(self, model, company):
        self.patch(
            self.env.registry[model],
            "_get_settings_company",
            lambda records, company=company: company,
        )

    def _tax_without_country(self, tax_group):
        return self.env["account.tax"].create(
            {
                "name": f"seam tax {tax_group.id}",
                "type_tax_use": "sale",
                "amount_type": "percent",
                "amount": 10,
                "tax_group_id": tax_group.id,
            }
        )

    def test_settings_company_is_the_acting_company(self):
        tax = self._tax(10)
        self.assertEqual(tax._get_settings_company(), self.env.company)
        self.assertEqual(
            tax.with_company(self.other_company)._get_settings_company(),
            self.other_company,
        )

    def test_group_settings_company_is_the_acting_company(self):
        self.assertEqual(
            self.tax_group._get_settings_company(),
            self.env.company,
        )
        self.assertEqual(
            self.tax_group.with_company(self.other_company)._get_settings_company(),
            self.other_company,
        )

    def test_tax_country_follows_the_seam(self):
        baseline = self._tax_without_country(self.tax_group)
        self.assertEqual(baseline.company_ids, self.company)
        self.assertEqual(baseline.country_id, self.country)

        self._patch_seam("account.tax", self.other_company)
        redirected = self._tax_without_country(self.cross_country_group)
        self.assertEqual(
            redirected.company_ids,
            self.company,
            "the tax still belongs to the original company",
        )
        self.assertEqual(
            redirected.country_id,
            self.other_country,
            "_compute_country_id must read the seam, not company_id",
        )

    def test_tax_group_country_follows_the_seam(self):
        self._patch_seam("account.tax.group", self.other_company)
        group = self.env["account.tax.group"].create(
            {"name": "seam group", "company_ids": [Command.set(self.company.ids)]}
        )
        self.assertEqual(
            group.country_id,
            self.other_country,
            "_compute_country_id must read the seam, not company_id",
        )

    def test_company_price_include_follows_the_seam(self):
        if not self.account_installed:
            self.skipTest("account_price_include is contributed by `account`")

        self.company.account_config_id.account_price_include = "tax_excluded"
        self.other_company.account_config_id.account_price_include = "tax_included"

        tax = self._tax(10)
        self.assertEqual(tax.company_price_include, "tax_excluded")
        self.assertFalse(tax.price_include)

        self._patch_seam("account.tax", self.other_company)
        tax.invalidate_recordset(["company_price_include", "price_include"])
        self.assertEqual(
            tax.company_price_include,
            "tax_included",
            "_compute_company_price_include must read the seam, not company_id",
        )
        self.assertTrue(tax.price_include)
