import calendar
from collections import defaultdict
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import models, api, _
from odoo.osv import expression
from odoo.tools import date_utils


class AccountAccount(models.Model):
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
            start = end = date(year, month, day)
        return start, end

    def _build_spreadsheet_formula_domain(self, formula_params):
        company_id = formula_params["company_id"] or self.env.company.id
        codes = [code for code in formula_params["codes"] if code]
        account_ids = self._get_all_accounts([formula_params], default_accounts=bool(not codes))[company_id].ids

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
        partner_ids = [int(partner_id) for partner_id in formula_params.get("partner_id", []) if partner_id]
        if partner_ids:
            domain = expression.AND(
                [domain, [("partner_id", "in", partner_ids)]]
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

        # Get all boundaries
        all_boundaries = set()
        for args in args_list:
            all_boundaries.add((args['date_from_boundary'], 'begin'))
            all_boundaries.add((args['date_to_boundary'], 'end'))

        all_boundaries = list(all_boundaries)
        all_boundaries.sort()

        # Compute non overlapping time period
        timeline = []
        for i in range(len(all_boundaries) - 1):
            start = all_boundaries[i]
            end = all_boundaries[i + 1]

            timeline.append((
                start[0] if start[1] == 'begin' else start[0] + relativedelta(days=1),
                end[0] if end[1] == 'end' else end[0] + relativedelta(days=-1),
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

        return [(date(year=1900, month=1, day=1), timeline[0][0] + relativedelta(days=-1))] + timeline

    def _get_all_accounts(self, args_list, default_accounts=False):
        company_to_codes = defaultdict(set)
        for args in args_list:
            codes = tuple({code for code in args["codes"] if code})
            company_to_codes[args['company_id'] or self.env.company.id].update(codes)

        default_domain = [('account_type', 'in', ['liability_payable', 'asset_receivable'])] if default_accounts else expression.FALSE_DOMAIN

        all_accounts = dict()
        for company_id, codes in company_to_codes.items():
            code_domain = expression.OR(
                [
                    ('code', '=like', f'{code}%'),
                ]
                for code in codes
            )
            domain = expression.AND([
                expression.OR([code_domain, default_domain]),
                self.env['account.account']._check_company_domain(company_id),
            ])
            accounts = self.env['account.account'].with_company(company_id).search(domain)
            all_accounts[company_id] = accounts

        return all_accounts

    def _get_all_lines(self, args_list, fields, timeline, accounts):
        if not args_list or not fields:
            return {}

        all_lines = {}
        aggregates = [field + ':sum' for field in fields]

        include_initial_balance_account_ids = []
        for company_id, acc in accounts.items():
            include_initial_balance_account_ids += acc.with_company(company_id).filtered('include_initial_balance').ids

        for period_num, period in enumerate(timeline):
            if period_num == 0:
                company_ids = list({args['company_id'] or self.env.company.id for args in args_list})
                account_ids = include_initial_balance_account_ids
            else:
                args_list_in_period = [args for args in args_list if period in args['date_periods']]
                company_ids = list({args['company_id'] or self.env.company.id for args in args_list_in_period})
                subcodes = tuple({subcode for args in args_list_in_period for subcode in args['codes'] if subcode})
                account_ids_in_period = self.env['account.account']
                for company_id in company_ids:
                    account_ids_in_period |= accounts[company_id].filtered(
                        lambda account:
                        account.with_company(company_id).code.startswith(subcodes)
                        or account.with_company(company_id).include_initial_balance
                    )
                account_ids = account_ids_in_period.ids

            domain = [
                *self.env['account.move.line']._check_company_domain(company_ids),
                ('account_id', 'in', account_ids),
                ('parent_state', 'in', ('draft', 'posted')),
                ('date', '>=', period[0]),
                ('date', '<=', period[1]),
            ]

            lines_in_period = self.env['account.move.line'].with_context(allowed_company_ids=company_ids)._read_group(
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

    @api.readonly
    @api.model
    def spreadsheet_move_line_action(self, args):
        self._pre_process_date_period_boundaries([args])
        domain = self._build_spreadsheet_formula_domain(args)
        codes = [code for code in args["codes"] if code]
        partner_ids = [partner_id for partner_id in args.get('partner_id', []) if partner_id]
        if codes:
            name = _("Journal items for account prefix %s", ", ".join(codes))
        elif partner_ids:
            name = _("Journal items for partner(s) %s", ", ".join(partner_ids))
        else:
            name = _("Journal items for payable and receivable accounts")
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move.line",
            "view_mode": "list",
            "views": [[False, "list"]],
            "target": "current",
            "domain": domain,
            "name": name,
        }

    @api.readonly
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
        return self._spreadsheet_fetch_data(args_list, ['debit', 'credit'])

    @api.readonly
    @api.model
    def spreadsheet_fetch_residual_amount(self, args_list):
        """Fetch data for ODOO.RESIDUAL formulas
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
        return self._spreadsheet_fetch_data(args_list, ['amount_residual'], default_accounts=True)

    @api.readonly
    @api.model
    def spreadsheet_fetch_partner_balance(self, args_list):
        """Fetch data for ODOO.PARTNER.BALANCE formulas
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
            partner_ids: str[]
        }]
        """
        return self._spreadsheet_fetch_data(args_list, ['balance'], default_accounts=True)

    @api.model
    def _spreadsheet_fetch_data(self, args_list, fields, default_accounts=False):
        if not args_list:
            return []

        self._pre_process_date_period_boundaries(args_list)
        timeline = self._pre_process_timeline(args_list)
        all_accounts = self._get_all_accounts(args_list, default_accounts=default_accounts)
        all_lines = self._get_all_lines(args_list, fields, timeline, all_accounts)

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
                accounts = all_accounts[company_id].filtered(lambda account: account.with_company(company_id).code.startswith(subcodes))
            else:
                accounts = all_accounts[company_id].filtered(lambda account: account.with_company(company_id).account_type in ['liability_payable', 'asset_receivable'])
            partner_ids = args.get('partner_ids')

            matching_keys = set()
            for account in accounts:
                # Initial balanced accounts are cumulated over the periods due to their nature. For that reason,
                # we need to add all previous period values for that account as well.
                past_periods = []
                if account.with_company(company_id).include_initial_balance:
                    past_periods = timeline[0:timeline.index(periods[0])]

                matching_keys.update(set(filter(
                    lambda line_key: (
                        # line_key should be (period, company_id, state, account_id, partner_ids)
                        line_key[0] in past_periods + periods
                        and line_key[1] == company_id
                        and line_key[2] in states
                        and line_key[3] == account.id
                        and (line_key[4] in partner_ids if partner_ids else True)
                    ),
                    all_lines.keys()
                )))

            cell_data = {field: 0.0 for field in fields}
            for matching_key in matching_keys:
                cell_data = {field: cell_data.get(field, 0.0) + all_lines[matching_key].get(field, 0.0) for field in fields}

            results.append(cell_data)
        return results

    @api.readonly
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
