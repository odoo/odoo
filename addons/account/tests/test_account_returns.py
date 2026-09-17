from datetime import date
from itertools import product
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tools.misc import ReadonlyDict
from odoo.tools.translate import CodeTranslations

from odoo.addons.account.tests.common_report_engine import TestAccountReportsCommon


def patched_generate_all_returns(
    account_return_type, country_code, main_company, tax_unit=None
):
    TestAccountReturn.basic_return_type._try_create_returns_for_fiscal_year(
        main_company, tax_unit
    )
    TestAccountReturn.ec_sales_list_return_type._try_create_returns_for_fiscal_year(
        main_company, tax_unit
    )
    TestAccountReturn.annual_return_type._try_create_returns_for_fiscal_year(
        main_company, tax_unit
    )


@tagged("post_install", "-at_install")
class TestAccountReturn(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # necessary to ensure successful return checks
        cls.company_data["company"].write(
            {
                "vat": "US12345671",
                "phone_ids": [
                    Command.create({"number": "123456789", "type": "landline"})
                ],
                "email": "test@gmail.com",
            }
        )

        cls.basic_tax_report = cls.env["account.report"].create(
            {
                "root_report_id": cls.env.ref("account.generic_tax_report").id,
                "name": "Account Returns Test Tax Report",
            }
        )

        cls.basic_return_type = cls.env["account.return.type"].create(
            {
                "name": "VAT Return (Generic)",
                "report_id": cls.basic_tax_report.id,
                "default_deadline_start_date": "2024-01-01",
            }
        )

        cls.basic_ec_sales_report = cls.env["account.report"].create(
            {
                "root_report_id": cls.env.ref("account.generic_ec_sales_report").id,
                "name": "Account Returns Test EC Sales Report",
            }
        )

        cls.ec_sales_list_return_type = cls.env["account.return.type"].create(
            {
                "name": "EC Sales List",
                "report_id": cls.basic_ec_sales_report.id,
                "default_deadline_start_date": "2024-01-01",
            }
        )

        cls.annual_return_type = cls.env.ref("account.annual_corporate_tax_return_type")

        cls.audit_return_type = cls.env.ref("account.default_audit_return_type")

        cls.audit_2024 = cls.audit_return_type.with_context(
            forced_date_from=fields.Date.from_string("2024-01-01"),
            forced_date_to=fields.Date.from_string("2024-12-31"),
        )._try_create_returns_for_fiscal_year(cls.env.company, False)

        cls.audit_2025 = cls.audit_return_type.with_context(
            forced_date_from=fields.Date.from_string("2025-01-01"),
            forced_date_to=fields.Date.from_string("2025-12-31"),
        )._try_create_returns_for_fiscal_year(cls.env.company, False)

        cls.startClassPatcher(freeze_time("2024-01-16"))

        with cls._patch_returns_generation():
            cls.env.company.account_opening_date = "2024-01-01"

    @classmethod
    def _patch_returns_generation(cls):
        return patch.object(
            cls.registry["account.return.type"],
            "_generate_all_returns",
            patched_generate_all_returns,
        )

    @classmethod
    def _patch_generate_locking_attachments(cls):
        return patch.object(
            cls.registry["account.return"],
            "_generate_locking_attachments",
            lambda self, options: None,
        )

    @classmethod
    def _patch_postprocess_vat_closing_entry_results(
        cls, profit_account, loss_account, line_1, line_2
    ):
        def patched_postprocess_vat_closing_entry_results(
            self, company, options, results
        ):
            rounding_accounts = {
                "profit": profit_account,
                "loss": loss_account,
            }

            vat_results_summary = [
                ("due", line_1.id, "balance"),
                ("deductible", line_2.id, "balance"),
            ]
            return self._vat_closing_entry_results_rounding(
                company, options, results, rounding_accounts, vat_results_summary
            )

        return patch.object(
            cls.registry["account.return"],
            "_postprocess_vat_closing_entry_results",
            patched_postprocess_vat_closing_entry_results,
        )

    def assert_return_dates_equal(self, returns, dates_list):
        self.assertEqual(len(returns), len(dates_list), "Return count mismatch")

        errors = []
        for i, account_return in enumerate(returns):
            dates_tuple = dates_list[i]
            if fields.Date.to_string(account_return.date_from) != dates_tuple[0]:
                errors += [
                    f"\n==== Differences at index {i} ====",
                    f"Current date_from:  {account_return.date_from}",
                    f"Expected date_from: {dates_tuple[0]}",
                ]
            if fields.Date.to_string(account_return.date_to) != dates_tuple[1]:
                errors += [
                    f"\n==== Differences at index {i} ====",
                    f"Current date_to:  {account_return.date_to}",
                    f"Expected date_to: {dates_tuple[1]}",
                ]
        if errors:
            self.fail("\n".join(errors))

    def assert_checks_equal(self, account_return, expected_check_dicts):
        checks_by_code = {
            account_return_check.code: account_return_check
            for account_return_check in account_return.check_ids
        }

        errors = []
        for expected_check_dict in expected_check_dicts:
            if "code" not in expected_check_dict:
                raise KeyError("'code' is mandatory.")
            if expected_check_dict["code"] not in checks_by_code:
                errors.append(
                    f"\n==== Code '{expected_check_dicts['code']}' missing in return check ===="
                )
            else:
                current_check = checks_by_code[expected_check_dict["code"]]
                current_check_errors = []
                for key, value in expected_check_dict.items():
                    if current_check[key] != value:
                        current_check_errors.append(
                            f"{key} are different: '{value}' != '{current_check[key]}'"
                        )

                if current_check_errors:
                    errors += [
                        f"\n==== Error in check with code: '{current_check.code}' ====",
                        *current_check_errors,
                    ]

        if errors:
            self.fail("\n".join(errors))

    def assert_return_contains_checks(self, account_return, expected_check_codes):
        checks_by_code = {check.code: check for check in account_return.check_ids}
        missing_checks = [
            code for code in expected_check_codes if code not in checks_by_code
        ]

        if missing_checks:
            self.fail(f"Missing checks in return: {', '.join(missing_checks)}")

    def test_report_return_periodicity_option(self):
        # 1. Check the 'return_type_id' key: it should fall back to the one linked to the report if there is one
        options = self.basic_tax_report.get_options(
            previous_options={
                "return_periodicity": {
                    "periodicity": "monthly",
                    "months_per_period": 1,
                    "start_day": 1,
                    "start_month": 1,
                    "report_id": self.basic_tax_report.id,
                    "fy_start_day": 1,
                    "fy_start_month": 1,
                },
            }
        )
        start_day, start_month = self.basic_return_type._get_start_date_elements(
            self.env.company
        )
        self.assertDictEqual(
            options["return_periodicity"],
            {
                "periodicity": self.basic_return_type._get_periodicity(
                    self.env.company
                ),
                "months_per_period": self.basic_return_type._get_periodicity_months_delay(
                    self.env.company
                ),
                "start_day": start_day,
                "start_month": start_month,
                "return_type_id": self.basic_return_type.id,
                "report_id": self.basic_tax_report.id,
                "fy_start_day": 1,
                "fy_start_month": 1,
            },
        )

        # 2. Valid override using the previous options
        options = self.basic_tax_report.get_options(
            previous_options={
                "return_periodicity": {
                    "periodicity": "monthly",
                    "months_per_period": 1,
                    "start_day": 1,
                    "start_month": 1,
                    "return_type_id": self.basic_return_type.id,
                    "report_id": self.basic_tax_report.id,
                    "fy_start_day": 1,
                    "fy_start_month": 10,
                },
            }
        )
        self.assertDictEqual(
            options["return_periodicity"],
            {
                "periodicity": "monthly",
                "months_per_period": 1,
                "start_day": 1,
                "start_month": 1,
                "return_type_id": self.basic_return_type.id,
                "report_id": self.basic_tax_report.id,
                "fy_start_day": 1,
                "fy_start_month": 10,
            },
        )

        # 3. Check that it is variant safe and should fallback to the return_type linked to the report
        options = self.basic_tax_report.get_options(
            previous_options={
                "return_periodicity": {
                    "periodicity": "monthly",
                    "months_per_period": 1,
                    "start_day": 1,
                    "start_month": 1,
                    "return_type_id": self.basic_return_type.id,
                    "report_id": self.basic_tax_report.id,
                    "fy_start_day": 1,
                    "fy_start_month": 1,
                },
            }
        )
        self.assertDictEqual(
            options["return_periodicity"],
            {
                "periodicity": self.basic_return_type._get_periodicity(
                    self.env.company
                ),
                "months_per_period": self.basic_return_type._get_periodicity_months_delay(
                    self.env.company
                ),
                "start_day": start_day,
                "start_month": start_month,
                "return_type_id": self.basic_return_type.id,
                "report_id": self.basic_tax_report.id,
                "fy_start_day": 1,
                "fy_start_month": 1,
            },
        )

        # 4. Check the final fallback using a report that has no link to a return
        basic_report_not_linked = self.env["account.report"].create(
            {
                "root_report_id": self.env.ref("account.generic_tax_report").id,
                "name": "Account Returns Test Tax Report - Not Linked",
            }
        )
        options = basic_report_not_linked.get_options(
            previous_options={
                "return_periodicity": {
                    "periodicity": "monthly",
                    "months_per_period": 1,
                    "start_day": 1,
                    "start_month": 1,
                    "return_type_id": self.basic_return_type.id,
                    "report_id": self.basic_tax_report.id,
                    "fy_start_day": 1,
                    "fy_start_month": 1,
                },
            }
        )
        self.assertFalse(
            options.get("return_periodicity"),
            "'return_periodicity' key should be absent as the report_id in the dict is different as the actual report generating the options.",
        )

        # 5. Check the default behaviour
        options = self.basic_tax_report.get_options(previous_options={})
        self.assertDictEqual(
            options["return_periodicity"],
            {
                "periodicity": self.basic_return_type._get_periodicity(
                    self.env.company
                ),
                "months_per_period": self.basic_return_type._get_periodicity_months_delay(
                    self.env.company
                ),
                "start_day": start_day,
                "start_month": start_month,
                "return_type_id": self.basic_return_type.id,
                "report_id": self.basic_tax_report.id,
                "fy_start_day": 1,
                "fy_start_month": 1,
            },
        )

    def test_report_return_periodicity_option_multi_returns(self):
        report = self.env["account.report"].create(
            {
                "root_report_id": self.env.ref("account.generic_tax_report").id,
                "name": "Reportt",
            }
        )

        return_types = self.env["account.return.type"].create(
            [
                {
                    "name": "Return Type 1",
                    "report_id": report.id,
                    "deadline_start_date": "2024-01-01",
                    "deadline_periodicity": "monthly",
                },
                {
                    "name": "Return Type 2",
                    "report_id": report.id,
                    "deadline_start_date": "2024-01-01",
                    "deadline_periodicity": "2_months",
                },
            ]
        )

        monthly_return = (
            return_types[0]
            .with_context(
                forced_date_from=fields.Date.from_string("2024-01-01"),
                forced_date_to=fields.Date.from_string("2024-01-31"),
            )
            ._try_create_returns_for_fiscal_year(self.env.company, False)
        )
        monthly_return_options = monthly_return._get_closing_report_options()
        self.assertEqual(monthly_return_options["date"]["date_from"], "2024-01-01")
        self.assertEqual(monthly_return_options["date"]["date_to"], "2024-01-31")

        bimonthly_return = (
            return_types[1]
            .with_context(
                forced_date_from=fields.Date.from_string("2024-01-01"),
                forced_date_to=fields.Date.from_string("2024-02-29"),
            )
            ._try_create_returns_for_fiscal_year(self.env.company, False)
        )
        bimonthly_return_options = bimonthly_return._get_closing_report_options()
        self.assertEqual(bimonthly_return_options["date"]["date_from"], "2024-01-01")
        self.assertEqual(bimonthly_return_options["date"]["date_to"], "2024-02-29")

        monthly_return_june = (
            return_types[0]
            .with_context(
                forced_date_from=fields.Date.from_string("2024-06-01"),
                forced_date_to=fields.Date.from_string("2024-06-30"),
            )
            ._try_create_returns_for_fiscal_year(self.env.company, False)
        )
        monthly_return_june_options = monthly_return_june._get_closing_report_options()
        self.assertEqual(monthly_return_june_options["date"]["date_from"], "2024-06-01")
        self.assertEqual(monthly_return_june_options["date"]["date_to"], "2024-06-30")

    def test_return_generation_normal(self):
        existing_returns = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.env.company.id),
            ]
        )

        self.assert_return_dates_equal(
            existing_returns,
            [
                ("2023-12-01", "2023-12-31"),
                ("2024-01-01", "2024-01-31"),
                ("2024-02-01", "2024-02-29"),
                ("2024-03-01", "2024-03-31"),
                ("2024-04-01", "2024-04-30"),
                ("2024-05-01", "2024-05-31"),
                ("2024-06-01", "2024-06-30"),
                ("2024-07-01", "2024-07-31"),
                ("2024-08-01", "2024-08-31"),
                ("2024-09-01", "2024-09-30"),
                ("2024-10-01", "2024-10-31"),
                ("2024-11-01", "2024-11-30"),
                ("2024-12-01", "2024-12-31"),
            ],
        )

    def test_tax_return_with_branches_and_rounding_applied(self):
        """
        The rounding some countries apply to the closing moves, by calling
        `_vat_closing_entry_results_rounding` with a specific `vat_results_summary`, must be
        correctly computed for a company with branches.
        """
        # We need to create a new tax report with report lines which will be used in _postprocess_vat_closing_entry_results
        report = self.env["account.report"].create(
            {
                "name": "Tax report",
                "root_report_id": self.env.ref("account.generic_tax_report").id,
                "column_ids": [
                    Command.create(
                        {
                            "name": "Balance",
                            "expression_label": "balance",
                        }
                    ),
                ],
            }
        )

        sale_tag, purchase_tag = self.env["account.account.tag"].create(
            [
                {
                    "name": name,
                    "applicability": "taxes",
                    "country_id": self.env.company.country_id.id,
                }
                for i, name in enumerate(["test_sale_tag", "test_purchase_tag"])
            ]
        )

        report_lines = self.env["account.report.line"].create(
            [
                {
                    "name": "test_sale_line",
                    "report_id": report.id,
                    "sequence": 10,
                    "expression_ids": [
                        Command.create(
                            {
                                "label": "balance",
                                "engine": "tax_tags",
                                "formula": tag.name,
                            }
                        ),
                    ],
                }
                for tag in (sale_tag, purchase_tag)
            ]
        )

        self.basic_return_type.write(
            {
                "report_id": report.id,
            }
        )

        self.tax_sale_a.invoice_repartition_line_ids.filtered(
            lambda l: l.repartition_type == "tax"
        ).tag_ids = sale_tag
        self.tax_purchase_a.invoice_repartition_line_ids.filtered(
            lambda l: l.repartition_type == "tax"
        ).tag_ids = purchase_tag

        branch_1, branch_2 = [
            self._create_company(name=name, parent_id=self.env.company.id)
            for name in ("Branch A", "Branch B")
        ]

        for move_type, amount, company in [
            ("in_invoice", 100, self.env.company),
            ("out_invoice", 200, branch_1),
            ("out_invoice", 300, branch_2),
        ]:
            self._create_invoice(
                move_type=move_type,
                invoice_date="2023-12-15",
                post=True,
                company_id=company.id,
                invoice_line_ids=[
                    self._prepare_invoice_line(
                        product_id=self.product_a, price_unit=amount
                    )
                ],
            )

        with self._patch_returns_generation():
            self.env.company.account_opening_date = "2024-01-01"

        existing_returns = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.env.company.id),
            ]
        )

        self.assert_return_dates_equal(
            existing_returns,
            [
                ("2023-12-01", "2023-12-31"),
                ("2024-01-01", "2024-01-31"),
                ("2024-02-01", "2024-02-29"),
                ("2024-03-01", "2024-03-31"),
                ("2024-04-01", "2024-04-30"),
                ("2024-05-01", "2024-05-31"),
                ("2024-06-01", "2024-06-30"),
                ("2024-07-01", "2024-07-31"),
                ("2024-08-01", "2024-08-31"),
                ("2024-09-01", "2024-09-30"),
                ("2024-10-01", "2024-10-31"),
                ("2024-11-01", "2024-11-30"),
                ("2024-12-01", "2024-12-31"),
            ],
        )

        profit_account = self.company_data["default_account_revenue"]
        loss_account = self.company_data["default_account_expense"]
        with (
            self.allow_pdf_render(),
            self._patch_postprocess_vat_closing_entry_results(
                profit_account, loss_account, *report_lines
            ),
        ):
            existing_returns[0].action_mark_completed()
            existing_returns[0].action_validate(bypass_failing_tests=True)

        self.assertRecordValues(
            existing_returns[0].closing_move_ids.line_ids.sorted("move_id"),
            [
                {
                    "company_id": self.env.company.id,
                    "account_id": self.company_data["default_account_tax_purchase"].id,
                    "debit": 0.0,
                    "credit": 15.0,
                },
                {
                    "company_id": self.env.company.id,
                    "account_id": self.company_data["default_account_expense"].id,
                    "debit": 15.0,
                    "credit": 0.0,
                },
                {
                    "company_id": branch_2.id,
                    "account_id": self.company_data["default_account_tax_sale"].id,
                    "debit": 45.0,
                    "credit": 0.0,
                },
                {
                    "company_id": branch_2.id,
                    "account_id": self.company_data["default_account_revenue"].id,
                    "debit": 0.0,
                    "credit": 45.0,
                },
                {
                    "company_id": branch_1.id,
                    "account_id": self.company_data["default_account_tax_sale"].id,
                    "debit": 30.0,
                    "credit": 0.0,
                },
                {
                    "company_id": branch_1.id,
                    "account_id": self.company_data["default_account_revenue"].id,
                    "debit": 0.0,
                    "credit": 30.0,
                },
            ],
        )

    def test_return_generation_change_periodicity_smaller_to_greater(self):
        existing_returns = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.env.company.id),
            ]
        )

        # Locking this one ("2023-12-01", "2023-12-31")
        with self.allow_pdf_render():
            existing_returns[0].action_validate()

        # Regenerate new returns without overriding posted ones
        with self._patch_returns_generation():
            self.env.company.account_return_periodicity = "2_months"

        existing_returns = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.env.company.id),
            ]
        )

        self.assert_return_dates_equal(
            existing_returns,
            [
                ("2023-12-01", "2023-12-31"),  # First one already posted
                ("2024-01-01", "2024-02-29"),
                ("2024-03-01", "2024-04-30"),
                ("2024-05-01", "2024-06-30"),
                ("2024-07-01", "2024-08-31"),
                ("2024-09-01", "2024-10-31"),
                ("2024-11-01", "2024-12-31"),
            ],
        )

    def test_return_generation_change_periodicity_greater_to_smaller(self):
        with self._patch_returns_generation():
            self.env.company.account_return_periodicity = "2_months"

        existing_returns = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.env.company.id),
            ]
        )

        self.assert_return_dates_equal(
            existing_returns,
            [
                ("2023-11-01", "2023-12-31"),
                ("2024-01-01", "2024-02-29"),
                ("2024-03-01", "2024-04-30"),
                ("2024-05-01", "2024-06-30"),
                ("2024-07-01", "2024-08-31"),
                ("2024-09-01", "2024-10-31"),
                ("2024-11-01", "2024-12-31"),
            ],
        )

        # Locking this one ("2023-11-01", "2023-12-31")
        with self.allow_pdf_render():
            existing_returns[0].action_validate()

        # Regenerate new returns without overriding posted ones
        with self._patch_returns_generation():
            self.env.company.account_return_periodicity = "monthly"

        existing_returns = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.env.company.id),
            ]
        )

        self.assert_return_dates_equal(
            existing_returns,
            [
                ("2023-11-01", "2023-12-31"),  # First one already posted
                ("2024-01-01", "2024-01-31"),
                ("2024-02-01", "2024-02-29"),
                ("2024-03-01", "2024-03-31"),
                ("2024-04-01", "2024-04-30"),
                ("2024-05-01", "2024-05-31"),
                ("2024-06-01", "2024-06-30"),
                ("2024-07-01", "2024-07-31"),
                ("2024-08-01", "2024-08-31"),
                ("2024-09-01", "2024-09-30"),
                ("2024-10-01", "2024-10-31"),
                ("2024-11-01", "2024-11-30"),
                ("2024-12-01", "2024-12-31"),
            ],
        )

    def test_return_generation_with_start_date(self):
        with self._patch_returns_generation():
            self.basic_return_type.deadline_start_date = "2024-12-01"
            self.env.company.account_return_periodicity = "4_months"

        existing_returns = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.env.company.id),
            ]
        )

        self.assert_return_dates_equal(
            existing_returns,
            [
                ("2023-12-01", "2024-03-31"),  # out of fy start
                ("2024-04-01", "2024-07-31"),
                ("2024-08-01", "2024-11-30"),
            ],
        )

    def test_return_generation_with_start_date_and_periodicity_change(self):
        existing_returns = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.env.company.id),
            ]
        )
        # Locking this one ("2023-12-01", "2023-12-31")
        with self.allow_pdf_render():
            existing_returns[0].action_validate()

        with self._patch_returns_generation():
            self.basic_return_type.deadline_start_date = "2024-12-01"
            self.env.company.account_return_periodicity = "4_months"

        existing_returns = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.env.company.id),
            ]
        )

        self.assert_return_dates_equal(
            existing_returns,
            [
                (
                    "2023-12-01",
                    "2023-12-31",
                ),  # first already posted so we won't create another one before it
                ("2024-04-01", "2024-07-31"),
                ("2024-08-01", "2024-11-30"),
            ],
        )

    def test_return_generation_with_all_return_posted(self):
        existing_returns = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.env.company.id),
            ]
        )

        self.assert_return_dates_equal(
            existing_returns,
            [
                ("2023-12-01", "2023-12-31"),
                ("2024-01-01", "2024-01-31"),
                ("2024-02-01", "2024-02-29"),
                ("2024-03-01", "2024-03-31"),
                ("2024-04-01", "2024-04-30"),
                ("2024-05-01", "2024-05-31"),
                ("2024-06-01", "2024-06-30"),
                ("2024-07-01", "2024-07-31"),
                ("2024-08-01", "2024-08-31"),
                ("2024-09-01", "2024-09-30"),
                ("2024-10-01", "2024-10-31"),
                ("2024-11-01", "2024-11-30"),
                ("2024-12-01", "2024-12-31"),
            ],
        )

        for existing_return in existing_returns:
            existing_return.action_mark_completed()

        self.assertRecordValues(
            existing_returns,
            [
                {"is_completed": True},
                {"is_completed": True},
                {"is_completed": True},
                {"is_completed": True},
                {"is_completed": True},
                {"is_completed": True},
                {"is_completed": True},
                {"is_completed": True},
                {"is_completed": True},
                {"is_completed": True},
                {"is_completed": True},
                {"is_completed": True},
                {"is_completed": True},
            ],
        )

        with self._patch_returns_generation():
            self.env.company.account_return_periodicity = "trimester"

        existing_returns = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.env.company.id),
            ]
        )
        self.assert_return_dates_equal(
            existing_returns,
            [
                ("2023-12-01", "2023-12-31"),
                ("2024-01-01", "2024-01-31"),
                ("2024-02-01", "2024-02-29"),
                ("2024-03-01", "2024-03-31"),
                ("2024-04-01", "2024-04-30"),
                ("2024-05-01", "2024-05-31"),
                ("2024-06-01", "2024-06-30"),
                ("2024-07-01", "2024-07-31"),
                ("2024-08-01", "2024-08-31"),
                ("2024-09-01", "2024-09-30"),
                ("2024-10-01", "2024-10-31"),
                ("2024-11-01", "2024-11-30"),
                ("2024-12-01", "2024-12-31"),
            ],
        )

    def test_return_fiscal_year_periodicity(self):
        with self._patch_returns_generation():
            self.env.company.fiscalyear_last_day = 31
            self.env.company.fiscalyear_last_month = "12"
            self.env["account.fiscal.year"].create(
                [
                    {
                        "name": "FY 2024_1",
                        "date_from": "2024-01-01",
                        "date_to": "2024-09-30",
                        "company_id": self.env.company.id,
                    },
                    {
                        "name": "FY 2024_2",
                        "date_from": "2024-10-01",
                        "date_to": "2024-12-31",
                        "company_id": self.env.company.id,
                    },
                ]
            )
            self.basic_return_type.deadline_periodicity = "fiscalyear"

            self.env["account.return.type"]._sync_all_returns(self.env.company)

        existing_returns = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.env.company.id),
            ]
        )
        self.assert_return_dates_equal(
            existing_returns,
            [
                ("2023-01-01", "2023-12-31"),
                ("2024-01-01", "2024-09-30"),
                ("2024-10-01", "2024-12-31"),
            ],
        )

    def test_period_boundaries_generation(self):
        def assert_period(input_date, expected_start, expected_end):
            period_start, period_end = self.basic_return_type._get_period_boundaries(
                self.env.company, input_date
            )
            self.assertEqual(
                period_start,
                expected_start,
                f"Period start date ({fields.Date.to_string(period_start)}) doesn't match the expected period start date: ({fields.Date.to_string(expected_start)})",
            )
            self.assertEqual(
                period_end,
                expected_end,
                f"Period end date ({fields.Date.to_string(period_end)}) doesn't match the expected period end date: ({fields.Date.to_string(expected_end)})",
            )

        # Periodicity only with default start_date
        self.env.company.account_return_periodicity = "monthly"
        assert_period(
            date(2024, 1, 1),
            expected_start=date(2024, 1, 1),
            expected_end=date(2024, 1, 31),
        )
        assert_period(
            date(2024, 9, 30),
            expected_start=date(2024, 9, 1),
            expected_end=date(2024, 9, 30),
        )
        assert_period(
            date(2024, 10, 1),
            expected_start=date(2024, 10, 1),
            expected_end=date(2024, 10, 31),
        )

        self.env.company.account_return_periodicity = "trimester"
        assert_period(
            date(2024, 1, 1),
            expected_start=date(2024, 1, 1),
            expected_end=date(2024, 3, 31),
        )
        assert_period(
            date(2024, 5, 1),
            expected_start=date(2024, 4, 1),
            expected_end=date(2024, 6, 30),
        )
        assert_period(
            date(2024, 9, 30),
            expected_start=date(2024, 7, 1),
            expected_end=date(2024, 9, 30),
        )
        assert_period(
            date(2024, 10, 1),
            expected_start=date(2024, 10, 1),
            expected_end=date(2024, 12, 31),
        )

        self.env.company.account_return_periodicity = "year"
        assert_period(
            date(2024, 1, 1),
            expected_start=date(2024, 1, 1),
            expected_end=date(2024, 12, 31),
        )
        assert_period(
            date(2023, 12, 31),
            expected_start=date(2023, 1, 1),
            expected_end=date(2023, 12, 31),
        )

        # Basic start dates
        self.env.company.account_return_periodicity = "trimester"
        self.basic_return_type.deadline_start_date = "2024-01-01"
        assert_period(
            date(2024, 1, 1),
            expected_start=date(2024, 1, 1),
            expected_end=date(2024, 3, 31),
        )
        assert_period(
            date(2024, 4, 1),
            expected_start=date(2024, 4, 1),
            expected_end=date(2024, 6, 30),
        )
        assert_period(
            date(2024, 5, 1),
            expected_start=date(2024, 4, 1),
            expected_end=date(2024, 6, 30),
        )
        assert_period(
            date(2024, 9, 30),
            expected_start=date(2024, 7, 1),
            expected_end=date(2024, 9, 30),
        )
        assert_period(
            date(2024, 10, 1),
            expected_start=date(2024, 10, 1),
            expected_end=date(2024, 12, 31),
        )

        self.basic_return_type.deadline_start_date = "2024-02-01"
        assert_period(
            date(2024, 1, 1),
            expected_start=date(2023, 11, 1),
            expected_end=date(2024, 1, 31),
        )
        assert_period(
            date(2024, 1, 31),
            expected_start=date(2023, 11, 1),
            expected_end=date(2024, 1, 31),
        )
        assert_period(
            date(2024, 2, 1),
            expected_start=date(2024, 2, 1),
            expected_end=date(2024, 4, 30),
        )
        assert_period(
            date(2024, 6, 1),
            expected_start=date(2024, 5, 1),
            expected_end=date(2024, 7, 31),
        )
        assert_period(
            date(2024, 10, 31),
            expected_start=date(2024, 8, 1),
            expected_end=date(2024, 10, 31),
        )
        assert_period(
            date(2024, 11, 1),
            expected_start=date(2024, 11, 1),
            expected_end=date(2025, 1, 31),
        )

        self.env.company.account_return_periodicity = "monthly"
        assert_period(
            date(2024, 2, 1),
            expected_start=date(2024, 2, 1),
            expected_end=date(2024, 2, 29),
        )
        assert_period(
            date(2024, 1, 31),
            expected_start=date(2024, 1, 1),
            expected_end=date(2024, 1, 31),
        )
        assert_period(
            date(2024, 1, 1),
            expected_start=date(2024, 1, 1),
            expected_end=date(2024, 1, 31),
        )
        assert_period(
            date(2024, 4, 1),
            expected_start=date(2024, 4, 1),
            expected_end=date(2024, 4, 30),
        )
        assert_period(
            date(2024, 12, 31),
            expected_start=date(2024, 12, 1),
            expected_end=date(2024, 12, 31),
        )
        assert_period(
            date(2024, 12, 1),
            expected_start=date(2024, 12, 1),
            expected_end=date(2024, 12, 31),
        )

        # Complexe start dates
        self.env.company.account_return_periodicity = "trimester"

        self.basic_return_type.deadline_start_date = "2024-02-06"
        assert_period(
            date(2024, 2, 5),
            expected_start=date(2023, 11, 6),
            expected_end=date(2024, 2, 5),
        )
        assert_period(
            date(2024, 2, 1),
            expected_start=date(2023, 11, 6),
            expected_end=date(2024, 2, 5),
        )
        assert_period(
            date(2023, 11, 7),
            expected_start=date(2023, 11, 6),
            expected_end=date(2024, 2, 5),
        )

        assert_period(
            date(2024, 2, 6),
            expected_start=date(2024, 2, 6),
            expected_end=date(2024, 5, 5),
        )
        assert_period(
            date(2024, 5, 5),
            expected_start=date(2024, 2, 6),
            expected_end=date(2024, 5, 5),
        )
        assert_period(
            date(2024, 4, 5),
            expected_start=date(2024, 2, 6),
            expected_end=date(2024, 5, 5),
        )

        assert_period(
            date(2024, 5, 6),
            expected_start=date(2024, 5, 6),
            expected_end=date(2024, 8, 5),
        )
        assert_period(
            date(2024, 11, 5),
            expected_start=date(2024, 8, 6),
            expected_end=date(2024, 11, 5),
        )
        assert_period(
            date(2024, 11, 6),
            expected_start=date(2024, 11, 6),
            expected_end=date(2025, 2, 5),
        )

        self.basic_return_type.deadline_start_date = "2024-06-06"
        assert_period(
            date(2024, 3, 5),
            expected_start=date(2023, 12, 6),
            expected_end=date(2024, 3, 5),
        )
        assert_period(
            date(2024, 6, 5),
            expected_start=date(2024, 3, 6),
            expected_end=date(2024, 6, 5),
        )
        assert_period(
            date(2024, 9, 5),
            expected_start=date(2024, 6, 6),
            expected_end=date(2024, 9, 5),
        )
        assert_period(
            date(2024, 12, 5),
            expected_start=date(2024, 9, 6),
            expected_end=date(2024, 12, 5),
        )

        self.env.company.account_return_periodicity = "monthly"
        assert_period(
            date(2024, 3, 5),
            expected_start=date(2024, 2, 6),
            expected_end=date(2024, 3, 5),
        )
        assert_period(
            date(2024, 3, 6),
            expected_start=date(2024, 3, 6),
            expected_end=date(2024, 4, 5),
        )
        assert_period(
            date(2024, 12, 5),
            expected_start=date(2024, 11, 6),
            expected_end=date(2024, 12, 5),
        )
        assert_period(
            date(2024, 12, 6),
            expected_start=date(2024, 12, 6),
            expected_end=date(2025, 1, 5),
        )
        assert_period(
            date(2025, 1, 5),
            expected_start=date(2024, 12, 6),
            expected_end=date(2025, 1, 5),
        )

        # Fiscal year
        self.basic_return_type.deadline_periodicity = "fiscalyear"
        self.env.company.fiscalyear_last_day = 31
        self.env.company.fiscalyear_last_month = "12"
        self.env["account.fiscal.year"].create(
            [
                {
                    "name": "FY 2024_1",
                    "date_from": "2024-01-01",
                    "date_to": "2024-09-30",
                    "company_id": self.env.company.id,
                },
                {
                    "name": "FY 2024_2",
                    "date_from": "2024-10-01",
                    "date_to": "2024-12-31",
                    "company_id": self.env.company.id,
                },
            ]
        )

        assert_period(
            date(2024, 5, 1),
            expected_start=date(2024, 1, 1),
            expected_end=date(2024, 9, 30),
        )
        assert_period(
            date(2024, 11, 5),
            expected_start=date(2024, 10, 1),
            expected_end=date(2024, 12, 31),
        )
        assert_period(
            date(2025, 5, 1),
            expected_start=date(2025, 1, 1),
            expected_end=date(2025, 12, 31),
        )

    def test_vat_closing_moves_with_lock_date(self):
        """Checks posting a closing entry after the tax lock date has been manually set is allowed."""
        self.env.company.tax_lock_date = "2024-12-31"

        first_return = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.env.company.id),
            ],
            order="date_from",
            limit=1,
        )
        self.assertEqual(len(first_return), 1)

        with self.allow_pdf_render():
            first_return.action_validate()

        self.assertTrue(first_return.closing_move_ids)

    def test_multicompany_generation_branches(self):
        with self._patch_returns_generation():
            branch_1_data = self.setup_other_company(
                name="Branch 1", parent_id=self.company_data["company"].id
            )
            branch_2_data = self.setup_other_company(
                name="Branch 2",
                vat="23434344",
                parent_id=self.company_data["company"].id,
                account_return_periodicity="semester",
                account_opening_date="2024-01-01",
            )

            branch_2_return = self.env["account.return"].search(
                [
                    ("type_id", "=", self.basic_return_type.id),
                    ("company_id", "=", branch_2_data["company"].id),
                ]
            )
            self.assert_return_dates_equal(
                branch_2_return,
                [
                    ("2023-07-01", "2023-12-31"),
                    ("2024-01-01", "2024-06-30"),
                    ("2024-07-01", "2024-12-31"),
                ],
            )
            self.assertEqual(branch_2_return.company_id, branch_2_data["company"])

            branch_1_1_data = self.setup_other_company(
                name="Branch 1-1", parent_id=branch_1_data["company"].id
            )
            branch_2_1_data = self.setup_other_company(
                name="Branch 2-1", parent_id=branch_2_data["company"].id
            )

            vat_tree_1 = (
                self.company_data["company"]
                + branch_1_data["company"]
                + branch_1_1_data["company"]
            )
            vat_tree_2 = branch_2_data["company"] + branch_2_1_data["company"]

            tree_1_returns = self.env["account.return"].search(
                [
                    ("type_id", "=", self.basic_return_type.id),
                    ("company_ids", "in", vat_tree_1.ids),
                ]
            )
            self.assert_return_dates_equal(
                tree_1_returns,
                [
                    ("2023-12-01", "2023-12-31"),
                    ("2024-01-01", "2024-01-31"),
                    ("2024-02-01", "2024-02-29"),
                    ("2024-03-01", "2024-03-31"),
                    ("2024-04-01", "2024-04-30"),
                    ("2024-05-01", "2024-05-31"),
                    ("2024-06-01", "2024-06-30"),
                    ("2024-07-01", "2024-07-31"),
                    ("2024-08-01", "2024-08-31"),
                    ("2024-09-01", "2024-09-30"),
                    ("2024-10-01", "2024-10-31"),
                    ("2024-11-01", "2024-11-30"),
                    ("2024-12-01", "2024-12-31"),
                ],
            )
            self.assertTrue(
                all(
                    tax_return.company_ids == vat_tree_1
                    for tax_return in tree_1_returns
                )
            )

            tree_2_returns = self.env["account.return"].search(
                [
                    ("type_id", "=", self.basic_return_type.id),
                    ("company_ids", "in", vat_tree_2.ids),
                ]
            )
            self.assert_return_dates_equal(
                tree_2_returns,
                [
                    ("2023-07-01", "2023-12-31"),
                    ("2024-01-01", "2024-06-30"),
                    ("2024-07-01", "2024-12-31"),
                ],
            )
            self.assertTrue(
                all(
                    tax_return.company_ids == vat_tree_2
                    for tax_return in tree_2_returns
                )
            )

    def test_multicompany_generation_tax_units(self):
        fiscal_country = self.company_data["company"].account_fiscal_country_id
        self.basic_return_type.report_id.country_id = (
            fiscal_country  # To make sure the tax unit is properly detected
        )
        other_company_data = self.setup_other_company(
            name="Tax unit other company", account_opening_date="2024-01-01"
        )
        unit_companies = self.company_data["company"] + other_company_data["company"]

        with self._patch_returns_generation():
            self.company_data["company"].account_return_periodicity = "2_months"
            other_company_data["company"].account_return_periodicity = "monthly"

        self.assert_return_dates_equal(
            self.env["account.return"].search(
                [
                    ("type_id", "=", self.basic_return_type.id),
                    ("company_ids", "in", self.company_data["company"].id),
                ]
            ),
            [
                ("2023-11-01", "2023-12-31"),
                ("2024-01-01", "2024-02-29"),
                ("2024-03-01", "2024-04-30"),
                ("2024-05-01", "2024-06-30"),
                ("2024-07-01", "2024-08-31"),
                ("2024-09-01", "2024-10-31"),
                ("2024-11-01", "2024-12-31"),
            ],
        )

        self.assert_return_dates_equal(
            self.env["account.return"].search(
                [
                    ("type_id", "=", self.basic_return_type.id),
                    ("company_ids", "in", other_company_data["company"].id),
                ]
            ),
            [
                ("2023-12-01", "2023-12-31"),
                ("2024-01-01", "2024-01-31"),
                ("2024-02-01", "2024-02-29"),
                ("2024-03-01", "2024-03-31"),
                ("2024-04-01", "2024-04-30"),
                ("2024-05-01", "2024-05-31"),
                ("2024-06-01", "2024-06-30"),
                ("2024-07-01", "2024-07-31"),
                ("2024-08-01", "2024-08-31"),
                ("2024-09-01", "2024-09-30"),
                ("2024-10-01", "2024-10-31"),
                ("2024-11-01", "2024-11-30"),
                ("2024-12-01", "2024-12-31"),
            ],
        )

        with self._patch_returns_generation():
            tax_unit = self.env["account.tax.unit"].create(
                {
                    "name": "Tax Unit",
                    "country_id": fiscal_country.id,
                    "main_company_id": self.company_data["company"].id,
                    "company_ids": unit_companies.ids,
                    "vat": "6537643",
                }
            )

        unit_returns = (
            self.env["account.return"]
            .search([("type_id", "=", self.basic_return_type.id)])
            .filtered(lambda r: r.company_ids == unit_companies)
        )

        self.assert_return_dates_equal(
            unit_returns,
            [
                ("2023-11-01", "2023-12-31"),
                ("2024-01-01", "2024-02-29"),
                ("2024-03-01", "2024-04-30"),
                ("2024-05-01", "2024-06-30"),
                ("2024-07-01", "2024-08-31"),
                ("2024-09-01", "2024-10-31"),
                ("2024-11-01", "2024-12-31"),
            ],
        )

        self.assertTrue(
            all(tax_return.company_ids == unit_companies for tax_return in unit_returns)
        )
        self.assertTrue(
            all(tax_return.tax_unit_id == tax_unit for tax_return in unit_returns)
        )

    def test_cannot_reset_if_subsequent_submitted(self):
        first_return, second_return = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.company_data["company"].id),
            ],
            order="date_to ASC",
            limit=2,
        )

        with self.allow_pdf_render():
            first_return.action_validate()
            second_return.action_validate()

        self.company_data["company"].tax_lock_date = (
            first_return.date_from - relativedelta(days=1)
        )

        with self.assertRaises(UserError):
            first_return.action_reset_tax_return_common()

        second_return.action_reset_tax_return_common()
        first_return.action_reset_tax_return_common()

    def test_cannot_submit_if_previous_not_submitted(self):
        first_return, second_return = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.company_data["company"].id),
            ],
            order="date_to ASC",
            limit=2,
        )

        with self.allow_pdf_render():
            with self.assertRaises(UserError):
                second_return.action_validate()

        with self.allow_pdf_render():
            first_return.action_validate()
            second_return.action_validate()

    def test_return_manual_creation_wizard_single_return(self):
        original_number_of_returns = self.env["account.return"].search_count([])
        wizard = self.env[
            "account.return.creation.wizard"
        ].create(
            [
                {
                    "date_from": "2023-11-01",
                    "date_to": "2023-11-30",  # December is auto generated by try_create using the normal range
                    "return_type_id": self.basic_return_type.id,
                }
            ]
        )
        wizard.action_create_manual_account_returns()
        new_number_of_returns = self.env["account.return"].search_count([])

        self.assertEqual(new_number_of_returns, original_number_of_returns + 1)

        new_return = self.env["account.return"].search(
            [("type_id", "=", self.basic_return_type.id)],
            order="date_from asc",
            limit=1,
        )
        self.assertRecordValues(
            new_return,
            [
                {
                    "company_id": self.env.company.id,
                    "type_id": self.basic_return_type.id,
                }
            ],
        )
        self.assert_return_dates_equal(new_return, [("2023-11-01", "2023-11-30")])

    def test_return_manual_creation_wizard_keeps_a_chosen_type_still_available(self):
        wizard = self.env["account.return.creation.wizard"].new({"category": "audit"})
        chosen = wizard.available_return_type_ids[:1]
        self.assertTrue(chosen)
        wizard.return_type_id = chosen

        wizard._compute_return_type_id()

        self.assertEqual(wizard.return_type_id, chosen)

        wizard.category = "account_return"
        wizard._compute_return_type_id()

        self.assertIn(wizard.return_type_id, wizard.available_return_type_ids)
        self.assertNotEqual(wizard.return_type_id, chosen)

    def test_return_manual_creation_wizard_multiple_returns(self):
        original_number_of_returns = self.env["account.return"].search_count([])
        wizard = self.env[
            "account.return.creation.wizard"
        ].create(
            [
                {
                    "date_from": "2023-10-01",
                    "date_to": "2023-11-30",  # December is auto generated by try_create using the normal range
                    "return_type_id": self.basic_return_type.id,
                }
            ]
        )
        wizard.action_create_manual_account_returns()

        new_number_of_returns = self.env["account.return"].search_count([])
        self.assertEqual(new_number_of_returns, original_number_of_returns + 2)

        new_returns = self.env["account.return"].search(
            [("type_id", "=", self.basic_return_type.id)], order="date_from", limit=2
        )
        self.assertEqual(new_returns[0].company_id.id, self.env.company.id)
        self.assert_return_dates_equal(
            new_returns,
            [
                ("2023-10-01", "2023-10-31"),
                ("2023-11-01", "2023-11-30"),
            ],
        )

    def test_return_creation_for_archived_return_month(self):
        existing_return = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.env.company.id),
                ("active", "=", True),
                ("date_from", "=", "2024-01-01"),
                ("date_to", "=", "2024-01-31"),
            ]
        )
        self.assertEqual(len(existing_return), 1)
        existing_return.action_archive()
        self.assertFalse(existing_return.active)

        # Create a return for a period where a return already existed but is now archived
        wizard = self.env["account.return.creation.wizard"].create(
            [
                {
                    "date_from": "2024-01-01",
                    "date_to": "2024-01-31",
                    "return_type_id": self.basic_return_type.id,
                }
            ]
        )
        wizard.action_create_manual_account_returns()
        domain = [
            ("company_id", "=", self.env.company.id),
            ("type_id", "=", self.basic_return_type.id),
            ("date_from", "=", "2024-01-01"),
            ("date_to", "=", "2024-01-31"),
            ("active", "=", True),
        ]
        self.assertEqual(self.env["account.return"].search_count(domain), 1)

        # Unarchiving old return should raise an error since a new return exists for same period
        with self.assertRaises(UserError):
            existing_return.action_unarchive()

    def test_return_manual_creation_wizard_wrong_dates(self):
        wizard = self.env["account.return.creation.wizard"].create(
            [
                {
                    "date_from": "2023-10-15",
                    "date_to": "2023-12-31",
                    "return_type_id": self.basic_return_type.id,
                }
            ]
        )
        self.assertEqual(wizard.show_warning_wrong_dates, True)
        wizard.write(
            {
                "date_from": "2023-12-01",
            }
        )
        self.assertEqual(wizard.show_warning_wrong_dates, False)

    def test_return_manual_creation_force_wrong_dates(self):
        wizard = self.env["account.return.creation.wizard"].create(
            [
                {
                    "date_from": "2023-10-15",
                    "date_to": "2023-12-31",
                    "return_type_id": self.basic_return_type.id,
                }
            ]
        )
        self.assertEqual(wizard.show_warning_wrong_dates, True)
        wizard.with_context(
            force_periodicity_violation=True
        ).action_create_manual_account_returns()

        generated_account_return = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.env.company.id),
                ("date_from", "=", "2023-10-15"),
                ("date_to", "=", "2023-12-31"),
            ]
        )
        self.assertEqual(len(generated_account_return), 1)

        options = generated_account_return._get_closing_report_options()
        self.assertEqual(options["date"]["filter"], "custom")
        self.assertEqual(options["date"]["date_from"], "2023-10-15")
        self.assertEqual(options["date"]["date_to"], "2023-12-31")

    def test_audit_manual_creation_allow_duplicates(self):
        wizard = self.env["account.return.creation.wizard"].create(
            [
                {
                    "category": "audit",
                    "date_from": "2024-01-01",
                    "date_to": "2024-12-31",
                    "return_type_id": self.audit_return_type.id,
                }
            ]
        )

        wizard.action_create_manual_account_returns()

        audits = self.env["account.return"].search(
            [
                ("type_id", "=", self.audit_return_type.id),
                ("company_id", "=", self.env.company.id),
                ("date_from", "=", "2024-01-01"),
                ("date_to", "=", "2024-12-31"),
            ]
        )

        self.assertEqual(len(audits), 2)

    def test_check_action_expression_context(self):
        company = self.env.company
        check = self.env["account.return.check"]
        context = {
            "company_id": company.id,
            "ref": lambda xml_id: self.env.ref(xml_id).id,
        }

        action_domain = check._parse_expression(
            "[('company_id', '=', company_id), ('currency_id', '=', ref('base.USD'))]",
            context,
        )

        self.assertEqual(
            action_domain,
            [
                ("company_id", "=", company.id),
                ("currency_id", "=", self.env.ref("base.USD").id),
            ],
        )

    def test_check_action_expression_invalid(self):
        check = self.env["account.return.check"]

        for expression in (
            "[",
            "unknown_helper()",
            "[1, unknown_helper(), 2]",
            "company_id.real()",
            "company_id()",
            "(lambda: 1)()",
            "ref()",
            "ref('base.USD', 'extra')",
        ):
            with (
                self.subTest(expression=expression),
                self.assertRaisesRegex(ValidationError, "Invalid code"),
            ):
                check._parse_expression(
                    expression,
                    {"company_id": self.env.company.id, "ref": lambda xml_id: 42},
                )

    def test_check_action_expression_rejects_keywords_before_calling_helper(self):
        check = self.env["account.return.check"]

        def ref(xml_id):
            self.fail("An unsupported call must not invoke its helper")

        for expression in (
            "ref('base.USD', ignored=unknown_helper())",
            "ref('base.USD', **{'ignored': 1})",
            "ref(xml_id='base.USD')",
        ):
            with (
                self.subTest(expression=expression),
                self.assertRaisesRegex(ValidationError, "Invalid code"),
            ):
                check._parse_expression(expression, {"ref": ref})

    def test_check_action_review_evaluates_template_overrides(self):
        template = self.env["account.return.check.template"].create(
            {
                "name": "Expression review",
                "return_type": self.audit_return_type.id,
                "additional_action_domain": "[('date', '>=', return_start_date)]",
                "additional_action_context": "{'return_id': active_id}",
                "additional_action_params": "{'currency_id': ref('base.USD')}",
            }
        )
        check = self.env["account.return.check"].create(
            {
                "name": "Expression review",
                "code": template.code,
                "return_id": self.audit_2024.id,
                "template_id": template.id,
                "action": {
                    "type": "ir.actions.client",
                    "tag": "account_report",
                    "domain": "[('company_id', '=', company_id)]",
                    "context": "{'active_model': active_model}",
                    "params": "{'report_id': ref('account.trial_balance_report')}",
                },
            }
        )

        action = check.action_review()

        self.assertEqual(
            action["domain"],
            [("company_id", "=", self.env.company.id), ("date", ">=", "2024-01-01")],
        )
        self.assertEqual(
            action["context"],
            {"active_model": "account.return", "return_id": self.audit_2024.id},
        )
        self.assertEqual(
            action["params"],
            {
                "report_id": self.env.ref("account.trial_balance_report").id,
                "currency_id": self.env.ref("base.USD").id,
            },
        )
        self.assertEqual(action["active_id"], self.audit_2024.id)
        self.assertEqual(action["active_model"], "account.return")
        self.assertIsInstance(check.action["domain"], str)

        template.additional_action_domain = "[('company_id', '=', company_id())]"
        with self.assertRaisesRegex(ValidationError, "Invalid code"):
            check.action_review()

    def test_account_return_check_template_basic(self):
        # 1. Create audit return type
        audit_return_type = self.env["account.return.type"].create(
            [
                {
                    "category": "audit",
                    "default_deadline_periodicity": "year",
                    "default_deadline_start_date": "2024-01-01",
                    "name": "Audit",
                }
            ]
        )

        # 2. Create check templates
        mail_activity_type = self.env.ref("mail.mail_activity_data_email")
        templates = self.env["account.return.check.template"].create(
            [
                {  # Manual Check with activity
                    "name": "Check 1",
                    "code": "_template_checks_1",
                    "return_type": audit_return_type.id,
                    "type": "check",
                    "model": False,
                    "activity_type": mail_activity_type.id,
                },
                {  # Auto Check Failing
                    "name": "Check 2",
                    "code": "_template_checks_2",
                    "return_type": audit_return_type.id,
                    "type": "check",
                    "model": "account.move",
                    "domain": "[('state', '=', 'draft')]",
                    "cycle": "equity",
                },
                {  # Auto Check Succeeding
                    "name": "Check 3",
                    "code": "_template_checks_3",
                    "return_type": audit_return_type.id,
                    "type": "check",
                    "model": "account.move",
                    "domain": "[('amount_total', '=', 94329.90)]",
                },
                {  # Upload File
                    "name": "Check 4",
                    "code": "_template_checks_4",
                    "return_type": audit_return_type.id,
                    "type": "file",
                },
            ]
        )

        # 3. Create audit return
        account_return = audit_return_type.with_context(
            forced_date_from=fields.Date.from_string("2024-01-01"),
            forced_date_to=fields.Date.from_string("2024-12-31"),
        )._try_create_returns_for_fiscal_year(self.env.company, False)

        self.assertEqual(
            len(account_return),
            1,
            "Only one return should be created for a period of one year using an annual return type.",
        )

        # 4. Create draft invoice
        self.init_invoice("out_invoice", amounts=[10], invoice_date="2024-01-01")

        # 5. Refresh checks
        account_return.refresh_checks()

        self.assertEqual(len(account_return.check_ids), 4)

        self.assertEqual(
            account_return.activity_ids[0].activity_type_id, mail_activity_type
        )

        account_return.refresh_checks()

        self.assertEqual(len(account_return.check_ids), 4)
        self.assertEqual(len(account_return.activity_ids), 1)

        self.assert_checks_equal(
            account_return,
            [
                {  # Manual Check with activity
                    "name": "Check 1",
                    "code": "_template_checks_1",
                    "message": False,
                    "type": "check",
                    "result": "todo",
                    "return_id": account_return,
                    "template_id": templates[0],
                },
                {  # Auto Check Failing
                    "name": "Check 2",
                    "code": "_template_checks_2",
                    "message": False,
                    "type": "check",
                    "result": "anomaly",
                    "return_id": account_return,
                    "cycle": "equity",
                    "template_id": templates[1],
                },
                {  # Auto Check Succeeding
                    "name": "Check 3",
                    "code": "_template_checks_3",
                    "message": False,
                    "type": "check",
                    "result": "reviewed",
                    "return_id": account_return,
                    "template_id": templates[2],
                },
                {  # Upload File
                    "name": "Check 4",
                    "code": "_template_checks_4",
                    "message": False,
                    "type": "file",
                    "result": "todo",
                    "return_id": account_return,
                    "cycle": "other",
                    "template_id": templates[3],
                },
            ],
        )

    def test_account_return_check_template_file(self):
        return_type = self.env["account.return.type"].create(
            [
                {
                    "category": "audit",
                    "default_deadline_periodicity": "year",
                    "default_deadline_start_date": "2024-01-01",
                    "name": "Audit",
                }
            ]
        )

        template = self.env["account.return.check.template"].create(
            [
                {  # Upload File
                    "name": "Check 1",
                    "code": "_template_checks_1",
                    "return_type": return_type.id,
                    "type": "file",
                }
            ]
        )

        account_return = return_type.with_context(
            forced_date_from=fields.Date.from_string("2024-01-01"),
            forced_date_to=fields.Date.from_string("2024-12-31"),
        )._try_create_returns_for_fiscal_year(self.env.company, False)

        account_return.refresh_checks()

        self.assert_checks_equal(
            account_return,
            [
                {
                    "name": "Check 1",
                    "code": "_template_checks_1",
                    "type": "file",
                    "result": "todo",
                    "return_id": account_return,
                    "template_id": template,
                }
            ],
        )

        attachment = self.env["ir.attachment"].create(
            {
                "res_model": "account.return.check",
                "res_id": account_return.check_ids[0].id,
                "name": "attachment",
                "company_id": self.env.company.id,
            }
        )

        account_return.check_ids[0].attachment_ids |= attachment

        self.assert_checks_equal(
            account_return,
            [
                {
                    "name": "Check 1",
                    "code": "_template_checks_1",
                    "type": "file",
                    "result": "todo",
                    "refresh_result": False,
                    "return_id": account_return,
                    "template_id": template,
                }
            ],
        )

        account_return.check_ids[0].action_unlink_attachments()

        self.assert_checks_equal(
            account_return,
            [
                {
                    "name": "Check 1",
                    "code": "_template_checks_1",
                    "type": "file",
                    "result": "todo",
                    "refresh_result": True,
                    "return_id": account_return,
                    "template_id": template,
                }
            ],
        )

    def test_account_return_check_template_changing_type(self):
        return_type = self.env["account.return.type"].create(
            [
                {
                    "category": "audit",
                    "default_deadline_periodicity": "year",
                    "default_deadline_start_date": "2024-01-01",
                    "name": "Audit",
                }
            ]
        )

        template = self.env["account.return.check.template"].create(
            [
                {  # Upload File
                    "name": "Check 1",
                    "code": "_template_checks_1",
                    "return_type": return_type.id,
                    "type": "file",
                }
            ]
        )

        account_return = return_type.with_context(
            forced_date_from=fields.Date.from_string("2024-01-01"),
            forced_date_to=fields.Date.from_string("2024-12-31"),
        )._try_create_returns_for_fiscal_year(self.env.company, False)

        account_return.refresh_checks()

        attachment = self.env["ir.attachment"].create(
            {
                "res_model": "account.return.check",
                "res_id": account_return.check_ids[0].id,
                "name": "attachment",
                "company_id": self.env.company.id,
            }
        )

        account_return.check_ids[0].attachment_ids |= attachment

        self.assert_checks_equal(
            account_return,
            [
                {
                    "name": "Check 1",
                    "code": "_template_checks_1",
                    "type": "file",
                    "result": "todo",
                    "refresh_result": False,
                    "return_id": account_return,
                    "template_id": template,
                    "attachment_ids": attachment,
                }
            ],
        )

        template.type = "check"
        account_return.refresh_checks()

        self.assert_checks_equal(
            account_return,
            [
                {
                    "code": "_template_checks_1",
                    "type": "check",
                    "result": "todo",
                    "refresh_result": False,
                    "attachment_ids": self.env["ir.attachment"],
                }
            ],
        )

        template.type = "file"
        account_return.refresh_checks()

        self.assert_checks_equal(
            account_return,
            [
                {
                    "code": "_template_checks_1",
                    "type": "file",
                    "result": "todo",
                    "attachment_ids": self.env["ir.attachment"],
                }
            ],
        )

    def test_reset_account_reviewed_audit_status_on_balance_change(self):
        audit_return_type = self.env["account.return.type"].create(
            [
                {
                    "category": "audit",
                    "default_deadline_periodicity": "monthly",
                    "default_deadline_start_date": "2024-01-01",
                    "name": "Audit",
                }
            ]
        )

        audits = self.env["account.return"]
        audits |= audit_return_type.with_context(
            forced_date_from=fields.Date.from_string("2024-01-01"),
            forced_date_to=fields.Date.from_string("2024-06-30"),
        )._try_create_returns_for_fiscal_year(self.env.company, False)

        self.assertEqual(len(audits), 6)

        invoices = self.env["account.move"]
        invoices |= self.init_invoice(
            "out_invoice", amounts=[10], invoice_date="2024-01-21"
        )
        invoices |= self.init_invoice(
            "out_invoice", amounts=[10], invoice_date="2024-01-22"
        )
        invoices |= self.init_invoice(
            "out_invoice", amounts=[10], invoice_date="2024-02-21"
        )
        # No invoice in March
        invoices |= self.init_invoice(
            "out_invoice", amounts=[10], invoice_date="2024-04-21"
        )
        invoices |= self.init_invoice(
            "out_invoice", amounts=[10], invoice_date="2024-04-21"
        )
        invoices |= self.init_invoice(
            "out_invoice", amounts=[10], invoice_date="2024-05-21"
        )
        invoices |= self.init_invoice(
            "out_invoice", amounts=[10], invoice_date="2024-06-21"
        )
        invoices |= self.init_invoice(
            "out_invoice", amounts=[10], invoice_date="2025-03-21"
        )

        # Set account audit status to 'reviewed'
        accounts = invoices.line_ids.account_id
        for account in accounts:
            for account_status in account.account_status:
                account_status.status = "reviewed"

        invoices.action_post()

        for audit in audits:
            for account in accounts:
                audit_status = account.with_context(
                    working_file_id=audit.id
                ).audit_status
                if audit.date_from == fields.Date.from_string("2024-03-01"):
                    # No reset, as no effect on accounts in March
                    self.assertEqual("reviewed", audit_status)
                else:
                    self.assertEqual("todo", audit_status)

    def test_basic_return_checks(self):

        january_return = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.env.company.id),
                ("date_from", "=", "2024-01-01"),
                ("date_to", "=", "2024-01-31"),
            ]
        )

        self.assertEqual(
            len(january_return), 1, "There should be one return for January 2024"
        )

        # check_company_data
        self.env.company.vat = False
        # check_match_all_bank_entries
        bank_journal = self.company_data["default_journal_bank"]
        bank_statement_line = self.env["account.bank.statement.line"].create(
            {
                "payment_ref": "To be reconciled",
                "company_id": self.env.company.id,
                "journal_id": bank_journal.id,
                "partner_id": self.partner_a.id,
                "amount": 100.0,
                "date": "2024-01-01",
            }
        )
        # check_draft_entries
        draft_invoice = self.init_invoice(
            "out_invoice", amounts=[10], invoice_date="2024-01-01"
        )
        # check_bills_attachment
        bill = self.init_invoice(
            "in_invoice", amounts=[10], invoice_date="2024-01-01", post=True
        )

        january_return.refresh_checks()
        checks = january_return.check_ids

        self.assert_return_contains_checks(
            january_return,
            [
                "check_match_all_bank_entries",
                "check_bills_attachment",
                "check_company_data",
                "check_draft_entries",
                "check_tax_countries",
            ],
        )

        company_data_check = checks.filtered(lambda c: c.code == "check_company_data")
        match_all_bank_entries_check = checks.filtered(
            lambda c: c.code == "check_match_all_bank_entries"
        )
        draft_entries_check = checks.filtered(lambda c: c.code == "check_draft_entries")
        bills_attachment_check = checks.filtered(
            lambda c: c.code == "check_bills_attachment"
        )

        self.assertEqual(
            company_data_check.result,
            "anomaly",
            "The company data check should fail as the VAT is not set",
        )
        self.assertEqual(
            match_all_bank_entries_check.result,
            "anomaly",
            "The match all bank entries check should fail as there's a bank statement line but not reconciled",
        )
        self.assertEqual(
            draft_entries_check.result,
            "anomaly",
            "The draft entries check should fail as the invoice is not posted",
        )
        self.assertEqual(
            bills_attachment_check.result,
            "anomaly",
            "The bills attachment check should fail as the bill has no attachment",
        )

        self.env.company.vat = "BE123456789"
        draft_invoice.action_post()
        bill.attachment_ids = self.env["ir.attachment"].create(
            {
                "name": "bill_attachment.pdf",
                "res_model": "account.move",
                "res_id": bill.id,
                "type": "binary",
                "datas": b"",
                "mimetype": "application/pdf",
                "company_id": self.env.company.id,
            }
        )
        payment = self.env["account.payment"].create(
            {
                "amount": 100.0,
                "payment_type": "inbound",
                "date": "2024-01-01",
                "journal_id": bank_journal.id,
                "partner_id": self.partner_a.id,
            }
        )
        payment.action_post()
        payment_line = payment.move_id.line_ids.filtered(
            lambda line: (
                line.account_id == payment.payment_channel_id.payment_account_id
            )
        )
        bank_statement_line.set_line_bank_statement_line(payment_line.id)

        january_return.refresh_checks()

        self.assertEqual(
            company_data_check.result,
            "reviewed",
            "The company data check should succeed as the VAT is set",
        )
        self.assertEqual(
            match_all_bank_entries_check.result,
            "reviewed",
            "The match all bank entries check should succeed as the bank statement line is reconciled",
        )
        self.assertEqual(
            draft_entries_check.result,
            "reviewed",
            "The draft entries check should succeed as the invoice is posted",
        )
        self.assertEqual(
            bills_attachment_check.result,
            "reviewed",
            "The bills attachment check should succeed as the bill has an attachment",
        )

    def test_ec_sales_list_return_checks(self):
        """Checks that the checks for the EC Sales List return are correctly generated."""
        ec_sales_list_return = self.env["account.return"].search(
            [
                ("type_id", "=", self.ec_sales_list_return_type.id),
                ("company_id", "=", self.env.company.id),
                ("date_from", "=", "2024-01-01"),
                ("date_to", "=", "2024-01-31"),
            ]
        )

        self.assertEqual(
            len(ec_sales_list_return),
            1,
            "There should be one EC Sales List return for January 2024",
        )
        ec_sales_list_return.refresh_checks()
        checks = ec_sales_list_return.check_ids

        self.assert_return_contains_checks(
            ec_sales_list_return,
            [
                "goods_service_classification",
                "eu_cross_border",
                "reverse_charge_mentioned",
                "no_partners_without_vat",
            ],
        )

        eu_cross_border_check = checks.filtered(lambda c: c.code == "eu_cross_border")
        no_partners_without_vat_check = checks.filtered(
            lambda c: c.code == "no_partners_without_vat"
        )

        self.assertEqual(
            eu_cross_border_check.result,
            "reviewed",
            "The EU cross border check should succeed as there is a cross-border transaction",
        )
        self.assertEqual(
            no_partners_without_vat_check.result,
            "reviewed",
            "The no partners without VAT check should succeed as there is a partner without VAT",
        )

    def test_annual_return_checks(self):
        """Checks that the checks for the Annual return are correctly generated."""
        annual_return = self.env["account.return"].search(
            [
                ("type_id", "=", self.annual_return_type.id),
                ("company_id", "=", self.env.company.id),
                ("date_from", "=", "2024-01-01"),
                ("date_to", "=", "2024-12-31"),
            ]
        )

        self.assertEqual(
            len(annual_return), 1, "There should be one Annual return for 2024"
        )

        bank_journal = self.company_data["default_journal_bank"]
        bank_statement_line = self.env["account.bank.statement.line"].create(
            {
                "payment_ref": "To be reconciled",
                "company_id": self.env.company.id,
                "journal_id": bank_journal.id,
                "partner_id": self.partner_a.id,
                "amount": 100.0,
                "date": "2024-01-01",
            }
        )
        draft_invoice = self.init_invoice(
            "out_invoice", amounts=[10], invoice_date="2024-01-01"
        )

        annual_return.refresh_checks()
        checks = annual_return.check_ids

        self.assert_return_contains_checks(
            annual_return,
            [
                "check_unkown_partner_payables",
                "check_unkown_partner_receivables",
                "check_bank_reconcile",
                "check_deferred_entries",
                "earnings_allocation",
                "manual_adjustments",
                "check_draft_entries",
                "check_overdue_payables",
                "check_overdue_receivables",
                "check_total_receivables",
                "check_total_payables",
            ],
        )

        check_unkown_partner_payables = checks.filtered(
            lambda c: c.code == "check_unkown_partner_payables"
        )
        check_unkown_partner_receivables = checks.filtered(
            lambda c: c.code == "check_unkown_partner_receivables"
        )
        check_bank_reconcile = checks.filtered(
            lambda c: c.code == "check_bank_reconcile"
        )
        check_deferred_entries = checks.filtered(
            lambda c: c.code == "check_deferred_entries"
        )
        earnings_allocation = checks.filtered(lambda c: c.code == "earnings_allocation")
        check_draft_entries = checks.filtered(lambda c: c.code == "check_draft_entries")
        manual_adjustments = checks.filtered(lambda c: c.code == "manual_adjustments")
        check_overdue_payables = checks.filtered(
            lambda c: c.code == "check_overdue_payables"
        )
        check_overdue_receivables = checks.filtered(
            lambda c: c.code == "check_overdue_receivables"
        )
        check_total_receivables = checks.filtered(
            lambda c: c.code == "check_total_receivables"
        )
        check_total_payables = checks.filtered(
            lambda c: c.code == "check_total_payables"
        )

        self.assertEqual(
            check_bank_reconcile.result,
            "anomaly",
            "The bank reconcile check should fail as the bank statement line is not reconciled",
        )
        self.assertEqual(
            check_draft_entries.result,
            "anomaly",
            "The draft entries check should fail as the invoice is not posted",
        )
        self.assertEqual(
            check_overdue_payables.result,
            "reviewed",
            "The overdue payables check should succeed as the payable is paid",
        )

        payment = self.env["account.payment"].create(
            {
                "amount": 100.0,
                "payment_type": "inbound",
                "date": "2024-01-01",
                "journal_id": bank_journal.id,
                "partner_id": self.partner_a.id,
            }
        )
        payment.action_post()
        payment_line = payment.move_id.line_ids.filtered(
            lambda line: (
                line.account_id == payment.payment_channel_id.payment_account_id
            )
        )
        bank_statement_line.set_line_bank_statement_line(payment_line.id)
        draft_invoice.action_post()
        self.init_invoice(
            "in_invoice", amounts=[400], invoice_date="2023-05-01", post=True
        )
        self.init_invoice(
            "out_invoice", amounts=[200], invoice_date="2023-06-01", post=True
        )

        annual_return.refresh_checks()

        self.assertEqual(
            check_unkown_partner_payables.result,
            "reviewed",
            "The unknown partner payables check should succeed as the invoice is posted",
        )
        self.assertEqual(
            check_unkown_partner_receivables.result,
            "reviewed",
            "The unknown partner receivables check should succeed as the invoice is posted",
        )
        self.assertEqual(
            check_bank_reconcile.result,
            "reviewed",
            "The bank reconcile check should succeed as the bank statement line is reconciled",
        )
        self.assertEqual(
            check_deferred_entries.result,
            "todo",
            "The deferred entries check should be todo as it requires user intervention",
        )
        self.assertEqual(
            earnings_allocation.result,
            "todo",
            "The earnings allocation check should be todo as it requires user intervention",
        )
        self.assertEqual(
            manual_adjustments.result,
            "todo",
            "The manual adjustments check should be todo as it requires user intervention",
        )
        self.assertEqual(
            check_draft_entries.result,
            "reviewed",
            "The draft entries check should succeed as the invoice is posted",
        )
        self.assertEqual(
            check_overdue_payables.result,
            "anomaly",
            "The overdue payables check should fail as the payable is not paid",
        )
        self.assertEqual(
            check_overdue_receivables.result,
            "anomaly",
            "The overdue receivables check should fail as the receivable is not paid",
        )
        self.assertEqual(
            check_total_receivables.result,
            "reviewed",
            "The total receivables check should succeed as the invoice is posted",
        )
        self.assertEqual(
            check_total_payables.result,
            "reviewed",
            "The total payables check should succeed as the invoice is posted",
        )

    def test_tax_return_recoverable_amounts(self):
        tax_account = self.env["account.account"].create(
            {
                "name": "Tax Account",
                "code": "test.tax.account",
                "account_type": "liability_current",
            }
        )

        sale_tax = self.env["account.tax"].create(
            {
                "name": "sale tax",
                "amount": 21,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "invoice_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": tax_account.id,
                        }
                    ),
                ],
                "refund_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": tax_account.id,
                        }
                    ),
                ],
            }
        )

        purchase_tax = self.env["account.tax"].create(
            {
                "name": "purchase tax",
                "amount": 21,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "invoice_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": tax_account.id,
                        }
                    ),
                ],
                "refund_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": tax_account.id,
                        }
                    ),
                ],
            }
        )

        (sale_tax + purchase_tax).repartition_line_ids.filtered(
            lambda x: x.repartition_type == "tax"
        ).write({"account_id": tax_account.id})

        tax_receivable = self.company_data["default_tax_account_receivable"]
        tax_payable = self.company_data["default_tax_account_payable"]

        self.init_invoice(
            "in_invoice",
            amounts=[10],
            taxes=purchase_tax,
            post=True,
            invoice_date="2024-01-01",
        )
        self.init_invoice(
            "out_invoice",
            amounts=[20],
            taxes=sale_tax,
            post=True,
            invoice_date="2024-02-01",
        )
        self.init_invoice(
            "out_invoice",
            amounts=[30],
            taxes=sale_tax,
            post=True,
            invoice_date="2024-03-01",
        )
        self.init_invoice(
            "in_invoice",
            amounts=[100],
            taxes=purchase_tax,
            post=True,
            invoice_date="2024-04-01",
        )
        self.init_invoice(
            "out_invoice",
            amounts=[10],
            taxes=sale_tax,
            post=True,
            invoice_date="2024-05-01",
        )
        self.init_invoice(
            "out_invoice",
            amounts=[90],
            taxes=sale_tax,
            post=True,
            invoice_date="2024-06-01",
        )
        self.init_invoice(
            "out_invoice",
            amounts=[50],
            taxes=sale_tax,
            post=True,
            invoice_date="2024-07-01",
        )

        # Mark december return completed
        december_return = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("date_to", "=", "2023-12-31"),
            ]
        )
        december_return.action_mark_completed()

        # January Return: 2.10 to recover
        january_return = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("date_to", "=", "2024-01-31"),
            ]
        )
        with self.allow_pdf_render():
            january_return.action_validate(bypass_failing_tests=True)
        self.assertEqual(january_return.total_amount_to_pay, -2.1)
        self.assertEqual(january_return.period_amount_to_pay, -2.1)
        self.assertRecordValues(
            january_return.closing_move_ids.line_ids,
            [
                {"account_id": tax_account.id, "debit": 0.0, "credit": 2.1},
                {"account_id": tax_receivable.id, "debit": 2.1, "credit": 0.0},
            ],
        )

        # February Return: 4.20 in period -2.10 to recover from January
        february_return = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("date_to", "=", "2024-02-29"),
            ]
        )
        with self.allow_pdf_render():
            february_return.action_validate(bypass_failing_tests=True)
        self.assertEqual(february_return.total_amount_to_pay, 2.1)
        self.assertEqual(february_return.period_amount_to_pay, 4.2)
        self.assertRecordValues(
            february_return.closing_move_ids.line_ids,
            [
                {"account_id": tax_account.id, "debit": 4.2, "credit": 0.0},
                {"account_id": tax_receivable.id, "debit": 0.0, "credit": 2.1},
                {"account_id": tax_payable.id, "debit": 0.0, "credit": 2.1},
            ],
        )

        # March Return: 6.3 in period; nothing coming from previous periods
        march_return = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("date_to", "=", "2024-03-31"),
            ]
        )
        with self.allow_pdf_render():
            march_return.action_validate(bypass_failing_tests=True)
        self.assertEqual(march_return.total_amount_to_pay, 6.3)
        self.assertEqual(march_return.period_amount_to_pay, 6.3)
        self.assertRecordValues(
            march_return.closing_move_ids.line_ids,
            [
                {"account_id": tax_account.id, "debit": 6.3, "credit": 0.0},
                {"account_id": tax_payable.id, "debit": 0.0, "credit": 6.3},
            ],
        )

        # April Return: 21 in period; to recover
        april_return = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("date_to", "=", "2024-04-30"),
            ]
        )
        with self.allow_pdf_render():
            april_return.action_validate(bypass_failing_tests=True)
        self.assertEqual(april_return.total_amount_to_pay, -21.0)
        self.assertEqual(april_return.period_amount_to_pay, -21.0)
        self.assertRecordValues(
            april_return.closing_move_ids.line_ids,
            [
                {"account_id": tax_account.id, "debit": 0.0, "credit": 21.0},
                {"account_id": tax_receivable.id, "debit": 21.0, "credit": 0.0},
            ],
        )

        # May Return: 2.1 in period ; 21 to recover => Nothing to pay in period, still 18.90 to recover in next periods
        may_return = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("date_to", "=", "2024-05-31"),
            ]
        )
        with self.allow_pdf_render():
            may_return.action_validate(bypass_failing_tests=True)
        self.assertEqual(may_return.total_amount_to_pay, -18.9)
        self.assertEqual(may_return.period_amount_to_pay, 2.10)
        self.assertRecordValues(
            may_return.closing_move_ids.line_ids,
            [
                {"account_id": tax_account.id, "debit": 2.1, "credit": 0.0},
                {"account_id": tax_receivable.id, "debit": 0.0, "credit": 21.0},
                {"account_id": tax_receivable.id, "debit": 18.9, "credit": 0.0},
            ],
        )

        # June Return: 18.90 in period - 18.90 to recover => nothing to pay
        june_return = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("date_to", "=", "2024-06-30"),
            ]
        )
        with self.allow_pdf_render():
            june_return.action_validate(bypass_failing_tests=True)
        self.assertEqual(june_return.total_amount_to_pay, 0.0)
        self.assertEqual(june_return.period_amount_to_pay, 18.9)
        self.assertRecordValues(
            june_return.closing_move_ids.line_ids,
            [
                {"account_id": tax_account.id, "debit": 18.9, "credit": 0.0},
                {"account_id": tax_receivable.id, "debit": 0.0, "credit": 18.9},
            ],
        )

        other_account = self.company_data["default_account_revenue"]
        # Generating an amount to recover of 200 which is not generated by a closing
        self.env["account.move"].create(
            {
                "date": "2024-07-01",
                "line_ids": [
                    Command.create({"debit": 200, "account_id": other_account.id}),
                    Command.create({"credit": 200, "account_id": tax_receivable.id}),
                ],
            }
        ).action_post()

        july_return = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("date_to", "=", "2024-07-31"),
            ]
        )
        with self.allow_pdf_render():
            july_return.action_validate(bypass_failing_tests=True)
        self.assertEqual(july_return.total_amount_to_pay, 210.5)
        self.assertEqual(july_return.period_amount_to_pay, 10.5)
        self.assertRecordValues(
            july_return.closing_move_ids.line_ids,
            [
                {"account_id": tax_account.id, "debit": 10.5, "credit": 0.0},
                {"account_id": tax_receivable.id, "debit": 200.0, "credit": 0.0},
                {"account_id": tax_payable.id, "debit": 0.0, "credit": 210.5},
            ],
        )

    def test_account_return_duplicates(self):
        self.basic_return_type.with_context(
            forced_date_from=fields.Date.from_string("2024-01-01"),
            forced_date_to=fields.Date.from_string("2024-01-31"),
        )._try_create_returns_for_fiscal_year(self.env.company, False)

        wizard = self.env["account.return.creation.wizard"].create(
            [
                {
                    "return_type_id": self.basic_return_type.id,
                    "company_id": self.env.company.id,
                    "date_from": fields.Date.from_string("2024-01-01"),
                    "date_to": fields.Date.from_string("2024-01-31"),
                    "category": "account_return",
                }
            ]
        )

        # Should raise an error as we cannot have duplicate returns for return type of category 'account_return'
        with self.assertRaises(UserError):
            wizard.action_create_manual_account_returns()

        # Simulate two creation of an audit for the same period, it should be allowed
        audit_return_type = self.env["account.return.type"].create(
            [
                {
                    "category": "audit",
                    "default_deadline_periodicity": "monthly",
                    "default_deadline_start_date": "2024-01-01",
                    "name": "Audit",
                }
            ]
        )

        wizard = self.env["account.return.creation.wizard"].create(
            [
                {
                    "return_type_id": audit_return_type.id,
                    "company_id": self.env.company.id,
                    "date_from": fields.Date.from_string("2024-01-01"),
                    "date_to": fields.Date.from_string("2024-12-31"),
                    "category": "audit",
                }
            ]
        )
        wizard.action_create_manual_account_returns()

        wizard = self.env["account.return.creation.wizard"].create(
            [
                {
                    "return_type_id": audit_return_type.id,
                    "company_id": self.env.company.id,
                    "date_from": fields.Date.from_string("2024-01-01"),
                    "date_to": fields.Date.from_string("2024-12-31"),
                    "category": "audit",
                }
            ]
        )
        wizard.action_create_manual_account_returns()

    def test_translations_checks(self):
        def patched_get_python_translations(self, credential, env):
            return ReadonlyDict(
                {
                    "Draft entries": "Écritures en brouillon",
                    "Review and post draft invoices and bills in the period, or change their accounting date.": "Vérifiez et validez les factures et factures fournisseurs en brouillon pour la période, "
                    "ou modifiez leur date comptable.",
                }
            )

        def _patch_get_python_translations():
            return patch.object(
                CodeTranslations,
                "get_python_translations",
                patched_get_python_translations,
            )

        with _patch_get_python_translations():
            self.env["res.lang"]._activate_lang("fr_FR")

            january_return = self.env["account.return"].search(
                [
                    ("type_id", "=", self.basic_return_type.id),
                    ("company_id", "=", self.env.company.id),
                    ("date_from", "=", "2024-01-01"),
                    ("date_to", "=", "2024-01-31"),
                ]
            )

            january_return.refresh_checks()
            checks = january_return.check_ids

            draft_entries_check = checks.filtered(
                lambda c: c.code == "check_draft_entries"
            )

            self.assertEqual(draft_entries_check.name, "Draft entries")
            self.assertEqual(
                draft_entries_check.message,
                "Review and post draft invoices and bills in the period, or change their accounting date.",
            )

            self.assertEqual(
                draft_entries_check.with_context({"lang": "fr_FR"}).name,
                "Écritures en brouillon",
            )
            self.assertEqual(
                draft_entries_check.with_context({"lang": "fr_FR"}).message,
                "Vérifiez et validez les factures et factures fournisseurs en brouillon pour la période, ou modifiez leur date comptable.",
            )

    def test_audit_balances_account(self):
        self.init_invoice(
            "out_invoice", amounts=[20], post=True, invoice_date="2024-02-01"
        )
        self.init_invoice(
            "out_invoice", amounts=[30], post=True, invoice_date="2025-02-01"
        )

        self.assertEqual(
            self.company_data["default_account_receivable"]
            .with_context(working_file_id=self.audit_2024.id)
            .audit_balance,
            20,
        )
        self.assertEqual(
            self.company_data["default_account_receivable"]
            .with_context(working_file_id=self.audit_2024.id)
            .audit_previous_balance,
            0,
        )
        self.assertEqual(
            self.company_data["default_account_receivable"]
            .with_context(working_file_id=self.audit_2025.id)
            .audit_balance,
            50,
        )
        self.assertEqual(
            self.company_data["default_account_receivable"]
            .with_context(working_file_id=self.audit_2025.id)
            .audit_previous_balance,
            20,
        )

        self.assertEqual(
            self.company_data["default_account_revenue"]
            .with_context(working_file_id=self.audit_2024.id)
            .audit_balance,
            -20,
        )
        self.assertEqual(
            self.company_data["default_account_revenue"]
            .with_context(working_file_id=self.audit_2024.id)
            .audit_previous_balance,
            0,
        )

        self.assertEqual(
            self.company_data["default_account_revenue"]
            .with_context(working_file_id=self.audit_2025.id)
            .audit_balance,
            -30,
        )
        self.assertEqual(
            self.company_data["default_account_revenue"]
            .with_context(working_file_id=self.audit_2025.id)
            .audit_previous_balance,
            -20,
        )

        self.init_invoice(
            "out_invoice", amounts=[10], post=True, invoice_date="2023-02-01"
        )

    def test_state_progression(self):
        return_types = [
            self.env["account.return.type"].create(
                [
                    {
                        "category": "account_return",
                        "default_deadline_periodicity": "monthly",
                        "default_deadline_start_date": "2024-01-01",
                        "name": name,
                        "report_id": self.env.ref("account.generic_tax_report").id,
                        "states_workflow": states_workflow,
                    }
                ]
            )
            for name, states_workflow in [
                ("Only Pay", "generic_state_only_pay"),
                ("Only Review", "generic_state_review"),
                ("Review and Submit", "generic_state_review_submit"),
                ("Review, Submit and Pay", "generic_state_tax_report"),
            ]
        ]

        audit_return_type = self.env["account.return.type"].create(
            [
                {
                    "category": "audit",
                    "default_deadline_periodicity": "monthly",
                    "default_deadline_start_date": "2024-01-01",
                    "name": "Audit",
                }
            ]
        )

        for return_type in return_types + [audit_return_type]:
            with self.subTest(return_type=return_type):
                account_return = return_type.with_context(
                    forced_date_from=fields.Date.from_string("2024-01-01"),
                    forced_date_to=fields.Date.from_string("2024-01-31"),
                )._try_create_returns_for_fiscal_year(self.env.company, False)
                self.assertEqual(account_return.state, "new")
                self.assertEqual(account_return.is_completed, False)

                if return_type.states_workflow in (
                    "generic_state_review",
                    "generic_state_review_submit",
                ):
                    with self._patch_generate_locking_attachments():
                        account_return.action_validate()
                    self.assertEqual(account_return.state, "reviewed")

                if return_type.states_workflow == "generic_state_review":
                    self.assertEqual(account_return.is_completed, True)
                    continue
                self.assertEqual(account_return.is_completed, False)

                if return_type.states_workflow in (
                    "generic_state_review_submit",
                    "generic_state_tax_report",
                ):
                    account_return.action_submit()
                    if return_type.states_workflow == "generic_state_tax_report":
                        # no submitted step for generic_state_tax_report as there's nothing to pay
                        # (see test_account_return_state_review_submit_pay for a case with something to pay)
                        self.assertEqual(account_return.state, "paid")
                    else:
                        self.assertEqual(account_return.state, "submitted")

                if return_type.states_workflow in (
                    "generic_state_review_submit",
                    "generic_state_tax_report",
                ):
                    self.assertEqual(account_return.is_completed, True)
                    continue
                self.assertEqual(account_return.is_completed, False)

                payment_wizard_info = account_return.action_pay()
                payment_wizard = self.env[payment_wizard_info["res_model"]].browse(
                    payment_wizard_info["res_id"]
                )
                payment_wizard.action_mark_as_paid()
                self.assertEqual(account_return.state, "paid")
                self.assertEqual(account_return.is_completed, True)

    def test_account_return_state_review_submit_pay(self):
        review_submit_pay_return_type = self.env["account.return.type"].create(
            [
                {
                    "category": "account_return",
                    "default_deadline_periodicity": "monthly",
                    "default_deadline_start_date": "2024-01-01",
                    "name": "Only Pay",
                    "report_id": self.env.ref("account.generic_tax_report").id,
                    "states_workflow": "generic_state_tax_report",
                }
            ]
        )

        review_submit_pay_return = review_submit_pay_return_type.with_context(
            forced_date_from=fields.Date.from_string("2024-02-01"),
            forced_date_to=fields.Date.from_string("2024-02-29"),
        )._try_create_returns_for_fiscal_year(self.env.company, False)
        self.assertEqual(review_submit_pay_return.state, "new")

        tax_account = self.env["account.account"].create(
            {
                "name": "Tax Account",
                "code": "test.tax.account",
                "account_type": "liability_current",
            }
        )
        sale_tax = self.env["account.tax"].create(
            {
                "name": "sale tax",
                "amount": 21,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "company_ids": [Command.set(self.env.company.ids)],
                "invoice_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": tax_account.id,
                        }
                    ),
                ],
                "refund_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": tax_account.id,
                        }
                    ),
                ],
            }
        )
        self.init_invoice(
            "out_invoice",
            amounts=[320],
            invoice_date="2024-02-10",
            taxes=[sale_tax],
            post=True,
        )

        with self._patch_generate_locking_attachments():
            review_submit_pay_return.action_validate()
        self.assertEqual(review_submit_pay_return.state, "reviewed")
        self.assertEqual(review_submit_pay_return.is_completed, False)

        payment_wizard_info = review_submit_pay_return.action_submit()
        self.assertEqual(review_submit_pay_return.state, "submitted")
        self.assertEqual(review_submit_pay_return.is_completed, False)

        payment_wizard = self.env[payment_wizard_info["res_model"]].browse(
            payment_wizard_info["res_id"]
        )
        payment_wizard.action_mark_as_paid()
        self.assertEqual(review_submit_pay_return.state, "paid")
        self.assertEqual(review_submit_pay_return.is_completed, True)

    def test_deadline_by_company(self):
        with self._patch_returns_generation():
            self.company_data_2["company"].account_opening_date = "2023-01-01"

        first_company_completed_return = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.company_data["company"].id),
                ("date_from", "=", "2024-01-01"),
            ]
        )
        second_company_completed_return = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.company_data_2["company"].id),
                ("date_from", "=", "2024-01-01"),
            ]
        )

        first_company_completed_return._mark_completed()
        second_company_completed_return._mark_completed()

        first_company_return = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.company_data["company"].id),
                ("date_from", "=", "2024-02-01"),
            ]
        )
        second_company_return = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.company_data_2["company"].id),
                ("date_from", "=", "2024-02-01"),
            ]
        )

        self.assertEqual(first_company_completed_return.date_deadline, date(2024, 2, 7))
        self.assertEqual(
            second_company_completed_return.date_deadline, date(2024, 2, 7)
        )
        self.assertEqual(first_company_return.date_deadline, date(2024, 3, 7))
        self.assertEqual(second_company_return.date_deadline, date(2024, 3, 7))

        self.basic_return_type.with_company(
            self.company_data["company"]
        ).deadline_days_delay = 10
        self.assertEqual(first_company_completed_return.date_deadline, date(2024, 2, 7))
        self.assertEqual(
            second_company_completed_return.date_deadline, date(2024, 2, 7)
        )
        self.assertEqual(first_company_return.date_deadline, date(2024, 3, 10))
        self.assertEqual(second_company_return.date_deadline, date(2024, 3, 7))

        self.basic_return_type.with_company(
            self.company_data_2["company"]
        ).deadline_days_delay = 15
        self.assertEqual(first_company_completed_return.date_deadline, date(2024, 2, 7))
        self.assertEqual(
            second_company_completed_return.date_deadline, date(2024, 2, 7)
        )
        self.assertEqual(first_company_return.date_deadline, date(2024, 3, 10))
        self.assertEqual(second_company_return.date_deadline, date(2024, 3, 15))

    def test_annual_corporate_tax_return_exception_case(self):
        """Annual corporate tax return generation for an extended fiscal year: when the
        fiscal year is longer than 12 months (spanning two calendar years here), the
        return dates must match the fiscal year boundaries.
        """
        self.env["account.fiscal.year"].create(
            {
                "name": "Custom FY",
                "date_from": date(2022, 9, 1),
                "date_to": date(2023, 12, 31),
            }
        )

        annual_corporate_tax_return = self.env.ref(
            "account.annual_corporate_tax_return_type"
        )
        with freeze_time(date(2023, 12, 1)):
            # Generating the return later to be sure that we are in the acceptable time range of year or year + 1.
            annual_corporate_tax_return._try_create_returns_for_fiscal_year(
                self.env.company, None
            )
        existing_return = self.env["account.return"].search(
            [
                ("type_id", "=", annual_corporate_tax_return.id),
                ("company_id", "=", self.env.company.id),
            ]
        )

        self.assert_return_dates_equal(existing_return, [("2022-09-01", "2023-12-31")])

    def test_tax_return_with_shared_accounts(self):
        """
        Test that creating an audit including a shared account will not raise an AccessError in case
        the account is used by the other company in the audit period.
        """

        company_1 = self.company_data["company"]
        company_2 = self.company_data_2["company"]
        account_revenue = self.company_data["default_account_revenue"]

        # Sharing account
        self.company_data["default_account_revenue"].write(
            {
                "code_mapping_ids": [
                    Command.create({"company_id": company_1.id, "code": "180021"}),
                    Command.create({"company_id": company_2.id, "code": "180022"}),
                ],
                "company_ids": [Command.set([company_1.id, company_2.id])],
            }
        )

        audit_2024_company_1 = self.audit_2024
        audit_2024_company_2 = self.audit_return_type.with_context(
            forced_date_from=fields.Date.from_string("2024-01-01"),
            forced_date_to=fields.Date.from_string("2024-12-31"),
        )._try_create_returns_for_fiscal_year(company_2, False)

        # Set the account audit status to 'reviewed'. An audit status is scoped to the
        # companies of the audit that owns it, so reaching company 2's row needs an
        # environment that allows company 2.
        both_companies = account_revenue.with_context(
            allowed_company_ids=(company_1 + company_2).ids
        )
        account_status = both_companies.account_status.filtered(
            lambda status: (
                status.audit_id in (audit_2024_company_1, audit_2024_company_2)
            )
        )
        self.assertEqual(len(account_status), 2, "one audit status per company")
        account_status.status = "reviewed"

        # ... and company 1 on its own must not see company 2's. The cache has to go
        # first: a restricted environment reads what a wider one already fetched, so
        # without this the record rule is never consulted and the check always passes.
        self.env.invalidate_all()
        self.assertFalse(
            self.env["account.audit.account.status"]
            .with_context(allowed_company_ids=company_1.ids)
            .search_count(
                [
                    ("id", "in", account_status.ids),
                    ("audit_id", "=", audit_2024_company_2.id),
                ]
            ),
            "an audit status must not be visible from a company the audit excludes",
        )
        self.env.invalidate_all()

        # With company 2, create a move in the audit period
        company_2_move = (
            self.env["account.move"]
            .with_company(company_2)
            .create(
                {
                    "move_type": "entry",
                    "date": "2024-01-02",
                    "company_id": company_2.id,
                    "line_ids": [
                        Command.create(
                            {
                                "name": "revenue_line",
                                "account_id": account_revenue.id,
                                "debit": 500.0,
                                "credit": 0.0,
                            }
                        ),
                        Command.create(
                            {
                                "name": "counterpart line",
                                "account_id": self.company_data_2[
                                    "default_account_expense"
                                ].id,
                                "debit": 0.0,
                                "credit": 500.0,
                            }
                        ),
                    ],
                }
            )
        )

        # Should be able to post the move without issues
        company_2_move.action_post()
        self.assertEqual(
            account_status.filtered(
                lambda a: a.audit_id.company_id == company_1
            ).status,
            "reviewed",
            "Audit status in company 1 should be unchanged",
        )
        self.assertEqual(
            account_status.filtered(
                lambda a: a.audit_id.company_id == company_2
            ).status,
            "todo",
            "Audit status in company 2 should reset to default",
        )

    def test_vies_validation_fiscal_position_vat_required(self):
        """Test that vies validation is performed only for moves with fiscal position with vat required"""

        def _check_vies(record, vat):
            return {"valid": vat == "ESA12345674"}

        # needed to have the 'check_partner_vies'
        self.ensure_installed("account_vat")
        self.basic_tax_report.country_id = self.env.ref("base.be")
        self.env.company.vat_check_vies = True

        partner = self.partner_a.copy({"country_id": self.env.ref("base.es").id})
        fp_vat_required = self.env["account.fiscal.position"].create(
            {
                "name": "fp vat required",
                "vat_required": True,
            }
        )

        january_return = self.env["account.return"].search(
            [
                ("type_id", "=", self.basic_return_type.id),
                ("company_id", "=", self.env.company.id),
                ("date_from", "=", "2024-01-01"),
                ("date_to", "=", "2024-01-31"),
            ]
        )

        self.assertEqual(
            len(january_return), 1, "There should be one return for January 2024"
        )

        invoice = self._create_invoice(
            "in_invoice", partner_id=partner, invoice_date="2024-01-01", post=True
        )

        data_list = [
            {"partner_vals": {"vat": False}, "expected_check": ["reviewed", "anomaly"]},
            {
                "partner_vals": {"vat": "ESA12345674"},
                "expected_check": ["reviewed", "reviewed"],
            },
            {
                "partner_vals": {"vat": "ESA12345678"},
                "expected_check": ["reviewed", "anomaly"],
            },
        ]

        for with_fp, data in product((False, True), data_list):
            with self.subTest(with_fp=with_fp, vat=data["partner_vals"]["vat"]):
                if bool(invoice.fiscal_position_id) ^ with_fp:
                    invoice.action_draft()
                    invoice.fiscal_position_id = (
                        False if not with_fp else fp_vat_required
                    )
                    invoice.action_post()

                partner.with_context(no_vat_validation=True).write(data["partner_vals"])
                with patch(
                    "odoo.addons.account_vat.models.res_partner.ResPartner._check_vies",
                    _check_vies,
                ):
                    january_return.refresh_checks()

                self.assert_return_contains_checks(
                    january_return,
                    ["check_partner_vies"],
                )

                vies_check = january_return.check_ids.filtered(
                    lambda c: c.code == "check_partner_vies"
                )
                self.assertEqual(vies_check.result, data["expected_check"][with_fp])
