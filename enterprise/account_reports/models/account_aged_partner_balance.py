# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import models, fields, _
from odoo.tools import SQL
from odoo.tools.misc import format_date

from dateutil.relativedelta import relativedelta
from itertools import chain


class AgedPartnerBalanceCustomHandler(models.AbstractModel):
    _name = 'account.aged.partner.balance.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Aged Partner Balance Custom Handler'

    def _get_custom_display_config(self):
        return {
            'css_custom_class': 'aged_partner_balance',
            'templates': {
                'AccountReportLineName': 'account_reports.AgedPartnerBalanceLineName',
            },
            'components': {
                'AccountReportFilters': 'account_reports.AgedPartnerBalanceFilters',
            },
        }

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        hidden_columns = set()

        options['multi_currency'] = report.env.user.has_group('base.group_multi_currency')
        options['show_currency'] = options['multi_currency'] and (previous_options or {}).get('show_currency', False)
        options['no_xlsx_currency_code_columns'] = True
        if not options['show_currency']:
            hidden_columns.update(['amount_currency', 'currency'])

        options['show_account'] = (previous_options or {}).get('show_account', False)
        if not options['show_account']:
            hidden_columns.add('account_name')

        options['columns'] = [
            column for column in options['columns']
            if column['expression_label'] not in hidden_columns
        ]

        default_order_column = {
            'expression_label': 'invoice_date',
            'direction': 'ASC',
        }

        options['order_column'] = previous_options.get('order_column') or default_order_column
        options['aging_based_on'] = previous_options.get('aging_based_on') or 'base_on_maturity_date'
        options['aging_interval'] = previous_options.get('aging_interval') or 30

        # Set aging column names
        interval = options['aging_interval']
        for column in options['columns']:
            if column['expression_label'].startswith('period'):
                period_number = int(column['expression_label'].replace('period', '')) - 1
                if 0 <= period_number < 4:
                    column['name'] = f'{interval * period_number + 1}-{interval * (period_number + 1)}'

    def _custom_line_postprocessor(self, report, options, lines):
        partner_lines_map = {}

        # Sort line dicts by partner
        for line in lines:
            model, model_id = report._get_model_info_from_id(line['id'])
            if model == 'res.partner':
                partner_lines_map[model_id] = line

        if partner_lines_map:
            for partner, line_dict in zip(
                    self.env['res.partner'].browse(partner_lines_map),
                    partner_lines_map.values()
            ):
                line_dict['trust'] = partner.with_company(partner.company_id or self.env.company).trust

        return lines

    def _report_custom_engine_aged_receivable(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._aged_partner_report_custom_engine_common(options, 'asset_receivable', current_groupby, next_groupby, offset=offset, limit=limit)

    def _report_custom_engine_aged_payable(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._aged_partner_report_custom_engine_common(options, 'liability_payable', current_groupby, next_groupby, offset=offset, limit=limit)

    def _aged_partner_report_custom_engine_common(self, options, internal_type, current_groupby, next_groupby, offset=0, limit=None):
        report = self.env['account.report'].browse(options['report_id'])
        report._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        def minus_days(date_obj, days):
            return fields.Date.to_string(date_obj - relativedelta(days=days))

        aging_date_field = SQL.identifier('invoice_date') if options['aging_based_on'] == 'base_on_invoice_date' else SQL.identifier('date_maturity')
        date_to = fields.Date.from_string(options['date']['date_to'])
        interval = options['aging_interval']
        periods = [(False, fields.Date.to_string(date_to))]
        # Since we added the first period in the list we have to do one less iteration
        nb_periods = len([column for column in options['columns'] if column['expression_label'].startswith('period')]) - 1
        for i in range(nb_periods):
            start_date = minus_days(date_to, (interval * i) + 1)
            # The last element of the list will have False for the end date
            end_date = minus_days(date_to, interval * (i + 1)) if i < nb_periods - 1 else False
            periods.append((start_date, end_date))

        def build_result_dict(report, query_res_lines):
            rslt = {f'period{i}': 0 for i in range(len(periods))}

            for query_res in query_res_lines:
                for i in range(len(periods)):
                    period_key = f'period{i}'
                    rslt[period_key] += query_res[period_key]

            if current_groupby == 'id':
                query_res = query_res_lines[0] # We're grouping by id, so there is only 1 element in query_res_lines anyway
                currency = self.env['res.currency'].browse(query_res['currency_id'][0]) if len(query_res['currency_id']) == 1 else None
                rslt.update({
                    'invoice_date': query_res['invoice_date'][0] if len(query_res['invoice_date']) == 1 else None,
                    'due_date': query_res['due_date'][0] if len(query_res['due_date']) == 1 else None,
                    'amount_currency': query_res['amount_currency'],
                    'currency_id': query_res['currency_id'][0] if len(query_res['currency_id']) == 1 else None,
                    'currency': currency.display_name if currency else None,
                    'account_name': query_res['account_name'][0] if len(query_res['account_name']) == 1 else None,
                    'total': None,
                    'has_sublines': query_res['aml_count'] > 0,

                    # Needed by the custom_unfold_all_batch_data_generator, to speed-up unfold_all
                    'partner_id': query_res['partner_id'][0] if query_res['partner_id'] else None,
                })
            else:
                rslt.update({
                    'invoice_date': None,
                    'due_date': None,
                    'amount_currency': None,
                    'currency_id': None,
                    'currency': None,
                    'account_name': None,
                    'total': sum(rslt[f'period{i}'] for i in range(len(periods))),
                    'has_sublines': False,
                })

            return rslt

        # Build period table
        period_table_format = ('(VALUES %s)' % ','.join("(%s, %s, %s)" for period in periods))
        params = list(chain.from_iterable(
            (period[0] or None, period[1] or None, i)
            for i, period in enumerate(periods)
        ))
        period_table = SQL(period_table_format, *params)

        # Build query
        query = report._get_report_query(options, 'strict_range', domain=[('account_id.account_type', '=', internal_type)])
        account_alias = query.left_join(lhs_alias='account_move_line', lhs_column='account_id', rhs_table='account_account', rhs_column='id', link='account_id')
        account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)

        always_present_groupby = SQL("period_table.period_index")
        if current_groupby:
            groupby_field_sql = self.env['account.move.line']._field_to_sql("account_move_line", current_groupby, query)
            select_from_groupby = SQL("%s AS grouping_key,", groupby_field_sql)
            groupby_clause = SQL("%s, %s", groupby_field_sql, always_present_groupby)
        else:
            select_from_groupby = SQL()
            groupby_clause = always_present_groupby
        multiplicator = -1 if internal_type == 'liability_payable' else 1
        select_period_query = SQL(',').join(
            SQL("""
                CASE WHEN period_table.period_index = %(period_index)s
                THEN %(multiplicator)s * SUM(%(balance_select)s)
                ELSE 0 END AS %(column_name)s
                """,
                period_index=i,
                multiplicator=multiplicator,
                column_name=SQL.identifier(f"period{i}"),
                balance_select=report._currency_table_apply_rate(SQL(
                    "account_move_line.balance - COALESCE(part_debit.amount, 0) + COALESCE(part_credit.amount, 0)"
                )),
            )
            for i in range(len(periods))
        )

        tail_query = report._get_engine_query_tail(offset, limit)
        query = SQL(
            """
            WITH period_table(date_start, date_stop, period_index) AS (%(period_table)s)

            SELECT
                %(select_from_groupby)s
                %(multiplicator)s * (
                    SUM(account_move_line.amount_currency)
                    - COALESCE(SUM(part_debit.debit_amount_currency), 0)
                    + COALESCE(SUM(part_credit.credit_amount_currency), 0)
                ) AS amount_currency,
                ARRAY_AGG(DISTINCT account_move_line.partner_id) AS partner_id,
                ARRAY_AGG(account_move_line.payment_id) AS payment_id,
                ARRAY_AGG(DISTINCT account_move_line.invoice_date) AS invoice_date,
                ARRAY_AGG(DISTINCT COALESCE(account_move_line.%(aging_date_field)s, account_move_line.date)) AS report_date,
                ARRAY_AGG(DISTINCT %(account_code)s) AS account_name,
                ARRAY_AGG(DISTINCT COALESCE(account_move_line.%(aging_date_field)s, account_move_line.date)) AS due_date,
                ARRAY_AGG(DISTINCT account_move_line.currency_id) AS currency_id,
                COUNT(account_move_line.id) AS aml_count,
                ARRAY_AGG(%(account_code)s) AS account_code,
                %(select_period_query)s

            FROM %(table_references)s

            JOIN account_journal journal ON journal.id = account_move_line.journal_id
            %(currency_table_join)s

            LEFT JOIN LATERAL (
                SELECT
                    SUM(part.amount) AS amount,
                    SUM(part.debit_amount_currency) AS debit_amount_currency,
                    part.debit_move_id
                FROM account_partial_reconcile part
                WHERE part.max_date <= %(date_to)s AND part.debit_move_id = account_move_line.id
                GROUP BY part.debit_move_id
            ) part_debit ON TRUE

            LEFT JOIN LATERAL (
                SELECT
                    SUM(part.amount) AS amount,
                    SUM(part.credit_amount_currency) AS credit_amount_currency,
                    part.credit_move_id
                FROM account_partial_reconcile part
                WHERE part.max_date <= %(date_to)s AND part.credit_move_id = account_move_line.id
                GROUP BY part.credit_move_id
            ) part_credit ON TRUE

            JOIN period_table ON
                (
                    period_table.date_start IS NULL
                    OR COALESCE(account_move_line.%(aging_date_field)s, account_move_line.date) <= DATE(period_table.date_start)
                )
                AND
                (
                    period_table.date_stop IS NULL
                    OR COALESCE(account_move_line.%(aging_date_field)s, account_move_line.date) >= DATE(period_table.date_stop)
                )

            WHERE %(search_condition)s

            GROUP BY %(groupby_clause)s

            HAVING
                ROUND(SUM(%(having_debit)s), %(currency_precision)s) != 0
                OR ROUND(SUM(%(having_credit)s), %(currency_precision)s) != 0

            ORDER BY %(groupby_clause)s

            %(tail_query)s
            """,
            account_code=account_code,
            period_table=period_table,
            select_from_groupby=select_from_groupby,
            select_period_query=select_period_query,
            multiplicator=multiplicator,
            aging_date_field=aging_date_field,
            table_references=query.from_clause,
            currency_table_join=report._currency_table_aml_join(options),
            date_to=date_to,
            search_condition=query.where_clause,
            groupby_clause=groupby_clause,
            having_debit=report._currency_table_apply_rate(SQL("CASE WHEN account_move_line.balance > 0  THEN account_move_line.balance else 0 END - COALESCE(part_debit.amount, 0)")),
            having_credit=report._currency_table_apply_rate(SQL("CASE WHEN account_move_line.balance < 0  THEN -account_move_line.balance else 0 END - COALESCE(part_credit.amount, 0)")),
            currency_precision=self.env.company.currency_id.decimal_places,
            tail_query=tail_query,
        )

        self._cr.execute(query)
        query_res_lines = self._cr.dictfetchall()

        if not current_groupby:
            return build_result_dict(report, query_res_lines)
        else:
            rslt = []

            all_res_per_grouping_key = {}
            for query_res in query_res_lines:
                grouping_key = query_res['grouping_key']
                all_res_per_grouping_key.setdefault(grouping_key, []).append(query_res)

            for grouping_key, query_res_lines in all_res_per_grouping_key.items():
                rslt.append((grouping_key, build_result_dict(report, query_res_lines)))

            return rslt

    def open_journal_items(self, options, params):
        params['view_ref'] = 'account.view_move_line_tree_grouped_partner'
        options_for_audit = {**options, 'date': {**options['date'], 'date_from': None}}
        report = self.env['account.report'].browse(options['report_id'])
        action = report.open_journal_items(options=options_for_audit, params=params)
        action.get('context', {}).update({'search_default_group_by_account': 0, 'search_default_group_by_partner': 1})
        return action

    def open_customer_statement(self, options, params):
        report = self.env['account.report'].browse(options['report_id'])
        record_model, record_id = report._get_model_info_from_id(params.get('line_id'))
        if self.env.ref('account_reports.customer_statement_report', raise_if_not_found=False):
            return self.env[record_model].browse(record_id).open_customer_statement()
        return self.env[record_model].browse(record_id).open_partner_ledger()

    def _common_custom_unfold_all_batch_data_generator(self, internal_type, report, options, lines_to_expand_by_function):
        rslt = {} # In the form {full_sub_groupby_key: all_column_group_expression_totals for this groupby computation}
        report_periods = 6 # The report has 6 periods

        for expand_function_name, lines_to_expand in lines_to_expand_by_function.items():
            for line_to_expand in lines_to_expand: # In standard, this loop will execute only once
                if expand_function_name == '_report_expand_unfoldable_line_with_groupby':
                    report_line_id = report._get_res_id_from_line_id(line_to_expand['id'], 'account.report.line')
                    expressions_to_evaluate = report.line_ids.expression_ids.filtered(lambda x: x.report_line_id.id == report_line_id and x.engine == 'custom')

                    if not expressions_to_evaluate:
                        continue

                    for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
                        # Get all aml results by partner
                        aml_data_by_partner = {}
                        for aml_id, aml_result in self._aged_partner_report_custom_engine_common(column_group_options, internal_type, 'id', None):
                            aml_result['aml_id'] = aml_id
                            aml_data_by_partner.setdefault(aml_result['partner_id'], []).append(aml_result)

                        # Iterate on results by partner to generate the content of the column group
                        partner_expression_totals = rslt.setdefault(f"[{report_line_id}]=>partner_id", {})\
                                                        .setdefault(column_group_key, {expression: {'value': []} for expression in expressions_to_evaluate})
                        for partner_id, aml_data_list in aml_data_by_partner.items():
                            partner_values = self._prepare_partner_values()
                            for i in range(report_periods):
                                partner_values[f'period{i}'] = 0

                            # Build expression totals under the right key
                            partner_aml_expression_totals = rslt.setdefault(f"[{report_line_id}]partner_id:{partner_id}=>id", {})\
                                                                .setdefault(column_group_key, {expression: {'value': []} for expression in expressions_to_evaluate})
                            for aml_data in aml_data_list:
                                for i in range(report_periods):
                                    period_value = aml_data[f'period{i}']
                                    partner_values[f'period{i}'] += period_value
                                    partner_values['total'] += period_value

                                for expression in expressions_to_evaluate:
                                    partner_aml_expression_totals[expression]['value'].append(
                                        (aml_data['aml_id'], aml_data[expression.subformula])
                                    )

                            for expression in expressions_to_evaluate:
                                partner_expression_totals[expression]['value'].append(
                                    (partner_id, partner_values[expression.subformula])
                                )

        return rslt

    def _prepare_partner_values(self):
        return {
            'invoice_date': None,
            'due_date': None,
            'amount_currency': None,
            'currency_id': None,
            'currency': None,
            'account_name': None,
            'total': 0,
        }

    def aged_partner_balance_audit(self, options, params, journal_type):
        """ Open a list of invoices/bills and/or deferral entries for the clicked cell
        :param dict options: the report's `options`
        :param dict params:  a dict containing:
                                 `calling_line_dict_id`: line id containing the optional account of the cell
                                 `expression_label`: the expression label of the cell
        """
        report = self.env['account.report'].browse(options['report_id'])
        action = self.env['ir.actions.actions']._for_xml_id('account.action_amounts_to_settle')
        journal_type_to_exclude = {'purchase': 'sale', 'sale': 'purchase'}
        if options:
            domain = [
                ('account_id.reconcile', '=', True),
                ('journal_id.type', '!=', journal_type_to_exclude.get(journal_type)),
                *self._build_domain_from_period(options, params['expression_label']),
                *report._get_options_domain(options, 'from_beginning'),
                *report._get_audit_line_groupby_domain(params['calling_line_dict_id']),
            ]
            action['domain'] = domain
        return action

    def _build_domain_from_period(self, options, period):
        if period != "total" and period[-1].isdigit():
            period_number = int(period[-1])
            if period_number == 0:
                domain = [
                    '|',
                    ('date_maturity', '>=', options['date']['date_to']),
                    '&', ('date_maturity', '=', False), ('date', '>=', options['date']['date_to']),
                ]
            else:
                options_date_to = datetime.datetime.strptime(options['date']['date_to'], '%Y-%m-%d')
                period_end = options_date_to - datetime.timedelta(30*(period_number-1)+1)
                period_start = options_date_to - datetime.timedelta(30*(period_number))
                domain = [
                        '|',
                        '&', ('date_maturity', '>=', period_start), ('date_maturity', '<=', period_end),
                        '&', '&', ('date_maturity', '=', False), ('date', '>=', period_start), ('date', '<=', period_end),
                    ]
                if period_number == 5:
                    domain = [
                        '|',
                        ('date_maturity', '<=', period_end),
                        '&', ('date_maturity', '=', False), ('date', '<=', period_end),
                    ]
        else:
            domain = []
        return domain

class AgedPayableCustomHandler(models.AbstractModel):
    _name = 'account.aged.payable.report.handler'
    _inherit = 'account.aged.partner.balance.report.handler'
    _description = 'Aged Payable Custom Handler'

    def open_journal_items(self, options, params):
        payable_account_type = {'id': 'trade_payable', 'name': _("Payable"), 'selected': True}

        if 'account_type' in options:
            options['account_type'].append(payable_account_type)
        else:
            options['account_type'] = [payable_account_type]

        return super().open_journal_items(options, params)

    def _custom_unfold_all_batch_data_generator(self, report, options, lines_to_expand_by_function):
        # We only optimize the unfold all if the groupby value of the report has not been customized. Else, we'll just run the full computation
        if self.env.ref('account_reports.aged_payable_line').groupby.replace(' ', '') == 'partner_id,id':
            return self._common_custom_unfold_all_batch_data_generator('liability_payable', report, options, lines_to_expand_by_function)
        return {}

    def action_audit_cell(self, options, params):
        return super().aged_partner_balance_audit(options, params, 'purchase')

class AgedReceivableCustomHandler(models.AbstractModel):
    _name = 'account.aged.receivable.report.handler'
    _inherit = 'account.aged.partner.balance.report.handler'
    _description = 'Aged Receivable Custom Handler'

    def open_journal_items(self, options, params):
        receivable_account_type = {'id': 'trade_receivable', 'name': _("Receivable"), 'selected': True}

        if 'account_type' in options:
            options['account_type'].append(receivable_account_type)
        else:
            options['account_type'] = [receivable_account_type]

        return super().open_journal_items(options, params)

    def _custom_unfold_all_batch_data_generator(self, report, options, lines_to_expand_by_function):
        # We only optimize the unfold all if the groupby value of the report has not been customized. Else, we'll just run the full computation
        if self.env.ref('account_reports.aged_receivable_line').groupby.replace(' ', '') == 'partner_id,id':
            return self._common_custom_unfold_all_batch_data_generator('asset_receivable', report, options, lines_to_expand_by_function)
        return {}

    def action_audit_cell(self, options, params):
        return super().aged_partner_balance_audit(options, params, 'sale')
