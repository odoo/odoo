# Author: Julien Coux
# Copyright 2016 Camptocamp SA
# Copyright 2020 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import time
from datetime import date

from odoo import api, fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestGeneralLedgerReport(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                mail_create_nolog=True,
                mail_create_nosubscribe=True,
                mail_notrack=True,
                no_reset_password=True,
                tracking_disable=True,
            )
        )
        cls.before_previous_fy_year = fields.Date.from_string("2014-05-05")
        cls.previous_fy_date_start = fields.Date.from_string("2015-01-01")
        cls.previous_fy_date_end = fields.Date.from_string("2015-12-31")
        cls.fy_date_start = fields.Date.from_string("2016-01-01")
        cls.fy_date_end = fields.Date.from_string("2016-12-31")
        # Get accounts
        cls.receivable_account = cls.company_data["default_account_receivable"]
        cls.income_account = cls.company_data["default_account_revenue"]
        cls.unaffected_account = cls.env["account.account"].search(
            [
                (
                    "account_type",
                    "=",
                    "equity_unaffected",
                ),
                ("company_ids", "in", [cls.env.user.company_id.id]),
            ],
            limit=1,
        )
        cls.partner = cls.env.ref("base.res_partner_12")

    def _add_move(
        self,
        date,
        receivable_debit,
        receivable_credit,
        income_debit,
        income_credit,
        unaffected_debit=0,
        unaffected_credit=0,
    ):
        journal = self.env["account.journal"].search(
            [("company_id", "=", self.env.user.company_id.id)], limit=1
        )
        partner = self.env.ref("base.res_partner_12")
        move_vals = {
            "journal_id": journal.id,
            "date": date,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "debit": receivable_debit,
                        "credit": receivable_credit,
                        "account_id": self.receivable_account.id,
                        "partner_id": partner.id,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "debit": income_debit,
                        "credit": income_credit,
                        "account_id": self.income_account.id,
                        "partner_id": partner.id,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "debit": unaffected_debit,
                        "credit": unaffected_credit,
                        "account_id": self.unaffected_account.id,
                        "partner_id": partner.id,
                    },
                ),
            ],
        }
        move = self.env["account.move"].create(move_vals)
        move.action_post()

    def _get_report_lines(self, with_partners=False, account_ids=False):
        centralize = True
        if with_partners:
            centralize = False
        company = self.env.user.company_id
        general_ledger = self.env["general.ledger.report.wizard"].create(
            {
                "date_from": self.fy_date_start,
                "date_to": self.fy_date_end,
                "target_move": "posted",
                "hide_account_at_0": False,
                "company_id": company.id,
                "account_ids": account_ids,
                "fy_start_date": self.fy_date_start,
                "centralize": centralize,
            }
        )
        data = general_ledger._prepare_report_general_ledger()
        res_data = self.env[
            "report.account_financial_report.general_ledger"
        ]._get_report_values(general_ledger, data)
        return res_data

    @api.model
    def check_account_in_report(self, account_id, general_ledger):
        account_in_report = False
        for account in general_ledger:
            if account["id"] == account_id:
                account_in_report = True
                break
        return account_in_report

    @api.model
    def check_partner_in_report(self, account_id, partner_id, general_ledger):
        partner_in_report = False
        for account in general_ledger:
            if account["id"] == account_id and account["partners"]:
                for partner in account["list_grouped"]:
                    if partner["id"] == partner_id:
                        partner_in_report = True
        return partner_in_report

    @api.model
    def _get_initial_balance(self, account_id, general_ledger):
        initial_balance = False
        for account in general_ledger:
            if account["id"] == account_id:
                initial_balance = account["init_bal"]
        return initial_balance

    @api.model
    def _get_partner_initial_balance(self, account_id, partner_id, general_ledger):
        initial_balance = False
        for account in general_ledger:
            if account["id"] == account_id and account["partners"]:
                for partner in account["list_grouped"]:
                    if partner["id"] == partner_id:
                        initial_balance = partner["init_bal"]
        return initial_balance

    @api.model
    def _get_final_balance(self, account_id, general_ledger):
        final_balance = False
        for account in general_ledger:
            if account["id"] == account_id:
                final_balance = account["fin_bal"]
        return final_balance

    @api.model
    def _get_partner_final_balance(self, account_id, partner_id, general_ledger):
        final_balance = False
        for account in general_ledger:
            if account["id"] == account_id and account["partners"]:
                for partner in account["list_grouped"]:
                    if partner["id"] == partner_id:
                        final_balance = partner["fin_bal"]
        return final_balance

    def test_01_account_balance(self):
        # Generate the general ledger line
        res_data = self._get_report_lines()
        general_ledger = res_data["general_ledger"]
        check_receivable_account = self.check_account_in_report(
            self.receivable_account.id, general_ledger
        )
        self.assertFalse(check_receivable_account)
        check_income_account = self.check_account_in_report(
            self.income_account.id, general_ledger
        )
        self.assertFalse(check_income_account)
        self.assertTrue(
            self.check_account_in_report(self.unaffected_account.id, general_ledger)
        )

        # Add a move at the previous day of the first day of fiscal year
        # to check the initial balance
        self._add_move(
            date=self.previous_fy_date_end,
            receivable_debit=1000,
            receivable_credit=0,
            income_debit=0,
            income_credit=1000,
        )

        # Re Generate the general ledger line
        res_data = self._get_report_lines()
        general_ledger = res_data["general_ledger"]
        check_receivable_account = self.check_account_in_report(
            self.receivable_account.id, general_ledger
        )
        self.assertTrue(check_receivable_account)
        check_income_account = self.check_account_in_report(
            self.income_account.id, general_ledger
        )
        self.assertFalse(check_income_account)

        # Check the initial and final balance
        receivable_init_balance = self._get_initial_balance(
            self.receivable_account.id, general_ledger
        )
        receivable_fin_balance = self._get_final_balance(
            self.receivable_account.id, general_ledger
        )

        self.assertEqual(receivable_init_balance["debit"], 1000)
        self.assertEqual(receivable_init_balance["credit"], 0)
        self.assertEqual(receivable_init_balance["balance"], 1000)
        self.assertEqual(receivable_fin_balance["debit"], 1000)
        self.assertEqual(receivable_fin_balance["credit"], 0)
        self.assertEqual(receivable_fin_balance["balance"], 1000)

        # Add reversale move of the initial move the first day of fiscal year
        # to check the first day of fiscal year is not used
        # to compute the initial balance
        self._add_move(
            date=self.fy_date_start,
            receivable_debit=0,
            receivable_credit=1000,
            income_debit=1000,
            income_credit=0,
        )

        # Re Generate the general ledger line
        res_data = self._get_report_lines()
        general_ledger = res_data["general_ledger"]
        check_receivable_account = self.check_account_in_report(
            self.receivable_account.id, general_ledger
        )
        self.assertTrue(check_receivable_account)
        check_income_account = self.check_account_in_report(
            self.income_account.id, general_ledger
        )
        self.assertTrue(check_income_account)

        # Check the initial and final balance
        receivable_init_balance = self._get_initial_balance(
            self.receivable_account.id, general_ledger
        )
        receivable_fin_balance = self._get_final_balance(
            self.receivable_account.id, general_ledger
        )
        income_init_balance = self._get_initial_balance(
            self.income_account.id, general_ledger
        )
        income_fin_balance = self._get_final_balance(
            self.income_account.id, general_ledger
        )

        self.assertEqual(receivable_init_balance["debit"], 1000)
        self.assertEqual(receivable_init_balance["credit"], 0)
        self.assertEqual(receivable_init_balance["balance"], 1000)
        self.assertEqual(receivable_fin_balance["debit"], 1000)
        self.assertEqual(receivable_fin_balance["credit"], 1000)
        self.assertEqual(receivable_fin_balance["balance"], 0)

        self.assertEqual(income_init_balance["debit"], 0)
        self.assertEqual(income_init_balance["credit"], 0)
        self.assertEqual(income_init_balance["balance"], 0)
        self.assertEqual(income_fin_balance["debit"], 1000)
        self.assertEqual(income_fin_balance["credit"], 0)
        self.assertEqual(income_fin_balance["balance"], 1000)

        # Re Generate the general ledger line
        res_data = self._get_report_lines(
            account_ids=(self.receivable_account + self.income_account).ids
        )
        general_ledger = res_data["general_ledger"]
        self.assertTrue(
            self.check_account_in_report(self.receivable_account.id, general_ledger)
        )
        self.assertTrue(
            self.check_account_in_report(self.income_account.id, general_ledger)
        )
        self.assertFalse(
            self.check_account_in_report(self.unaffected_account.id, general_ledger)
        )

        # Add another move at the end day of fiscal year
        # to check that it correctly used on report
        self._add_move(
            date=self.fy_date_end,
            receivable_debit=0,
            receivable_credit=1000,
            income_debit=1000,
            income_credit=0,
        )

        # Re Generate the general ledger line
        res_data = self._get_report_lines()
        general_ledger = res_data["general_ledger"]
        check_receivable_account = self.check_account_in_report(
            self.receivable_account.id, general_ledger
        )
        self.assertTrue(check_receivable_account)
        check_income_account = self.check_account_in_report(
            self.income_account.id, general_ledger
        )
        self.assertTrue(check_income_account)

        # Check the initial and final balance
        receivable_init_balance = self._get_initial_balance(
            self.receivable_account.id, general_ledger
        )
        receivable_fin_balance = self._get_final_balance(
            self.receivable_account.id, general_ledger
        )
        income_init_balance = self._get_initial_balance(
            self.income_account.id, general_ledger
        )
        income_fin_balance = self._get_final_balance(
            self.income_account.id, general_ledger
        )

        self.assertEqual(receivable_init_balance["debit"], 1000)
        self.assertEqual(receivable_init_balance["credit"], 0)
        self.assertEqual(receivable_init_balance["balance"], 1000)
        self.assertEqual(receivable_fin_balance["debit"], 1000)
        self.assertEqual(receivable_fin_balance["credit"], 2000)
        self.assertEqual(receivable_fin_balance["balance"], -1000)

        self.assertEqual(income_init_balance["debit"], 0)
        self.assertEqual(income_init_balance["credit"], 0)
        self.assertEqual(income_init_balance["balance"], 0)
        self.assertEqual(income_fin_balance["debit"], 2000)
        self.assertEqual(income_fin_balance["credit"], 0)
        self.assertEqual(income_fin_balance["balance"], 2000)

    def test_02_partner_balance(self):
        # Generate the general ledger line
        res_data = self._get_report_lines(with_partners=True)
        general_ledger = res_data["general_ledger"]
        check_partner = self.check_partner_in_report(
            self.receivable_account.id, self.partner.id, general_ledger
        )
        self.assertFalse(check_partner)

        # Add a move at the previous day of the first day of fiscal year
        # to check the initial balance
        self._add_move(
            date=self.previous_fy_date_end,
            receivable_debit=1000,
            receivable_credit=0,
            income_debit=0,
            income_credit=1000,
        )

        # Re Generate the general ledger line
        res_data = self._get_report_lines(with_partners=True)
        general_ledger = res_data["general_ledger"]
        check_partner = self.check_partner_in_report(
            self.receivable_account.id, self.partner.id, general_ledger
        )
        self.assertTrue(check_partner)

        # Check the initial and final balance
        partner_initial_balance = self._get_partner_initial_balance(
            self.receivable_account.id, self.partner.id, general_ledger
        )
        partner_final_balance = self._get_partner_final_balance(
            self.receivable_account.id, self.partner.id, general_ledger
        )

        self.assertEqual(partner_initial_balance["debit"], 1000)
        self.assertEqual(partner_initial_balance["credit"], 0)
        self.assertEqual(partner_initial_balance["balance"], 1000)
        self.assertEqual(partner_final_balance["debit"], 1000)
        self.assertEqual(partner_final_balance["credit"], 0)
        self.assertEqual(partner_final_balance["balance"], 1000)

        # Add reversale move of the initial move the first day of fiscal year
        # to check the first day of fiscal year is not used
        # to compute the initial balance
        self._add_move(
            date=self.fy_date_start,
            receivable_debit=0,
            receivable_credit=1000,
            income_debit=1000,
            income_credit=0,
        )

        # Re Generate the general ledger line
        res_data = self._get_report_lines(with_partners=True)
        general_ledger = res_data["general_ledger"]
        check_partner = self.check_partner_in_report(
            self.receivable_account.id, self.partner.id, general_ledger
        )
        self.assertTrue(check_partner)

        # Check the initial and final balance
        partner_initial_balance = self._get_partner_initial_balance(
            self.receivable_account.id, self.partner.id, general_ledger
        )
        partner_final_balance = self._get_partner_final_balance(
            self.receivable_account.id, self.partner.id, general_ledger
        )

        self.assertEqual(partner_initial_balance["debit"], 1000)
        self.assertEqual(partner_initial_balance["credit"], 0)
        self.assertEqual(partner_initial_balance["balance"], 1000)
        self.assertEqual(partner_final_balance["debit"], 1000)
        self.assertEqual(partner_final_balance["credit"], 1000)
        self.assertEqual(partner_final_balance["balance"], 0)

        # Add another move at the end day of fiscal year
        # to check that it correctly used on report
        self._add_move(
            date=self.fy_date_end,
            receivable_debit=0,
            receivable_credit=1000,
            income_debit=1000,
            income_credit=0,
        )

        # Re Generate the general ledger line
        res_data = self._get_report_lines(with_partners=True)
        general_ledger = res_data["general_ledger"]
        check_partner = self.check_partner_in_report(
            self.receivable_account.id, self.partner.id, general_ledger
        )
        self.assertTrue(check_partner)

        # Check the initial and final balance
        partner_initial_balance = self._get_partner_initial_balance(
            self.receivable_account.id, self.partner.id, general_ledger
        )
        partner_final_balance = self._get_partner_final_balance(
            self.receivable_account.id, self.partner.id, general_ledger
        )

        self.assertEqual(partner_initial_balance["debit"], 1000)
        self.assertEqual(partner_initial_balance["credit"], 0)
        self.assertEqual(partner_initial_balance["balance"], 1000)
        self.assertEqual(partner_final_balance["debit"], 1000)
        self.assertEqual(partner_final_balance["credit"], 2000)
        self.assertEqual(partner_final_balance["balance"], -1000)

    def test_03_unaffected_account_balance(self):
        # Generate the general ledger line
        res_data = self._get_report_lines()
        general_ledger = res_data["general_ledger"]
        check_unaffected_account = self.check_account_in_report(
            self.unaffected_account.id, general_ledger
        )
        self.assertTrue(check_unaffected_account)

        # Check the initial and final balance
        unaffected_init_balance = self._get_initial_balance(
            self.unaffected_account.id, general_ledger
        )
        unaffected_fin_balance = self._get_final_balance(
            self.unaffected_account.id, general_ledger
        )

        self.assertEqual(unaffected_init_balance["debit"], 0)
        self.assertEqual(unaffected_init_balance["credit"], 0)
        self.assertEqual(unaffected_init_balance["balance"], 0)
        self.assertEqual(unaffected_fin_balance["debit"], 0)
        self.assertEqual(unaffected_fin_balance["credit"], 0)
        self.assertEqual(unaffected_fin_balance["balance"], 0)

        # Add a move at the previous day of the first day of fiscal year
        # to check the initial balance
        self._add_move(
            date=self.previous_fy_date_end,
            receivable_debit=1000,
            receivable_credit=0,
            income_debit=0,
            income_credit=1000,
        )

        # Re Generate the general ledger line
        res_data = self._get_report_lines()
        general_ledger = res_data["general_ledger"]
        check_unaffected_account = self.check_account_in_report(
            self.unaffected_account.id, general_ledger
        )
        self.assertTrue(check_unaffected_account)

        # Check the initial and final balance
        unaffected_init_balance = self._get_initial_balance(
            self.unaffected_account.id, general_ledger
        )
        unaffected_fin_balance = self._get_final_balance(
            self.unaffected_account.id, general_ledger
        )

        self.assertEqual(unaffected_init_balance["debit"], 0)
        self.assertEqual(unaffected_init_balance["credit"], 1000)
        self.assertEqual(unaffected_init_balance["balance"], -1000)
        self.assertEqual(unaffected_fin_balance["debit"], 0)
        self.assertEqual(unaffected_fin_balance["credit"], 1000)
        self.assertEqual(unaffected_fin_balance["balance"], -1000)

        # Add reversale move of the initial move the first day of fiscal year
        # to check the first day of fiscal year is not used
        # to compute the initial balance
        self._add_move(
            date=self.fy_date_start,
            receivable_debit=0,
            receivable_credit=0,
            income_debit=0,
            income_credit=1000,
            unaffected_debit=1000,
            unaffected_credit=0,
        )

        # Re Generate the general ledger line
        res_data = self._get_report_lines()
        general_ledger = res_data["general_ledger"]
        check_unaffected_account = self.check_account_in_report(
            self.unaffected_account.id, general_ledger
        )
        self.assertTrue(check_unaffected_account)

        # Check the initial and final balance
        unaffected_init_balance = self._get_initial_balance(
            self.unaffected_account.id, general_ledger
        )
        unaffected_fin_balance = self._get_final_balance(
            self.unaffected_account.id, general_ledger
        )

        self.assertEqual(unaffected_init_balance["debit"], 0)
        self.assertEqual(unaffected_init_balance["credit"], 1000)
        self.assertEqual(unaffected_init_balance["balance"], -1000)
        self.assertEqual(unaffected_fin_balance["debit"], 1000)
        self.assertEqual(unaffected_fin_balance["credit"], 1000)
        self.assertEqual(unaffected_fin_balance["balance"], 0)

        # Add another move at the end day of fiscal year
        # to check that it correctly used on report
        self._add_move(
            date=self.fy_date_end,
            receivable_debit=3000,
            receivable_credit=0,
            income_debit=0,
            income_credit=0,
            unaffected_debit=0,
            unaffected_credit=3000,
        )

        # Re Generate the general ledger line
        res_data = self._get_report_lines()
        general_ledger = res_data["general_ledger"]
        check_unaffected_account = self.check_account_in_report(
            self.unaffected_account.id, general_ledger
        )
        self.assertTrue(check_unaffected_account)

        # Check the initial and final balance
        unaffected_init_balance = self._get_initial_balance(
            self.unaffected_account.id, general_ledger
        )
        unaffected_fin_balance = self._get_final_balance(
            self.unaffected_account.id, general_ledger
        )

        self.assertEqual(unaffected_init_balance["debit"], 0)
        self.assertEqual(unaffected_init_balance["credit"], 1000)
        self.assertEqual(unaffected_init_balance["balance"], -1000)
        self.assertEqual(unaffected_fin_balance["debit"], 1000)
        self.assertEqual(unaffected_fin_balance["credit"], 4000)
        self.assertEqual(unaffected_fin_balance["balance"], -3000)

    def test_04_unaffected_account_balance_2_years(self):
        # Generate the general ledger line
        res_data = self._get_report_lines()
        general_ledger = res_data["general_ledger"]
        check_unaffected_account = self.check_account_in_report(
            self.unaffected_account.id, general_ledger
        )
        self.assertTrue(check_unaffected_account)

        # Check the initial and final balance
        unaffected_init_balance = self._get_initial_balance(
            self.unaffected_account.id, general_ledger
        )
        unaffected_fin_balance = self._get_final_balance(
            self.unaffected_account.id, general_ledger
        )

        self.assertEqual(unaffected_init_balance["debit"], 0)
        self.assertEqual(unaffected_init_balance["credit"], 0)
        self.assertEqual(unaffected_init_balance["balance"], 0)
        self.assertEqual(unaffected_fin_balance["debit"], 0)
        self.assertEqual(unaffected_fin_balance["credit"], 0)
        self.assertEqual(unaffected_fin_balance["balance"], 0)

        # Add a move at any date 2 years before the balance
        # (to create an historic)
        self._add_move(
            date=self.before_previous_fy_year,
            receivable_debit=0,
            receivable_credit=1000,
            income_debit=1000,
            income_credit=0,
        )

        # Re Generate the general ledger line
        res_data = self._get_report_lines()
        general_ledger = res_data["general_ledger"]
        check_unaffected_account = self.check_account_in_report(
            self.unaffected_account.id, general_ledger
        )
        self.assertTrue(check_unaffected_account)

        # Check the initial and final balance
        unaffected_init_balance = self._get_initial_balance(
            self.unaffected_account.id, general_ledger
        )
        unaffected_fin_balance = self._get_final_balance(
            self.unaffected_account.id, general_ledger
        )

        self.assertEqual(unaffected_init_balance["debit"], 1000)
        self.assertEqual(unaffected_init_balance["credit"], 0)
        self.assertEqual(unaffected_init_balance["balance"], 1000)
        self.assertEqual(unaffected_fin_balance["debit"], 1000)
        self.assertEqual(unaffected_fin_balance["credit"], 0)
        self.assertEqual(unaffected_fin_balance["balance"], 1000)

        # Affect the company's result last year
        self._add_move(
            date=self.previous_fy_date_start,
            receivable_debit=1000,
            receivable_credit=0,
            income_debit=0,
            income_credit=0,
            unaffected_debit=0,
            unaffected_credit=1000,
        )

        # Add another move last year to test the initial balance this year
        self._add_move(
            date=self.previous_fy_date_start,
            receivable_debit=0,
            receivable_credit=500,
            income_debit=500,
            income_credit=0,
            unaffected_debit=0,
            unaffected_credit=0,
        )

        # Re Generate the general ledger line
        res_data = self._get_report_lines()
        general_ledger = res_data["general_ledger"]
        check_unaffected_account = self.check_account_in_report(
            self.unaffected_account.id, general_ledger
        )
        self.assertTrue(check_unaffected_account)

        # Check the initial and final balance
        unaffected_init_balance = self._get_initial_balance(
            self.unaffected_account.id, general_ledger
        )
        unaffected_fin_balance = self._get_final_balance(
            self.unaffected_account.id, general_ledger
        )

        self.assertEqual(unaffected_init_balance["debit"], 1500)
        self.assertEqual(unaffected_init_balance["credit"], 1000)
        self.assertEqual(unaffected_init_balance["balance"], 500)
        self.assertEqual(unaffected_fin_balance["debit"], 1500)
        self.assertEqual(unaffected_fin_balance["credit"], 1000)
        self.assertEqual(unaffected_fin_balance["balance"], 500)

    def test_partner_filter(self):
        partner_1 = self.env.ref("base.res_partner_1")
        partner_2 = self.env.ref("base.res_partner_2")
        partner_3 = self.env.ref("base.res_partner_3")
        partner_4 = self.env.ref("base.res_partner_4")
        partner_1.write({"is_company": False, "parent_id": partner_2.id})
        partner_3.write({"is_company": False})

        expected_list = [partner_2.id, partner_3.id, partner_4.id]
        context = {
            "active_ids": [partner_1.id, partner_2.id, partner_3.id, partner_4.id],
            "active_model": "res.partner",
        }

        wizard = self.env["general.ledger.report.wizard"].with_context(**context)
        self.assertEqual(wizard._default_partners(), expected_list)

    def test_validate_date(self):
        company_id = self.env.user.company_id
        company_id.write({"fiscalyear_last_day": 31, "fiscalyear_last_month": "12"})
        user = self.env.ref("base.user_root").with_context(company_id=company_id.id)
        wizard = self.env["general.ledger.report.wizard"].with_context(user=user.id)
        self.assertEqual(wizard._init_date_from(), time.strftime("%Y") + "-01-01")

    def test_validate_date_range(self):
        data_type = self.env["date.range.type"].create(
            {"name": "Fiscal year", "company_id": False, "allow_overlap": False}
        )

        dr = self.env["date.range"].create(
            {
                "name": "FS2015",
                "date_start": "2018-01-01",
                "date_end": "2018-12-31",
                "type_id": data_type.id,
            }
        )

        wizard = self.env["general.ledger.report.wizard"].create(
            {"date_range_id": dr.id}
        )
        wizard.onchange_date_range_id()
        self.assertEqual(wizard.date_from, date(2018, 1, 1))
        self.assertEqual(wizard.date_to, date(2018, 12, 31))
