# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import models, fields, _
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
            'components': {
                'AccountReportLineName': 'account_reports.AgedPartnerBalanceLineName',
            },
        }

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        if report.user_has_groups('base.group_multi_currency'):
            options['multi_currency'] = True
        else:
            options['columns'] = [
                column for column in options['columns']
                if column['expression_label'] not in {'amount_currency', 'currency'}
            ]

        default_order_column = {
            'expression_label': 'invoice_date',
            'direction': 'ASC',
        }

        options['order_column'] = (previous_options or {}).get('order_column') or default_order_column

    def _custom_line_postprocessor(self, report, options, lines, warnings=None):
        partner_lines_map = {}

        # Sort line dicts by partner
        for line in lines:
            model, model_id = report._get_model_info_from_id(line['id'])
            if model == 'res.partner':
                partner_lines_map[model_id] = line

        if partner_lines_map:
            # Query trust for the required partners
            self._cr.execute("""
                SELECT res_id, value_text
                FROM ir_property
                WHERE res_id IN %s
                AND name = 'trust'
                AND company_id IN %s
            """, [
                tuple(f"res.partner,{partner_id}" for partner_id in partner_lines_map),
                tuple(report.get_report_company_ids(options)),
            ])

            trust_map = {}
            for res_id_str, trust in self._cr.fetchall():
                partner_id = int(res_id_str.split(',')[1])
                trust_map[partner_id] = trust

            # Set the trust key into the line dicts
            for partner_id, line_dict in partner_lines_map.items():
                line_dict['trust'] = trust_map.get(partner_id, 'normal')

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

        date_to = fields.Date.from_string(options['date']['date_to'])
        periods = [
            (False, fields.Date.to_string(date_to)),
            (minus_days(date_to, 1), minus_days(date_to, 30)),
            (minus_days(date_to, 31), minus_days(date_to, 60)),
            (minus_days(date_to, 61), minus_days(date_to, 90)),
            (minus_days(date_to, 91), minus_days(date_to, 120)),
            (minus_days(date_to, 121), False),
        ]

        def build_result_dict(report, query_res_lines):
            rslt = {f'period{i}': 0 for i in range(len(periods))}

            for query_res in query_res_lines:
                for i in range(len(periods)):
                    period_key = f'period{i}'
                    rslt[period_key] += query_res[period_key]

            if current_groupby == 'id':
                query_res = query_res_lines[0] # We're grouping by id, so there is only 1 element in query_res_lines anyway
                currency = self.env['res.currency'].browse(query_res['currency_id'][0]) if len(query_res['currency_id']) == 1 else None
                expected_date = len(query_res['expected_date']) == 1 and query_res['expected_date'][0] or len(query_res['due_date']) == 1 and query_res['due_date'][0]
                rslt.update({
                    'invoice_date': query_res['invoice_date'][0] if len(query_res['invoice_date']) == 1 else None,
                    'due_date': query_res['due_date'][0] if len(query_res['due_date']) == 1 else None,
                    'amount_currency': query_res['amount_currency'],
                    'currency_id': query_res['currency_id'][0] if len(query_res['currency_id']) == 1 else None,
                    'currency': currency.display_name if currency else None,
                    'account_name': query_res['account_name'][0] if len(query_res['account_name']) == 1 else None,
                    'expected_date': expected_date or None,
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
                    'expected_date': None,
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
        period_table = self.env.cr.mogrify(period_table_format, params).decode(self.env.cr.connection.encoding)

        # Build query
        tables, where_clause, where_params = report._query_get(options, 'strict_range', domain=[('account_id.account_type', '=', internal_type)])

        currency_table = report._get_query_currency_table(options)
        always_present_groupby = "period_table.period_index, currency_table.rate, currency_table.precision"
        if current_groupby:
            select_from_groupby = f"account_move_line.{current_groupby} AS grouping_key,"
            groupby_clause = f"account_move_line.{current_groupby}, {always_present_groupby}"
        else:
            select_from_groupby = ''
            groupby_clause = always_present_groupby
        select_period_query = ','.join(
            f"""
                CASE WHEN period_table.period_index = {i}
                THEN %s * (
                    SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision))
                    - COALESCE(SUM(ROUND(part_debit.amount * currency_table.rate, currency_table.precision)), 0)
                    + COALESCE(SUM(ROUND(part_credit.amount * currency_table.rate, currency_table.precision)), 0)
                )
                ELSE 0 END AS period{i}
            """
            for i in range(len(periods))
        )

        tail_query, tail_params = report._get_engine_query_tail(offset, limit)
        query = f"""
            WITH period_table(date_start, date_stop, period_index) AS ({period_table})

            SELECT
                {select_from_groupby}
                %s * (
                    SUM(account_move_line.amount_currency)
                    - COALESCE(SUM(part_debit.debit_amount_currency), 0)
                    + COALESCE(SUM(part_credit.credit_amount_currency), 0)
                ) AS amount_currency,
                ARRAY_AGG(DISTINCT account_move_line.partner_id) AS partner_id,
                ARRAY_AGG(account_move_line.payment_id) AS payment_id,
                ARRAY_AGG(DISTINCT move.invoice_date) AS invoice_date,
                ARRAY_AGG(DISTINCT COALESCE(account_move_line.date_maturity, account_move_line.date)) AS report_date,
                ARRAY_AGG(DISTINCT account_move_line.expected_pay_date) AS expected_date,
                ARRAY_AGG(DISTINCT account.code) AS account_name,
                ARRAY_AGG(DISTINCT COALESCE(account_move_line.date_maturity, account_move_line.date)) AS due_date,
                ARRAY_AGG(DISTINCT account_move_line.currency_id) AS currency_id,
                COUNT(account_move_line.id) AS aml_count,
                ARRAY_AGG(account.code) AS account_code,
                {select_period_query}

            FROM {tables}

            JOIN account_journal journal ON journal.id = account_move_line.journal_id
            JOIN account_account account ON account.id = account_move_line.account_id
            JOIN account_move move ON move.id = account_move_line.move_id
            JOIN {currency_table} ON currency_table.company_id = account_move_line.company_id

            LEFT JOIN LATERAL (
                SELECT
                    SUM(part.amount) AS amount,
                    SUM(part.debit_amount_currency) AS debit_amount_currency,
                    part.debit_move_id
                FROM account_partial_reconcile part
                WHERE part.max_date <= %s AND part.debit_move_id = account_move_line.id
                GROUP BY part.debit_move_id
            ) part_debit ON TRUE

            LEFT JOIN LATERAL (
                SELECT
                    SUM(part.amount) AS amount,
                    SUM(part.credit_amount_currency) AS credit_amount_currency,
                    part.credit_move_id
                FROM account_partial_reconcile part
                WHERE part.max_date <= %s AND part.credit_move_id = account_move_line.id
                GROUP BY part.credit_move_id
            ) part_credit ON TRUE

            JOIN period_table ON
                (
                    period_table.date_start IS NULL
                    OR COALESCE(account_move_line.date_maturity, account_move_line.date) <= DATE(period_table.date_start)
                )
                AND
                (
                    period_table.date_stop IS NULL
                    OR COALESCE(account_move_line.date_maturity, account_move_line.date) >= DATE(period_table.date_stop)
                )

            WHERE {where_clause}

            GROUP BY {groupby_clause}

            HAVING
                (
                    SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))
                    - COALESCE(SUM(ROUND(part_debit.amount * currency_table.rate, currency_table.precision)), 0)
                ) != 0
                OR
                (
                    SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))
                    - COALESCE(SUM(ROUND(part_credit.amount * currency_table.rate, currency_table.precision)), 0)
                ) != 0
            {tail_query}
        """

        multiplicator = -1 if internal_type == 'liability_payable' else 1
        params = [
            multiplicator,
            *([multiplicator] * len(periods)),
            date_to,
            date_to,
            *where_params,
            *tail_params,
        ]
        self._cr.execute(query, params)
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
            'expected_date': None,
            'total': 0,
        }

    def change_expected_date(self, options, params=None):
        aml_id = self.env['account.report']._get_res_id_from_line_id(params['line_id'], 'account.move.line')
        aml = self.env['account.move.line'].browse(aml_id)

        old_date = format_date(self.env, aml.expected_pay_date) if aml.expected_pay_date else _('any')
        aml.write({'expected_pay_date': params['expected_pay_date']})

        if aml.move_id.move_type == 'out_invoice':
            new_date = format_date(self.env, aml.expected_pay_date) if aml.expected_pay_date else _('any')
            move_msg = _('Expected payment date for journal item %r has been changed from %s to %s on journal entry %r', aml.name, old_date, new_date, aml.move_id.name)
            aml.partner_id._message_log(body=move_msg)
            aml.move_id._message_log(body=move_msg)

    def aged_partner_balance_audit(self, options, params, journal_type):
        """ Open a list of invoices/bills and/or deferral entries for the clicked cell
        :param dict options: the report's `options`
        :param dict params:  a dict containing:
                                 `calling_line_dict_id`: line id containing the optional account of the cell
                                 `expression_label`: the expression label of the cell
        """
        report = self.env['account.report'].browse(options['report_id'])
        action = self.env['ir.actions.actions']._for_xml_id('account.action_open_payment_items')
        journal_type_to_exclude = {'purchase': 'sale', 'sale': 'purchase'}
        if options:
            domain = [
                ('account_id.reconcile', '=', True),
                ('journal_id.type', '!=', journal_type_to_exclude.get(journal_type)),
                *self._build_domain_from_period(options, params['expression_label']),
                *report._get_options_domain(options, 'normal'),
                *report._get_audit_line_groupby_domain(params['calling_line_dict_id']),
            ]
            action['domain'] = domain
        return action

    def _build_domain_from_period(self, options, period):
        if period != "total" and period[-1].isdigit():
            period_number = int(period[-1])
            if period_number == 0:
                domain = [('date_maturity', '>=', options['date']['date_to'])]
            else:
                options_date_to = datetime.datetime.strptime(options['date']['date_to'], '%Y-%m-%d')
                period_end = options_date_to - datetime.timedelta(30*(period_number-1)+1)
                period_start = options_date_to - datetime.timedelta(30*(period_number))
                domain = [('date_maturity', '>=', period_start), ('date_maturity', '<=', period_end)]
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
