import calendar
from collections import Counter, defaultdict
from datetime import date
from dateutil.relativedelta import relativedelta

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

    @api.model
    def _build_spreadsheet_formula_domain(self, formula_params):
        company_id = formula_params["company_id"] or self.env.company.id

        codes = [code for code in formula_params["codes"] if code]
        accounts = self._get_all_accounts([formula_params], default_accounts=bool(not codes))

        self._pre_process_date_period_boundaries([formula_params], accounts)

        start = formula_params['date_from_boundary']
        end = formula_params['date_to_boundary']

        balance_domain = [
            ("account_id.include_initial_balance", "=", True),
            ("date", "<=", end),
        ]
        pnl_domain = [
            ("account_id.include_initial_balance", "=", False),
            ("date", ">=", start),
            ("date", "<=", end),
        ]
        code_domain = [("account_id", "in", accounts[company_id].ids)]
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
        partner_ids = [int(partner_id) for partner_id in formula_params.get("partner_id", []) if partner_id]
        if partner_ids:
            domain = expression.AND(
                [domain, [("partner_id", "in", partner_ids)]]
            )
        return domain

    @api.model
    def _pre_process_date_period_boundaries(self, args_list, all_accounts : dict):
        include_initial_balance_account_ids = {
            company_id: acc.filtered('include_initial_balance')
            for company_id, acc in all_accounts.items()
        }

        for args in args_list:
            company_id = args['company_id'] or self.env.company.id
            company = self.env['res.company'].browse(company_id)

            start, end = self._get_date_period_boundaries(
                args['date_range'], company
            )

            # If the args accounts include at least one initial_balance accounts
            # We need to take it into concideration when creating the timeline
            subcodes = tuple({subcode for subcode in args.get('codes', []) if subcode})
            has_initial_balance_account = True
            if subcodes:
                has_initial_balance_account = any(
                    acc.code.startswith(subcodes)
                    for acc in include_initial_balance_account_ids[company_id]
                )

            args['needs_initial_balance'] = has_initial_balance_account
            args['date_from_boundary'] = start
            args['date_to_boundary'] = end

    @api.model
    def _get_timeline(self, args_list):

        # Counter and `depth` are used as a stack tracker to know whether or not we
        # are still in a broader period or at the end of one and about to start a new one.
        # The counter is necessary as several cells may have the same start date but
        # different end dates. Thus, we use the Counter to track how many period deep we are.
        all_boundaries_counter = Counter()
        for args in args_list:
            all_boundaries_counter[(args['date_from_boundary'], 'begin')] += 1
            all_boundaries_counter[(args['date_to_boundary'], 'end')] += 1
            if args['needs_initial_balance']:
                all_boundaries_counter[(date(year=1900, month=1, day=1), 'begin')] += 1
                all_boundaries_counter[(args['date_from_boundary'] + relativedelta(days=-1), 'end')] += 1

        # Get all boundaries sorted by dates
        all_boundaries = sorted(all_boundaries_counter)

        # Compute non overlapping time period
        timeline = []
        depth = 0
        for start, end in zip(all_boundaries[:-1], all_boundaries[1:]):
            # We don't add a new time period if we just finished one and are not in a broader one.
            # For example:
            # - cell 1: 01/03/2020 -> 31/03/2020
            # - cell 2: 01/05/2020 -> 31/05/2020
            # We don't want to compute the period between cell 1 and cell 2; 01/04/2020 -> 30/04/2020
            # But if we also have:
            # - cell 3: 01/01/2020 -> 31/12/2020, we want to compute it.
            if depth == 0 and start[1] == 'end':
                continue

            if start[1] == 'begin':
                depth += all_boundaries_counter[start]
            if end[1] == 'end':
                depth -= all_boundaries_counter[end]

            period_start = start[0] if start[1] == 'begin' else start[0] + relativedelta(days=1)
            period_end = end[0] if end[1] == 'end' else end[0] + relativedelta(days=-1)

            # The if condition deals with the issue that occurs when we have:
            # cell 1 - 01/01/2020 -> 31/12/2020
            # cell 2 - 01/03/2020 -> 31/03/2020
            # cell 3 - 01/04/2020 -> 30/04/2020
            # In such scenario, we actually compute the time period between cell 2 and cell 3 because
            # we are are in a broader time period due to cell 1. This leads to the following unwanted
            # time period to be added to the timeline: (01/04/2020, 31/03/2020)
            if period_start <= period_end:
                timeline.append((period_start, period_end))

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

    @api.model
    def _get_all_accounts(self, args_list, default_accounts=False):
        company_to_codes = defaultdict(set)
        for args in args_list:
            codes = {code for code in args["codes"] if code}
            company_to_codes[args['company_id'] or self.env.company.id].update(codes)

        default_domain = [('account_type', 'in', ['liability_payable', 'asset_receivable'])] if default_accounts else expression.FALSE_DOMAIN

        all_accounts = dict()
        for company_id, codes in company_to_codes.items():
            code_domain = expression.OR(
                [('code', '=like', f'{code}%')]
                for code in codes
            )
            domain = expression.AND([
                expression.OR([code_domain, default_domain]),
                self.env['account.account']._check_company_domain(company_id),
            ])
            accounts = self.env['account.account'].with_company(company_id).search(domain)
            all_accounts[company_id] = accounts

        return all_accounts

    @api.model
    def _get_all_lines(self, args_list, fields, timeline, accounts):
        if not args_list or not fields:
            return {}

        all_lines = {}
        aggregates = [field + ':sum' for field in fields]

        all_include_initial_balance_account_ids = set()
        for company_id, acc in accounts.items():
            all_include_initial_balance_account_ids.update(acc.filtered('include_initial_balance').ids)

        include_initial_balance_accounts_ids = set()
        company_ids = set()

        for period in reversed(timeline):
            account_ids = set()

            args_list_in_period = [args for args in args_list if period in args['date_periods']]
            for args in args_list_in_period:
                company_id = args['company_id'] or self.env.company.id
                company_ids.add(company_id)

                subcodes = tuple({subcode for subcode in args['codes'] if subcode})
                if subcodes:
                    accounts_ids_to_fetch = set(accounts[company_id].filtered(
                        lambda account: account.code.startswith(subcodes)
                    ).ids)
                else:
                    accounts_ids_to_fetch = set(accounts[company_id].filtered('include_initial_balance').ids)

                include_initial_balance_accounts_ids.update(accounts_ids_to_fetch & all_include_initial_balance_account_ids)
                account_ids.update(accounts_ids_to_fetch)

            account_ids = account_ids | include_initial_balance_accounts_ids
            if not account_ids:
                continue

            domain = [
                *self.env['account.move.line']._check_company_domain(list(company_ids)),
                ('account_id', 'in', list(account_ids)),
                ('parent_state', 'in', ('draft', 'posted')),
                ('date', '>=', period[0]),
                ('date', '<=', period[1]),
            ]

            lines_in_period = self.env['account.move.line'].with_context(allowed_company_ids=list(company_ids))._read_group(
                domain=domain,
                groupby=['company_id', 'parent_state', 'account_id', 'partner_id'],
                aggregates=aggregates,
            )
            all_lines.update({
                (period, company.id, state, account.id, partner.id): dict(zip(fields, val))
                for company, state, account, partner, *val in lines_in_period
            })
        return all_lines

    # ------------------------ #
    #      API functions       #
    # ------------------------ #

    @api.model
    def spreadsheet_move_line_action(self, args):
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move.line",
            "view_mode": "list",
            "views": [[False, "list"]],
            "target": "current",
            "domain": self._build_spreadsheet_formula_domain(args),
            "name": _("Cell Audit"),
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
        return self._spreadsheet_fetch_data(args_list, ['debit', 'credit'])

    @api.model
    def spreadsheet_fetch_residual_amount(self, args_list):
        """Fetch data for ODOO.RESIDUAL formulas
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
        return self._spreadsheet_fetch_data(args_list, ['amount_residual'], default_accounts=True)

    @api.model
    def spreadsheet_fetch_partner_balance(self, args_list):
        """Fetch data for ODOO.PARTNER.BALANCE formulas
        The input list looks like this:
        [{
            date_range: {
                range_type: "year"
                year: int
            },
            company_id: int
            codes: str[]
            include_unposted: bool
            partner_ids: str[]
        }]
        """
        return self._spreadsheet_fetch_data(args_list, ['balance'], default_accounts=True)

    @api.model
    def _spreadsheet_fetch_data(self, args_list, fields, default_accounts=False):
        if not args_list:
            return []

        all_accounts = self._get_all_accounts(args_list, default_accounts=default_accounts)
        self._pre_process_date_period_boundaries(args_list, all_accounts)
        timeline = self._get_timeline(args_list)
        all_lines = self._get_all_lines(args_list, fields, timeline, all_accounts)
        all_partner_ids = {line[4] for line in all_lines}

        results = []
        for args in args_list:
            subcodes = tuple({subcode for subcode in args["codes"] if subcode})

            if not subcodes and not default_accounts:
                results.append({field: 0.0 for field in fields})
                continue

            company_id = args['company_id'] or self.env.company.id
            states = ['posted', 'draft'] if args['include_unposted'] else ['posted']
            periods = args['date_periods']
            if subcodes:
                accounts = all_accounts[company_id].filtered(lambda account: account.code.startswith(subcodes))
            else:
                accounts = all_accounts[company_id].filtered(lambda account: account.account_type in ['liability_payable', 'asset_receivable'])
            partner_ids = set(args.get('partner_ids', [])) or all_partner_ids

            cell_data = {field: 0.0 for field in fields}
            for account in accounts:
                # Initial balanced accounts are cumulated over the periods due to their nature. For that reason,
                # we need to add all previous period values for that account as well.
                past_periods = []
                if account.include_initial_balance:
                    past_periods = timeline[0:timeline.index(periods[0])]

                for period in past_periods + periods:
                    for state in states:
                        for partner_id in partner_ids:
                            for field in fields:
                                cell_data[field] += all_lines.get((period, company_id, state, account.id, partner_id), {}).get(field, 0.0)

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
