# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
import calendar
from dateutil.relativedelta import relativedelta
from collections import defaultdict

from odoo import models, api, _
from odoo.osv import expression
from odoo.tools import date_utils


class AccountAccount(models.Model):
    _inherit = ["account.account"]

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
            start = end = date(year, month, day)
            # start, _ = date_utils.get_fiscal_year(end, fiscal_day, fiscal_month)
        return start, end

    def _build_spreadsheet_formula_domain(self, formula_params):
        codes = [code for code in formula_params["codes"] if code]
        if not codes:
            return expression.FALSE_DOMAIN

        company_id = formula_params["company_id"] or self.env.company.id
        company = self.env["res.company"].browse(company_id)

        account_ids = self._get_all_accounts([formula_params]).ids

        start = formula_params['date_from_boundary']
        end = formula_params['date_to_boundary']

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

    def _pre_process_date_period_boundaries(self, args_list):
        for args in args_list:
            company_id = args['company_id'] or self.env.company.id
            company = self.env['res.company'].browse(company_id)

            start, _end = self._get_date_period_boundaries(
                args['date_from'], company
            )
            _start, end = self._get_date_period_boundaries(
                args['date_to'], company
            )

            args['date_from_boundary'] = start
            args['date_to_boundary'] = end

    def _pre_process_timeline(self, args_list):

        # Get all bounderies
        all_periods = set()
        for args in args_list:
            all_periods.add((args['date_from_boundary'], '0'))
            all_periods.add((args['date_to_boundary'], '1'))

        all_periods = list(all_periods)
        all_periods.sort()

        # Compute non overlapping time period
        timeline = []
        for i in range(len(all_periods) - 1):
            start = all_periods[i]
            end = all_periods[i + 1]

            timeline.append((
                start[0] if start[1] == '0' else start[0] + relativedelta(days=1),
                end[0] if end[1] == '1' else end[0] + relativedelta(days=-1),
            ))

        # Compute in which time period(s) the cell is part of
        all_starts = [period[0] for period in timeline]
        all_ends = [period[1] for period in timeline]
        for args in args_list:
            start = args['date_from_boundary']
            end = args['date_to_boundary']

            start_index = all_starts.index(start)
            end_index = all_ends.index(end)

            args['date_periods'] = timeline[start_index:end_index + 1]

        return timeline

    def _get_all_accounts(self, args_list):
        company_to_codes = {
            args['company_id'] or self.env.company_id: tuple({code for code in args["codes"] if code})
            for args in args_list
        }

        all_accounts = self.env['account.account']
        for company_id, codes in company_to_codes.items():
            domain = expression.OR(
                [
                    ("code", "=like", f"{code}%"),
                ]
                for code in codes
            )
            all_accounts |= self.env["account.account"].with_company(company_id).search(domain)

        return all_accounts

    def _get_all_lines(self, args_list, fields, periods, accounts):
        if not args_list or not fields:
            return {}

        all_lines = {}
        aggregates = [field + ':sum' for field in fields]

        for period in periods:
            args_list_in_period = [args for args in args_list if period in args['date_periods']]
            company_ids = list({args['company_id'] or self.env.company.id for args in args_list_in_period})
            subcodes = tuple({subcode for args in args_list_in_period for subcode in args["codes"] if subcode})
            accounts_in_period = accounts.filtered(lambda acc: acc.code.startswith(subcodes))

            # TODO: manage partner_id somehow (using an extra_group_by param maybe?)

            common_domain = [
                *self.env['account.move.line']._check_company_domain(company_ids),
                ('account_id', 'in', accounts_in_period.ids),
                ('parent_state', 'in', ('draft', 'posted')),
            ]
            balance_domain = [
                ("account_id.include_initial_balance", "=", True),
                ("date", "<=", period[1]),
            ]
            pnl_domain = [
                ("account_id.include_initial_balance", "=", False),
                ("date", ">=", period[0]),
                ("date", "<=", period[1]),
            ]
            period_domain = expression.OR([balance_domain, pnl_domain])
            domain = expression.AND([common_domain, period_domain])

            lines_in_period = self.env['account.move.line']._read_group(
                domain=domain,
                groupby=['company_id', 'parent_state', 'account_id'],
                aggregates=aggregates,
            )

            all_lines.update({(period, company.id, state, account.id): {field: val for field, val in zip(fields, val)} for company, state, account, *val in lines_in_period})
        return all_lines

    # ------------------------ #
    #      API functions       #
    # ------------------------ #

    @api.model
    def spreadsheet_move_line_action(self, args):
        self._pre_process_date_period_boundaries([args])
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
        return self.spreadsheet_fetch_data(args_list, ['debit', 'credit'])

    @api.model
    def spreadsheet_fetch_data(self, args_list, fields):
        self._pre_process_date_period_boundaries(args_list)
        timeline = self._pre_process_timeline(args_list)
        all_accounts = self._get_all_accounts(args_list)
        all_lines = self._get_all_lines(args_list, fields, timeline, all_accounts)

        results = []
        for args in args_list:
            subcodes = tuple({subcode for subcode in args["codes"] if subcode})

            if not subcodes:
                results.append({field: 0.0 for field in fields})
                continue

            company_id = args['company_id'] or self.env.company.id
            states = ['posted', 'draft'] if args['include_unposted'] else ['posted']
            periods = args['date_periods']

            accounts = all_accounts.filtered(lambda acc: acc.with_company(company_id).code.startswith(subcodes))

            cell_data = {field: 0.0 for field in fields}
            for account in accounts:
                for state in states:
                    for period in periods:
                        # Initial balanced accounts are cumulated over the periods due to their nature. For that reason,
                        # we only add the lastest one in such case
                        if account.include_initial_balance and period != periods[-1]:
                            continue

                        data = all_lines.get((period, company_id, state, account.id), {field: 0.0 for field in fields})
                        cell_data = {field: cell_data.get(field, 0.0) + data.get(field, 0.0) for field in fields}

            results.append(cell_data)
        return results

    @api.model
    def get_account_group(self, account_types):
        data = self._read_group(
            [
                *self.env['account.account']._check_company_domain(self.env.company),
                ("account_type", "in", account_types),
            ],
            ['account_type'],
            ['code:array_agg'],
        )
        mapped = dict(data)
        return [mapped.get(account_type, []) for account_type in account_types]
