from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestFiscalPositionReconcile(AccountTestInvoicingCommon):
    def check_compute_fiscal_year(
        self, company, date, expected_date_from, expected_date_to
    ):
        current_date = fields.Date.from_string(date)
        res = company.compute_fiscalyear_dates(current_date)
        self.assertEqual(res["date_from"], fields.Date.from_string(expected_date_from))
        self.assertEqual(res["date_to"], fields.Date.from_string(expected_date_to))

    def test_default_fiscal_year(self):
        company = self.env.company
        company.account_config_id.fiscalyear_last_day = 31
        company.account_config_id.fiscalyear_last_month = "12"

        self.check_compute_fiscal_year(
            company,
            "2017-12-31",
            "2017-01-01",
            "2017-12-31",
        )

        self.check_compute_fiscal_year(
            company,
            "2017-01-01",
            "2017-01-01",
            "2017-12-31",
        )

    def test_leap_fiscal_year_1(self):
        company = self.env.company
        company.account_config_id.fiscalyear_last_day = 29
        company.account_config_id.fiscalyear_last_month = "2"

        self.check_compute_fiscal_year(
            company,
            "2016-02-29",
            "2015-03-01",
            "2016-02-29",
        )

        self.check_compute_fiscal_year(
            company,
            "2015-03-01",
            "2015-03-01",
            "2016-02-29",
        )

    def test_leap_fiscal_year_2(self):
        company = self.env.company
        company.account_config_id.fiscalyear_last_day = 28
        company.account_config_id.fiscalyear_last_month = "2"

        self.check_compute_fiscal_year(
            company,
            "2016-02-29",
            "2015-03-01",
            "2016-02-29",
        )

        self.check_compute_fiscal_year(
            company,
            "2016-03-01",
            "2016-03-01",
            "2017-02-28",
        )

    def test_custom_fiscal_year(self):
        company = self.env.company
        company.account_config_id.fiscalyear_last_day = 31
        company.account_config_id.fiscalyear_last_month = "12"

        self.env["account.fiscal.year"].create(
            {
                "name": "6 month 2017",
                "date_from": "2017-01-01",
                "date_to": "2017-05-31",
                "company_id": company.id,
            }
        )

        self.check_compute_fiscal_year(
            company,
            "2017-02-01",
            "2017-01-01",
            "2017-05-31",
        )

        self.check_compute_fiscal_year(
            company,
            "2017-11-01",
            "2017-06-01",
            "2017-12-31",
        )

        self.env["account.fiscal.year"].create(
            {
                "name": "last 3 month 2017",
                "date_from": "2017-10-01",
                "date_to": "2017-12-31",
                "company_id": company.id,
            }
        )

        self.check_compute_fiscal_year(
            company,
            "2017-07-01",
            "2017-06-01",
            "2017-09-30",
        )

    def test_fiscal_years_of_one_company_may_not_overlap(self):
        company = self.company_data["company"]
        FiscalYear = self.env["account.fiscal.year"]
        FiscalYear.create(
            {
                "name": "FY 2030",
                "date_from": "2030-01-01",
                "date_to": "2030-12-31",
                "company_id": company.id,
            }
        )
        with self.assertRaises(ValidationError):
            FiscalYear.create(
                {
                    "name": "overlapping tail",
                    "date_from": "2030-12-01",
                    "date_to": "2031-05-31",
                    "company_id": company.id,
                }
            )
        with self.assertRaises(ValidationError):
            FiscalYear.create(
                {
                    "name": "enclosing",
                    "date_from": "2029-06-01",
                    "date_to": "2031-05-31",
                    "company_id": company.id,
                }
            )
        with self.assertRaises(ValidationError):
            FiscalYear.create(
                [
                    {
                        "name": "batch a",
                        "date_from": "2032-01-01",
                        "date_to": "2032-06-30",
                        "company_id": company.id,
                    },
                    {
                        "name": "batch b, overlapping a",
                        "date_from": "2032-06-01",
                        "date_to": "2032-12-31",
                        "company_id": company.id,
                    },
                ]
            )
        adjacent = FiscalYear.create(
            {
                "name": "FY 2031",
                "date_from": "2031-01-01",
                "date_to": "2031-12-31",
                "company_id": company.id,
            }
        )
        self.assertTrue(adjacent, "an adjacent year is not an overlapping one")
        other_company = self.setup_other_company()["company"]
        self.assertTrue(
            FiscalYear.create(
                {
                    "name": "FY 2030, other company",
                    "date_from": "2030-01-01",
                    "date_to": "2030-12-31",
                    "company_id": other_company.id,
                }
            ),
            "another company's years do not overlap this one's",
        )
