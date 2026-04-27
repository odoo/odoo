# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.tools import SQL

from collections import OrderedDict
from datetime import timedelta


class ChileanReportCustomHandler(models.AbstractModel):
    _name = 'l10n_cl.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Chilean Report Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        # dict of the form {account_id: {column_group_key: {expression_label: value}}}
        lines_dict = {}

        # totals dictionaries: dicts of the form {column_group_key: {expression_label: total_value}}
        subtotals_dict = {}
        fiscalyear_result_dict = {}
        previous_years_unallocated_earnings_dict = {}
        totals_dict = {}

        # Build query
        query_list = []
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            query = self._prepare_query(report, column_group_options, column_group_key)
            query_list.append(SQL("(%s)", query))

            # Set defaults here since the results of the query for this column_group_key might be empty
            subtotals_dict[column_group_key] = dict.fromkeys([col['expression_label'] for col in column_group_options['columns']], 0.0)

        full_query = SQL(" UNION ALL ").join(query_list)
        self._cr.execute(full_query)

        # Fill lines and subtotals dictionaries
        for result in self._cr.dictfetchall():
            account_id = result['id']
            column_group_key = result['column_group_key']

            lines_dict.setdefault(account_id, {})

            lines_dict[account_id]['full_name'] = f"{result['code']} {result['name']}" if result['code'] else result['name']
            lines_dict[account_id][column_group_key] = result

            for expression_label in subtotals_dict[column_group_key]:
                subtotals_dict[column_group_key][expression_label] += result[expression_label]

        # Compute other 'total' lines
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            subtotals = subtotals_dict[column_group_key]

            fiscalyear_result = self._calculate_fiscalyear_result(column_group_options, subtotals)
            fiscalyear_result_dict[column_group_key] = fiscalyear_result

            previous_years_unallocated_earnings = self._calculate_previous_years_unallocated_earnings(report, column_group_options)
            previous_years_unallocated_earnings_dict[column_group_key] = previous_years_unallocated_earnings

            totals = self._calculate_totals(column_group_options, subtotals, fiscalyear_result, previous_years_unallocated_earnings)
            totals_dict[column_group_key] = totals

        lines = []
        for account_id, line_vals in lines_dict.items():
            line = self._create_report_line(report, options, line_vals, account_id)
            lines.append((0, line))

        # Subtotals line
        lines.append((0, self._create_report_total_line(report, options, subtotals_dict, _("Subtotal"), 2, markup='subtotals')))
        # Fiscal year results line
        lines.append((0, self._create_report_total_line(report, options, fiscalyear_result_dict, _("Profit and Loss"), 3, markup='fiscalyear_result')))
        # Previous year unallocated earnings line
        unalloc_line = self._create_report_total_line(
            report, options, previous_years_unallocated_earnings_dict, _("Previous years unallocated earnings"), 3, markup='previous_years_unallocated_earnings')
        if any(not self.env.company.currency_id.is_zero(column['no_format']) for column in unalloc_line['columns']):
            lines.append((0, unalloc_line))
        # General total line
        lines.append((0, self._create_report_total_line(report, options, totals_dict, _("Total"), 1, markup='general_total')))

        return lines

    @api.model
    def _prepare_query(self, report, options, column_group_key) -> SQL:
        domain = [
            '|',
            ('date', '>=', options['date']['date_from']),
            '&',
            ('account_id.include_initial_balance', '=', True),
            ('account_id.account_type', '!=', 'equity_unaffected'),
        ]
        query = report._get_report_query(options, 'from_beginning', domain=domain)
        query.add_join('JOIN', alias='aa', table='account_account', condition=SQL('account_move_line.account_id = aa.id'))
        account_code = self.env['account.account']._field_to_sql('aa', 'code', query)
        account_name = self.env['account.account']._field_to_sql('aa', 'name')

        sql_query = SQL(
            """
            SELECT %(column_group_key)s AS column_group_key,
                   aa.id, %(account_code)s AS code, %(account_name)s AS name,
                   SUM(account_move_line.debit) AS debit,
                   SUM(account_move_line.credit) AS credit,
                   GREATEST(SUM(account_move_line.balance), 0) AS debitor,
                   GREATEST(SUM(-account_move_line.balance), 0) AS creditor,
                   CASE WHEN %(bs)s THEN GREATEST(SUM(account_move_line.balance), 0) ELSE 0 END AS assets,
                   CASE WHEN %(bs)s THEN GREATEST(SUM(-account_move_line.balance), 0) ELSE 0 END AS liabilities,
                   CASE WHEN %(pnl)s THEN GREATEST(SUM(account_move_line.balance), 0) ELSE 0 END AS loss,
                   CASE WHEN %(pnl)s THEN GREATEST(SUM(-account_move_line.balance), 0) ELSE 0 END AS gain
            FROM %(table_references)s
            WHERE %(search_condition)s
            GROUP BY aa.id, %(account_code)s, %(account_name)s
            ORDER BY %(account_code)s
            """,
            column_group_key=column_group_key,
            account_code=account_code,
            account_name=account_name,
            table_references=query.from_clause,
            search_condition=query.where_clause,
            bs=SQL("aa.account_type LIKE 'asset%%' OR aa.account_type LIKE 'liability%%' OR aa.account_type LIKE 'equity%%'"),
            pnl=SQL("aa.account_type LIKE 'expense%%' OR aa.account_type LIKE 'income%%'"),
        )
        return sql_query

    def _create_report_line(self, report, options, vals, vals_id):
        """ Create a standard (non total) line for the report
        :param options: report options
        :param vals: values necessary for the line
        :param vals_id: id of the account
        """

        columns = []
        for column in options['columns']:
            col_value = vals.get(column['column_group_key'], {}).get(column['expression_label'], False)
            columns.append(report._build_column_dict(col_value, column, options=options))

        return {
            'id': report._get_generic_line_id('account.account', vals_id),
            'caret_options': 'account.account',
            'name': vals['full_name'],
            'columns': columns,
            'level': 2,
        }

    def _create_report_total_line(self, report, options, total_vals, name, level=1, markup=''):
        """ Create a total line for the report
        :param options: report options
        :param total_vals: values necessary for the line
        :param name: name given to the total line
        :param level: the level of the total line
        """
        if not total_vals:
            total_vals = {}

        columns = []
        for column in options['columns']:
            col_value = total_vals.get(column['column_group_key'], {}).get(column['expression_label'], False)
            columns.append(report._build_column_dict(col_value, column, options=options))
        return {
            'id': report._get_generic_line_id(None, None, markup=markup),
            'name': name,
            'level': level,
            'columns': columns,
        }

    def _calculate_fiscalyear_result(self, options, subtotal_line):
        exercise_result = OrderedDict.fromkeys([col['expression_label'] for col in options['columns']], 0)
        if subtotal_line['gain'] >= subtotal_line['loss']:
            exercise_result['loss'] = subtotal_line['gain'] - subtotal_line['loss']
            exercise_result['liabilities'] = exercise_result['loss']
        else:
            exercise_result['gain'] = subtotal_line['loss'] - subtotal_line['gain']
            exercise_result['assets'] = exercise_result['gain']
        return exercise_result

    def _calculate_unallocated_earnings_value(self, report, options):
        """
            Get all the unallocated earnings value from the previous fiscal years.
            The past moves that target Income and expense account (+ special type of expenses)
            are summed, and the allocated earnings are removed by summing the balances
            of the moves targeting the special account 'Undistributed Profits/Losses'.
        """
        new_options = options.copy()
        date_from_str = new_options.get('date', {}).get('date_from', '')
        date_from = fields.Date.from_string(date_from_str) or fields.Date.today()
        fiscal_dates = self.env.company.compute_fiscalyear_dates(date_from)
        new_options['date'] = report._get_dates_period(
            None,
            fiscal_dates['date_from'] - timedelta(days=1),
            'range',
            period_type='custom')
        query = report._get_report_query(new_options, 'strict_range')
        account_types = (
            'equity_unaffected',
            'income',
            'income_other',
            'expense_direct_cost',
            'expense',
            'expense_depreciation'
        )
        sql_query = SQL(
            """
            SELECT -SUM(account_move_line.balance) as unaffected_earnings
            FROM account_account AS aa, %(table_references)s
            WHERE %(search_condition)s
            AND aa.id = account_move_line.account_id
            AND aa.account_type IN %(account_types)s
            """.strip('\n'),
            table_references=query.from_clause,
            search_condition=query.where_clause,
            account_types=account_types,
        )
        self.env.cr.execute(sql_query)
        value = self.env.cr.fetchone()[0] or 0.0
        return self.env.company.currency_id.round(value)

    def _calculate_previous_years_unallocated_earnings(self, report, options):
        earning = self._calculate_unallocated_earnings_value(report, options)
        if not earning:
            return {}

        sum_col, sold_col, liabilities_sign = {
            True: ('debit', 'debitor', -1),
            False: ('credit', 'creditor', 1),
        }.get(earning < 0)

        abs_earning = abs(earning)
        row = OrderedDict.fromkeys([col['expression_label'] for col in options['columns']], 0)
        row[sum_col] = abs_earning
        row[sold_col] = abs_earning
        row['liabilities'] = liabilities_sign * abs_earning
        return row

    def _calculate_totals(self, options, subtotal_line, exercise_result_line, previous_years_unallocated_earnings):
        parts = [subtotal_line, exercise_result_line]
        if previous_years_unallocated_earnings:
            parts.append(previous_years_unallocated_earnings)
        column_expression_labels = [col['expression_label'] for col in options['columns']]
        return OrderedDict([(col, sum([part.get(col, 0) for part in parts])) for col in column_expression_labels])
