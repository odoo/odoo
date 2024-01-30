# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
import calendar
from dateutil.relativedelta import relativedelta
from collections import defaultdict

from odoo import models, api, _
from odoo.osv import expression
from odoo.tools import date_utils


class AccountMove(models.Model):
    _inherit = "account.account"

    # ------------------------ #
    # Domain utility functions #
    # ------------------------ #

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

        account_ids = self._search_accounts_with_codes_or_types(codes=codes).ids

        company_id = formula_params["company_id"] or self.env.company.id
        company = self.env["res.company"].browse(company_id)
        start, _end = self._get_date_period_boundaries(
            formula_params["date_from"], company
        )
        _start, end = self._get_date_period_boundaries(
            formula_params["date_to"], company
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

    def _search_accounts_with_codes_or_types(self, codes=[], types=[], extra_domains=[]):
        code_domain = expression.OR(
            [
                ("code", "=like", f"{code}%"),
            ]
            for code in codes
        )
        payable_receivable_domain = [('account_type', 'in', types)]
        domain = expression.AND([
            expression.OR([code_domain, payable_receivable_domain]),
            extra_domains,
        ])

        return self.env["account.account"].search(domain)

    def _get_accounts_and_lines_for_all_cells(self, args_list, extra_aggregates=[]):
        company_ids = tuple(args['company_id'] or self.env.company.id for args in args_list)
        account_codes = [
            code
            for args in args_list
            for code in args["codes"]
            if code
        ]

        all_accounts = self._search_accounts_with_codes_or_types(
            codes=account_codes,
            types=["liability_payable", "asset_receivable"],
            extra_domains=[('company_id', 'in', company_ids)]
        )

        domain = [
            ('company_id', 'in', company_ids),
            ('account_id', 'in', all_accounts.ids),
            ('parent_state', 'in', ('draft', 'posted')),
        ]

        all_lines = self.env['account.move.line']._read_group(
            domain=domain,
            groupby=['company_id', 'parent_state', 'account_id'],
            aggregates=['date:array_agg'] + extra_aggregates,
        )

        return all_accounts, all_lines

    # ------------------------ #
    #      API functions       #
    # ------------------------ #

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
            date_from: {
                range_type: "year"
                year: int
            },
            date_to: {
                range_type: "year"
                year: int
            },
            company_id: int
            codes: str[]
            include_unposted: bool
        }]
        """
        all_accounts, all_lines = self._get_accounts_and_lines_for_all_cells(
            args_list,
            extra_aggregates=['debit:array_agg', 'credit:array_agg']
        )

        lines_dict = defaultdict(
            lambda: (),
            {(company.id, state, account.id): tuple(val) for company, state, account, *val in all_lines}
        )

        results = []

        for args in args_list:
            subcodes = {subcode for subcode in args["codes"] if subcode}

            if not subcodes:
                results.append({'credit': 0, 'debit': 0})
                continue

            company_id = args['company_id'] or self.env.company.id
            company = self.env["res.company"].browse(company_id)
            states = ['posted', 'draft'] if args['include_unposted'] else ['posted']
            start, _end = self._get_date_period_boundaries(
                args['date_from'], company
            )
            _start, end = self._get_date_period_boundaries(
                args['date_to'], company
            )

            accounts = self.env['account.account']
            for subcode in subcodes:
                accounts += all_accounts.filtered(lambda acc: acc.code.startswith(subcode))

            cell_debit = 0.0
            cell_credit = 0.0
            for account in accounts:
                include_initial_balance = account.include_initial_balance
                for state in states:
                    for line_date, line_debit, line_credit in zip(*lines_dict[(company_id, state, account.id)]):
                        if (include_initial_balance and line_date > end) \
                           or (not include_initial_balance and (line_date < start or line_date > end)):
                            continue

                        cell_debit += line_debit
                        cell_credit += line_credit

            results.append({'debit': cell_debit or 0, 'credit': cell_credit or 0})
        return results

    @api.model
    def get_account_group(self, account_types):
        data = self._read_group(
            [
                *self._check_company_domain(self.env.company),
                ("account_type", "in", account_types),
            ],
            ['account_type'],
            ['code:array_agg'],
        )
        mapped = dict(data)
        return [mapped.get(account_type, []) for account_type in account_types]
