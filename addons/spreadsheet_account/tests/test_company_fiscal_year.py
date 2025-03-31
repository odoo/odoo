# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase

from datetime import date


class SpreadsheetFiscalYearTest(TransactionCase):
    def test_fiscal_year_reference(self):
        self.env.company.fiscalyear_last_day = 3
        self.env.company.fiscalyear_last_month = "2"

        self.assertEqual(
            self.env["res.company"].get_fiscal_dates(
                [{"company_id": None, "date": "2020-03-05"}]
            ),
            [
                {"start": date(2020, 2, 4), "end": date(2021, 2, 3)},
            ],
        )

    def test_fiscal_year_reference_last_day(self):
        self.env.company.fiscalyear_last_day = 3
        self.env.company.fiscalyear_last_month = "2"

        self.assertEqual(
            self.env["res.company"].get_fiscal_dates(
                [{"company_id": None, "date": "2020-02-03"}]
            ),
            [
                {"start": date(2019, 2, 4), "end": date(2020, 2, 3)},
            ],
        )

    def test_fiscal_year_reference_first_day(self):
        self.env.company.fiscalyear_last_day = 3
        self.env.company.fiscalyear_last_month = "2"

        self.assertEqual(
            self.env["res.company"].get_fiscal_dates(
                [{"company_id": None, "date": "2020-02-04"}]
            ),
            [{"start": date(2020, 2, 4), "end": date(2021, 2, 3)}],
        )

    def test_fiscal_year_with_company_id(self):
        self.env.company.fiscalyear_last_day = 7
        self.env.company.fiscalyear_last_month = "6"
        company = self.env["res.company"].create(
            {
                "name": "test company",
                "fiscalyear_last_day": 3,
                "fiscalyear_last_month": "2",
            }
        )
        self.assertEqual(
            self.env["res.company"].get_fiscal_dates(
                [
                    {"company_id": company.id, "date": "2020-02-04"},
                    {"company_id": None, "date": "2020-02-04"},
                ]
            ),
            [
                {"start": date(2020, 2, 4), "end": date(2021, 2, 3)},
                {"start": date(2019, 6, 8), "end": date(2020, 6, 7)},
            ],
        )

    def test_result_order(self):
        company = self.env["res.company"].create(
            {
                "name": "test company",
                "fiscalyear_last_day": 3,
                "fiscalyear_last_month": "2",
            }
        )
        request1 = {"company_id": company.id, "date": "2020-02-04"}
        request2 = {"company_id": None, "date": "2020-02-04"}
        [o1_request1, o1_request2] = self.env["res.company"].get_fiscal_dates(
            [request1, request2]
        )
        [o2_request2, o2_request1] = self.env["res.company"].get_fiscal_dates(
            [request2, request1]
        )
        self.assertEqual(o1_request1, o2_request1)
        self.assertEqual(o1_request2, o2_request2)

    def test_fiscal_year_with_wrong_company_id(self):
        self.env.company.fiscalyear_last_day = 7
        self.env.company.fiscalyear_last_month = "6"
        self.assertEqual(
            self.env["res.company"].get_fiscal_dates(
                [
                    {"company_id": 999, "date": "2020-02-04"},
                    {"company_id": None, "date": "2020-02-04"},
                ]
            ),
            [
                False,
                {"start": date(2019, 6, 8), "end": date(2020, 6, 7)},
            ],
        )
