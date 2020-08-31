# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from copy import deepcopy

from odoo import models, api, _, fields


class AccountChartOfAccountReport(models.AbstractModel):
    _name = "account.coa.report"
    _description = "Chart of Account Report"
    _inherit = "account.report"

    filter_date = {'mode': 'range', 'filter': 'this_month'}
    filter_comparison = {'date_from': '', 'date_to': '', 'filter': 'no_comparison', 'number_period': 1}
    filter_all_entries = False
    filter_journals = True
    filter_analytic = True
    filter_unfold_all = False
    filter_cash_basis = None
    filter_hierarchy = False
    MAX_LINES = None

    @api.model
    def _get_templates(self):
        templates = super(AccountChartOfAccountReport, self)._get_templates()
        templates['main_table_header_template'] = 'account_reports.template_coa_table_header'
        return templates

    @api.model
    def _get_columns_name(self, options):
        columns = [
            {'name': '', 'style': 'width:40%'},
            {'name': _('Debit'), 'class': 'number'},
            {'name': _('Credit'), 'class': 'number'},
        ]
        if options.get('comparison') and options['comparison'].get('periods'):
            columns += [
                {'name': _('Debit'), 'class': 'number '},
                {'name': _('Credit'), 'class': 'number'},
            ] * len(options['comparison']['periods'])
        return columns + [
            {'name': _('Debit'), 'class': 'number '},
            {'name': _('Credit'), 'class': 'number'},
            {'name': _('Debit'), 'class': 'number '},
            {'name': _('Credit'), 'class': 'number'},
        ]

    @api.model
    def _get_super_columns(self, options):
        date_cols = options.get('date') and [options['date']] or []
        date_cols += (options.get('comparison') or {}).get('periods', [])

        columns = [{'string': _('Initial Balance')}]
        columns += reversed(date_cols)
        columns += [{'string': _('Total')}]

        return {'columns': columns, 'x_offset': 1, 'merge': 2}

    @api.model
    def _get_lines(self, options, line_id=None):
        # Create new options with 'unfold_all' to compute the initial balances.
        # Then, the '_do_query' will compute all sums/unaffected earnings/initial balances for all comparisons.
        new_options = options.copy()
        new_options['unfold_all'] = True
        options_list = self._get_options_periods_list(new_options)
        accounts_results, taxes_results = self.env['account.general.ledger']._do_query(options_list, fetch_lines=False)

        lines = []
        totals = [0.0] * (2 * (len(options_list) + 2))

        # Add lines, one per account.account record.
        for account, periods_results in accounts_results:
            sums = []
            account_balance = 0.0
            for i, period_values in enumerate(reversed(periods_results)):
                account_sum = period_values.get('sum', {})
                account_un_earn = period_values.get('unaffected_earnings', {})
                account_init_bal = period_values.get('initial_balance', {})

                if i == 0:
                    # Append the initial balances.
                    initial_balance = account_init_bal.get('balance', 0.0) + account_un_earn.get('balance', 0.0)
                    sums += [
                        initial_balance > 0 and initial_balance or 0.0,
                        initial_balance < 0 and -initial_balance or 0.0,
                    ]
                    account_balance += initial_balance

                # Append the debit/credit columns.
                sums += [
                    account_sum.get('debit', 0.0) - account_init_bal.get('debit', 0.0),
                    account_sum.get('credit', 0.0) - account_init_bal.get('credit', 0.0),
                ]
                account_balance += sums[-2] - sums[-1]

            # Append the totals.
            sums += [
                account_balance > 0 and account_balance or 0.0,
                account_balance < 0 and -account_balance or 0.0,
            ]

            # account.account report line.
            columns = []
            for i, value in enumerate(sums):
                # Update totals.
                totals[i] += value

                # Create columns.
                columns.append({'name': self.format_value(value, blank_if_zero=True), 'class': 'number', 'no_format_name': value})

            name = account.name_get()[0][1]
            if len(name) > 40 and not self._context.get('print_mode'):
                name = name[:40]+'...'

            lines.append({
                'id': account.id,
                'name': name,
                'title_hover': name,
                'columns': columns,
                'unfoldable': False,
                'caret_options': 'account.account',
            })

        # Total report line.
        lines.append({
             'id': 'grouped_accounts_total',
             'name': _('Total'),
             'class': 'total',
             'columns': [{'name': self.format_value(total), 'class': 'number'} for total in totals],
             'level': 1,
        })

        return lines

    @api.model
    def _get_report_name(self):
        return _("Trial Balance")
