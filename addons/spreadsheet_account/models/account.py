# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
import calendar
from dateutil.relativedelta import relativedelta

from odoo import models, api, _
from odoo.osv import expression
from odoo.tools import date_utils


class AccountMove(models.Model):
    _inherit = "account.account"

    @api.model
    def _get_date_period_boundaries(self, date_period, company):
        period_type = date_period["range_type"]
        year = date_period.get("year")
        month = date_period.get("month")
        quarter = date_period.get("quarter")
        day = date_period.get("day")
        if period_type == "year":
            fiscal_day = company.fiscalyear_last_day
            fiscal_month = int(company.fiscalyear_last_month)
            if not (fiscal_day == 31 and fiscal_month == 12):
                year += 1
            max_day = calendar.monthrange(year, fiscal_month)[1]
            current = date(year, fiscal_month, min(fiscal_day, max_day))
            start, end = date_utils.get_fiscal_year(current, fiscal_day, fiscal_month)
        elif period_type == "month":
            start = date(year, month, 1)
            end = start + relativedelta(months=1, days=-1)
        elif period_type == "quarter":
            first_month = quarter * 3 - 2
            start = date(year, first_month, 1)
            end = start + relativedelta(months=3, days=-1)
        elif period_type == "day":
            fiscal_day = company.fiscalyear_last_day
            fiscal_month = int(company.fiscalyear_last_month)
            end = date(year, month, day)
            start, _ = date_utils.get_fiscal_year(end, fiscal_day, fiscal_month)
        return start, end

    def _build_spreadsheet_formula_domain(self, formula_params):
        codes = [code for code in formula_params["codes"] if code]
        if not codes:
            return expression.FALSE_DOMAIN
        company_id = formula_params["company_id"] or self.env.company.id
        company = self.env["res.company"].browse(company_id)
        start, end = self._get_date_period_boundaries(
            formula_params["date_range"], company
        )
        balance_domain = [
            ("account_id.include_initial_balance", "=", True),
            ("date", "<=", end),
        ]
        pnl_domain = [
            ("account_id.include_initial_balance", "=", False),
            ("date", ">=", start),
            ("date", "<=", end),
        ]
        # It is more optimized to (like) search for code directly in account.account than in account_move_line
        code_domain = expression.OR(
            [
                ("code", "=like", f"{code}%"),
            ]
            for code in codes
        )
        account_ids = self.env["account.account"].with_company(company_id).search(code_domain).ids
        code_domain = [("account_id", "in", account_ids)]
        period_domain = expression.OR([balance_domain, pnl_domain])
        domain = expression.AND([code_domain, period_domain, [("company_id", "=", company_id)]])
        if formula_params["include_unposted"]:
            domain = expression.AND(
                [domain, [("move_id.state", "!=", "cancel")]]
            )
        else:
            domain = expression.AND(
                [domain, [("move_id.state", "=", "posted")]]
            )
        return domain

    @api.model
    def spreadsheet_move_line_action(self, args):
        domain = self._build_spreadsheet_formula_domain(args)
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move.line",
            "view_mode": "list",
            "views": [[False, "list"]],
            "target": "current",
            "domain": domain,
            "name": _("Journal items for account prefix %s", ", ".join(args["codes"])),
        }

    @api.model
    def spreadsheet_fetch_debit_credit(self, args_list):
        """Fetch data for ODOO.CREDIT, ODOO.DEBIT and ODOO.BALANCE formulas
        The input list looks like this:
        [{
            date_range: {
                range_type: "year"
                year: int
            },
            company_id: int
            codes: str[]
            include_unposted: bool
        }]
        """
        results = []
        for args in args_list:
            company_id = args["company_id"] or self.env.company.id
            domain = self._build_spreadsheet_formula_domain(args)
            # remove this when _search always returns a Query object
            if expression.is_false(self.env["account.move.line"], domain):
                results.append({"credit": 0, "debit": 0})
                continue
            MoveLines = self.env["account.move.line"].with_company(company_id)
            query = MoveLines._search(domain)
            query.order = None
            query_str, params = query.select(
                "SUM(debit) AS debit", "SUM(credit) AS credit"
            )
            self.env.cr.execute(query_str, params)
            line_values = self.env.cr.dictfetchone()
            results.append(
                {
                    "credit": line_values["credit"] or 0,
                    "debit": line_values["debit"] or 0,
                }
            )

        return results

    @api.model
    def get_account_group(self, account_types):
        data = self._read_group(
            [
                ("account_type", "in", account_types),
                ("company_id", "=", self.env.company.id),
            ],
            ["code:array_agg"],
            ["account_type"],
        )
        mapped = {group["account_type"]: group["code"] for group in data}
        return [mapped.get(account_type, []) for account_type in account_types]
