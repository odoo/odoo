from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models, release
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

DATEFORMAT_SIE4 = '%Y%m%d'
DATEFORMAT_MAIN = DEFAULT_SERVER_DATE_FORMAT


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options)
        if self.env.company.account_fiscal_country_id.code == 'SE':
            options.setdefault('buttons', []).append({
                'name': _("SIE 4"),
                'sequence': 50,
                'action': 'export_file',
                'action_param': 'export_l10n_se_sie4_file',
                'file_export_type': _("SIE")
            })

    @api.model
    def _get_l10n_se_sie4_dates(self, options, use_sie4_format=False):
        """ Returns a dictionary of date strings from previous year's start to next year's end in the desired format.

        :param options: ``account.report`` options dictionary
        :param use_sie4_format: desired format. ex: without sie4_format '2024-01-01' -> with sie4_format '20240101'
        """
        result_strf = DATEFORMAT_SIE4 if use_sie4_format else DATEFORMAT_MAIN
        datetime_from = datetime.strptime(options['date']['date_from'], DATEFORMAT_MAIN)
        datetime_to = datetime.strptime(options['date']['date_to'], DATEFORMAT_MAIN)
        return {
            'prev_date_from': (datetime_from - relativedelta(years=1)).strftime(result_strf),
            'prev_date_to': (datetime_to - relativedelta(years=1)).strftime(result_strf),
            'curr_date_from': datetime_from.strftime(result_strf),
            'curr_date_to': datetime_to.strftime(result_strf),
            'next_date_from': (datetime_from + relativedelta(years=1)).strftime(result_strf),
            'next_date_to': (datetime_to + relativedelta(years=1)).strftime(result_strf),
        }

    @api.model
    def _get_l10n_se_sie4_ktyp(self, account_type):
        group_asset = {'asset_receivable', 'asset_cash', 'asset_current', 'asset_non_current', 'asset_prepayments', 'asset_fixed'}
        group_debt = {'liability_payable', 'liability_credit_card', 'liability_current', 'liability_non_current', 'equity',
                      'equity_unaffected', 'off_balance'}
        group_cost = {'expense', 'expense_depreciation', 'expense_direct_cost'}

        if account_type in group_asset:
            return 'T'
        if account_type in group_debt:
            return 'S'
        if account_type in group_cost:
            return 'K'
        return 'I'  # income type

    @api.model
    def _get_l10n_se_sie4_options(self, report, date_from, date_to):
        return report.get_options({
            'date': {
                'date_from': date_from,
                'date_to': date_to,
                'mode': 'range',
                'filter': 'custom',
            },
        })

    @api.model
    def _export_l10n_se_sie4_identification(self, options):
        dates = self._get_l10n_se_sie4_dates(options, use_sie4_format=True)

        return [
            '#FLAGGA 0',
            '#FORMAT PC8',
            '#SIETYP 4',
            f'#PROGRAM "Odoo" {release.version}',
            f'#GEN {fields.Date.context_today(self).strftime(DATEFORMAT_SIE4)}',
            f'#FNAMN "{options["companies"][0]["name"]}"',
            f'#RAR -1 {dates["prev_date_from"]} {dates["prev_date_to"]}',
            f'#RAR  0 {dates["curr_date_from"]} {dates["curr_date_to"]}',
        ]

    @api.model
    def _export_l10n_se_sie4_chart_of_account(self, options):
        sie4_coa_lines = []
        company_id = options['companies'][0]['id']
        accounts = self.env['account.account'].with_company(company_id).search([])

        for account in accounts:
            sie4_coa_lines.extend((
                f'#KONTO {account.code} "{account.name}"',
                f'#KTYP  {account.code} {self._get_l10n_se_sie4_ktyp(account.account_type)}',
            ))

        return sie4_coa_lines

    @api.model
    def _export_l10n_se_sie4_bs_balance(self, options):
        """ Generates the opening/closing balance lines and return them as a list of string line.
        In SIE 4, the opening/closing balance lines are saved with the following keywords:

        - "IB" -> Opening balance
        - "UB" -> Closing balance

        The number to the next of them refers to what year they are referring to.
        "0" means current year, "-1" means previous year.
        Consequently, this also means that "#UB -1" is the exact same as "#IB 0".
        """
        sie4_bs_balance_lines = []
        report = self.env['account.report'].browse(options['report_id'])
        dates = self._get_l10n_se_sie4_dates(options)
        company_id = options['companies'][0]['id']
        bs_accounts = self.env['account.account'].with_company(company_id).search_fetch(
            domain=[('include_initial_balance', '=', True)],
            field_names=['id'],
        )
        seen_bs_account_codes = set()
        prev_ib, prev_ub, curr_ib, curr_ub = {}, {}, {}, {}  # dict[str, str] | {account_code: balance_str_line}

        prev_year_options = self._get_l10n_se_sie4_options(report, dates['prev_date_from'], dates['prev_date_to'])
        next_year_options = self._get_l10n_se_sie4_options(report, dates['next_date_from'], dates['next_date_to'])
        report._init_currency_table(prev_year_options)
        report._init_currency_table(options)
        report._init_currency_table(next_year_options)
        prev_ib_values = self.with_company(company_id)._get_initial_balance_values(report, bs_accounts.mapped('id'), prev_year_options)
        curr_ib_values = self.with_company(company_id)._get_initial_balance_values(report, bs_accounts.mapped('id'), options)
        next_ib_values = self.with_company(company_id)._get_initial_balance_values(report, bs_accounts.mapped('id'), next_year_options)

        for ib_values in (prev_ib_values, curr_ib_values, next_ib_values):
            for account_id, (account, ib_map) in ib_values.items():
                ib_item = next(iter(ib_map.values()))
                if ib_item != {}:
                    seen_bs_account_codes.add(account.code)
                    if ib_values is prev_ib_values:  # for [IB/-1] (previous year opening balance)
                        prev_ib[account.code] = f'#IB  -1 {account.code} {ib_item["balance"]}'
                    elif ib_values is curr_ib_values:  # for [UB/-1] and [IB/0] (previous year closing balance + current year opening balance)
                        prev_ub[account.code] = f'#UB  -1 {account.code} {ib_item["balance"]}'
                        curr_ib[account.code] = f'#IB   0 {account.code} {ib_item["balance"]}'
                    else:  # ib_values is next_ib_values  # for [UB/0] (current year closing balance)
                        curr_ub[account.code] = f'#UB   0 {account.code} {ib_item["balance"]}'

        default_ib_values = ('#IB  -1', '#UB  -1', '#IB   0', '#UB   0')
        for account_code in sorted(seen_bs_account_codes):
            for idx, period_ib in enumerate((prev_ib, prev_ub, curr_ib, curr_ub)):
                if account_code in period_ib:
                    sie4_bs_balance_lines.append(period_ib[account_code])
                else:  # if the mentioned account doesn't exist in other periods, fill it with a default value
                    default_ib_value = default_ib_values[idx]
                    sie4_bs_balance_lines.append(f'{default_ib_value} {account_code} 0.0')

        return sie4_bs_balance_lines

    @api.model
    def _export_l10n_se_sie4_pl_balance(self, options):
        sie4_pl_balance_lines = []
        dates = self._get_l10n_se_sie4_dates(options)
        company_id = options['companies'][0]['id']

        common_domain = [
            ('account_id.include_initial_balance', '=', False),
            ('display_type', 'not in', ('line_note', 'line_section')),
            ('move_id.state', '!=', 'cancel'),
        ]
        prev_year_domain = common_domain + [('date', '>=', dates['prev_date_from']), ('date', '<=', dates['prev_date_to'])]
        curr_year_domain = common_domain + [('date', '>=', dates['curr_date_from']), ('date', '<=', dates['curr_date_to'])]

        prev_account_sum_group = self.env['account.move.line'].with_company(company_id)._read_group(prev_year_domain, ['account_id'], ['balance:sum'])
        curr_account_sum_group = self.env['account.move.line'].with_company(company_id)._read_group(curr_year_domain, ['account_id'], ['balance:sum'])
        prev_code_sum_map = {account.code: str(account_sum) for account, account_sum in prev_account_sum_group}
        curr_code_sum_map = {account.code: str(account_sum) for account, account_sum in curr_account_sum_group}
        seen_account_code = set(prev_code_sum_map.keys()).union(curr_code_sum_map.keys())

        for account_code in sorted(seen_account_code):
            sie4_pl_balance_lines.extend((
                f'#RES -1 {account_code} {prev_code_sum_map.get(account_code, "0.0")}',
                f'#RES  0 {account_code} {curr_code_sum_map.get(account_code, "0.0")}',
            ))

        return sie4_pl_balance_lines

    @api.model
    def _export_l10n_se_sie4_verification(self, options):
        sie4_verification_lines = []
        dates = self._get_l10n_se_sie4_dates(options)
        company_id = options['companies'][0]['id']
        unsupported_display_type = {'line_note', 'line_section'}
        moves = self.env['account.move'].with_company(company_id).search([
            ('state', '=', 'posted'),
            ('date', '>=', dates['curr_date_from']),
            ('date', '<=', dates['curr_date_to']),
        ])

        for verification_idx, move in enumerate(moves.sorted(reverse=True), start=1):
            transactions = []
            for line in move.line_ids:
                if line.display_type not in unsupported_display_type:
                    transactions.append(f'    #TRANS {line.account_id.code} {{}} {line.balance}')

            sie4_verification_lines.extend((
                f'#VER A {verification_idx} {move.date.strftime(DATEFORMAT_SIE4)} "{move.name}"',
                '{', *transactions, '}',
            ))

        return sie4_verification_lines

    def export_l10n_se_sie4_file(self, options):
        if options['date']['period_type'] != 'fiscalyear':
            raise UserError(_("You must set the period type to be in fiscal year in order to export SIE 4 file."))
        if len(options['companies']) > 1:
            selected_companies = self.env['res.company'].search_fetch(
                domain=[('id', 'in', [company_dict['id'] for company_dict in options['companies']])],
                field_names=['chart_template'],
            )
            if len(set(selected_companies.mapped('chart_template'))) >= 2:  # we can only export one chart template
                raise UserError(_("You can't export multiple companies with different templates."))
            else:
                # filter other selected company/ies in the options
                options['companies'] = [company_dict for company_dict in options['companies'] if company_dict['id'] == self.env.company.id]

        content_lines = [
            *self._export_l10n_se_sie4_identification(options),
            *self._export_l10n_se_sie4_chart_of_account(options),
            *self._export_l10n_se_sie4_bs_balance(options),
            *self._export_l10n_se_sie4_pl_balance(options),
            *self._export_l10n_se_sie4_verification(options),
            '',  # to make sure the file ends with a new line
        ]
        return {
            'file_name': f'odoo_sie4_{fields.Date.context_today(self).strftime(DATEFORMAT_SIE4)}.se',
            'file_content': '\n'.join(content_lines).encode('ISO-8859-1'),
            'file_type': 'txt',
        }
