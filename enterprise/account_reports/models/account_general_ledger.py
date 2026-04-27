# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import csv
import io
import json

from odoo import models, fields, api, _
from odoo.tools.misc import format_date
from odoo.tools import float_repr, SQL
from odoo.exceptions import UserError

from datetime import timedelta
from collections import defaultdict


class GeneralLedgerCustomHandler(models.AbstractModel):
    _name = 'account.general.ledger.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'General Ledger Custom Handler'

    def _get_custom_display_config(self):
        return {
            'templates': {
                'AccountReportLineName': 'account_reports.GeneralLedgerLineName',
            },
        }

    def _custom_options_initializer(self, report, options, previous_options):
        options['buttons'].append({
            'name': _("CSV"),
            'sequence': 50,
            'action': 'export_file',
            'action_param': 'generate_csv_export',
            'file_export_type': _('CSV'),
        })

        # Remove multi-currency columns if needed
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        if self.env.user.has_group('base.group_multi_currency'):
            options['multi_currency'] = True
        else:
            options['columns'] = [
                column for column in options['columns']
                if column['expression_label'] != 'amount_currency'
            ]

        # Automatically unfold the report when printing it, unless some specific lines have been unfolded
        options['unfold_all'] = (options['export_mode'] == 'print' and not options.get('unfolded_lines')) or options['unfold_all']

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        lines = []
        date_from = fields.Date.from_string(options['date']['date_from'])
        company_currency = self.env.company.currency_id

        totals_by_column_group = defaultdict(lambda: {'debit': 0, 'credit': 0, 'balance': 0})
        for account, column_group_results in self._query_values(report, options):
            eval_dict = {}
            has_lines = False
            for column_group_key, results in column_group_results.items():
                account_sum = results.get('sum', {})
                account_un_earn = results.get('unaffected_earnings', {})

                account_debit = account_sum.get('debit', 0.0) + account_un_earn.get('debit', 0.0)
                account_credit = account_sum.get('credit', 0.0) + account_un_earn.get('credit', 0.0)
                account_balance = account_sum.get('balance', 0.0) + account_un_earn.get('balance', 0.0)

                eval_dict[column_group_key] = {
                    'amount_currency': account_sum.get('amount_currency', 0.0) + account_un_earn.get('amount_currency', 0.0),
                    'debit': account_debit,
                    'credit': account_credit,
                    'balance': account_balance,
                }

                max_date = account_sum.get('max_date')
                has_lines = has_lines or (max_date and max_date >= date_from)

                totals_by_column_group[column_group_key]['debit'] += account_debit
                totals_by_column_group[column_group_key]['credit'] += account_credit
                totals_by_column_group[column_group_key]['balance'] += account_balance

            lines.append(self._get_account_title_line(report, options, account, has_lines, eval_dict))

        # Report total line.
        for totals in totals_by_column_group.values():
            totals['balance'] = company_currency.round(totals['balance'])

        # Tax Declaration lines.
        journal_options = report._get_options_journals(options)
        if len(options['column_groups']) == 1 and len(journal_options) == 1 and journal_options[0]['type'] in ('sale', 'purchase'):
            lines += self._tax_declaration_lines(report, options, journal_options[0]['type'])

        # Total line
        lines.append(self._get_total_line(report, options, totals_by_column_group))

        return [(0, line) for line in lines]

    def _custom_unfold_all_batch_data_generator(self, report, options, lines_to_expand_by_function):
        account_ids_to_expand = []
        for line_dict in lines_to_expand_by_function.get('_report_expand_unfoldable_line_general_ledger', []):
            model, model_id = report._get_model_info_from_id(line_dict['id'])
            if model == 'account.account':
                account_ids_to_expand.append(model_id)

        limit_to_load = report.load_more_limit if report.load_more_limit and not options.get('export_mode') else None
        has_more_per_account_id = {}

        unlimited_aml_results_per_account_id = self._get_aml_values(report, options, account_ids_to_expand)[0]
        if limit_to_load:
            # Apply the load_more_limit.
            # load_more_limit cannot be passed to the call to _get_aml_values, otherwise it won't be applied per account but on the whole result.
            # We gain perf from batching, but load every result ; then we need to filter them.

            aml_results_per_account_id = {}
            for account_id, account_aml_results in unlimited_aml_results_per_account_id.items():
                account_values = {}
                for key, value in account_aml_results.items():
                    if len(account_values) == limit_to_load:
                        has_more_per_account_id[account_id] = True
                        break
                    account_values[key] = value
                aml_results_per_account_id[account_id] = account_values
        else:
            aml_results_per_account_id = unlimited_aml_results_per_account_id

        return {
            'initial_balances': self._get_initial_balance_values(report, account_ids_to_expand, options),
            'aml_results': aml_results_per_account_id,
            'has_more': has_more_per_account_id,
        }

    def _tax_declaration_lines(self, report, options, tax_type):
        labels_replacement = {
            'debit': _("Base Amount"),
            'credit': _("Tax Amount"),
        }

        rslt = [{
            'id': report._get_generic_line_id(None, None, markup='tax_decl_header_1'),
            'name': _('Tax Declaration'),
            'columns': [{} for column in options['columns']],
            'level': 1,
            'unfoldable': False,
            'unfolded': False,
        }, {
            'id': report._get_generic_line_id(None, None, markup='tax_decl_header_2'),
            'name': _('Name'),
            'columns': [{'name': labels_replacement.get(col['expression_label'], '')} for col in options['columns']],
            'level': 3,
            'unfoldable': False,
            'unfolded': False,
        }]

        # Call the generic tax report
        generic_tax_report = self.env.ref('account.generic_tax_report')
        tax_report_options = generic_tax_report.get_options({**options, 'selected_variant_id': generic_tax_report.id, 'forced_domain': [('tax_line_id.type_tax_use', '=', tax_type)]})
        tax_report_lines = generic_tax_report._get_lines(tax_report_options)
        tax_type_parent_line_id = generic_tax_report._get_generic_line_id(None, None, markup=tax_type)

        for tax_report_line in tax_report_lines:
            if tax_report_line.get('parent_id') == tax_type_parent_line_id:
                original_columns = tax_report_line['columns']
                row_column_map = {
                    'debit': original_columns[0],
                    'credit': original_columns[1],
                }

                tax_report_line['columns'] = [row_column_map.get(col['expression_label'], {}) for col in options['columns']]
                rslt.append(tax_report_line)

        return rslt

    def _query_values(self, report, options):
        """ Executes the queries, and performs all the computations.

        :return:    [(record, values_by_column_group), ...],  where
                    - record is an account.account record.
                    - values_by_column_group is a dict in the form {column_group_key: values, ...}
                        - column_group_key is a string identifying a column group, as in options['column_groups']
                        - values is a list of dictionaries, one per period containing:
                            - sum:                              {'debit': float, 'credit': float, 'balance': float}
                            - (optional) initial_balance:       {'debit': float, 'credit': float, 'balance': float}
                            - (optional) unaffected_earnings:   {'debit': float, 'credit': float, 'balance': float}
        """
        # Execute the queries and dispatch the results.
        query = self._get_query_sums(report, options)

        if not query:
            return []

        groupby_accounts = {}
        groupby_companies = {}

        for res in self.env.execute_query_dict(query):
            # No result to aggregate.
            if res['groupby'] is None:
                continue

            column_group_key = res['column_group_key']
            key = res['key']
            if key == 'sum':
                groupby_accounts.setdefault(res['groupby'], {col_group_key: {} for col_group_key in options['column_groups']})
                groupby_accounts[res['groupby']][column_group_key][key] = res

            elif key == 'initial_balance':
                groupby_accounts.setdefault(res['groupby'], {col_group_key: {} for col_group_key in options['column_groups']})
                groupby_accounts[res['groupby']][column_group_key][key] = res

            elif key == 'unaffected_earnings':
                groupby_companies.setdefault(res['groupby'], {col_group_key: {} for col_group_key in options['column_groups']})
                groupby_companies[res['groupby']][column_group_key] = res

        # Affect the unaffected earnings to the first fetched account of type 'account.data_unaffected_earnings'.
        # It's less costly to fetch all candidate accounts in a single search and then iterate it.
        if groupby_companies:
            unaffected_earnings_accounts = self.env['account.account'].search([
                ('display_name', 'ilike', options.get('filter_search_bar')),
                *self.env['account.account']._check_company_domain(list(groupby_companies.keys())),
                ('account_type', '=', 'equity_unaffected'),
            ])
            for company_id, groupby_company in groupby_companies.items():
                if equity_unaffected_account := unaffected_earnings_accounts.filtered(lambda a: self.env['res.company'].browse(company_id).root_id in a.company_ids):
                    for column_group_key in options['column_groups']:
                        groupby_accounts.setdefault(
                            equity_unaffected_account.id,
                            {col_group_key: {'unaffected_earnings': {}} for col_group_key in options['column_groups']},
                        )
                        if unaffected_earnings := groupby_company.get(column_group_key):
                            if groupby_accounts[equity_unaffected_account.id][column_group_key].get('unaffected_earnings'):
                                for key in ['amount_currency', 'debit', 'credit', 'balance']:
                                    groupby_accounts[equity_unaffected_account.id][column_group_key]['unaffected_earnings'][key] += unaffected_earnings[key]
                            else:
                                groupby_accounts[equity_unaffected_account.id][column_group_key]['unaffected_earnings'] = unaffected_earnings

        # Retrieve the accounts to browse.
        # groupby_accounts.keys() contains all account ids affected by:
        # - the amls in the current period.
        # - the amls affecting the initial balance.
        # - the unaffected earnings allocation.
        # Note a search is done instead of a browse to preserve the table ordering.
        if groupby_accounts:
            accounts = self.env['account.account'].search([('id', 'in', list(groupby_accounts.keys()))])
        else:
            accounts = []

        return [(account, groupby_accounts[account.id]) for account in accounts]

    def _get_query_sums(self, report, options) -> SQL:
        """ Construct a query retrieving all the aggregated sums to build the report. It includes:
        - sums for all accounts.
        - sums for the initial balances.
        - sums for the unaffected earnings.
        - sums for the tax declaration.
        :return:                    query as SQL object
        """
        options_by_column_group = report._split_options_per_column_group(options)

        queries = []

        # ============================================
        # 1) Get sums for all accounts.
        # ============================================
        for column_group_key, options_group in options_by_column_group.items():

            # Sum is computed including the initial balance of the accounts configured to do so, unless a special option key is used
            # (this is required for trial balance, which is based on general ledger)
            sum_date_scope = 'strict_range' if options_group.get('general_ledger_strict_range') else 'from_beginning'

            query_domain = []

            if not options_group.get('general_ledger_strict_range'):
                date_from = fields.Date.from_string(options_group['date']['date_from'])
                current_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date_from)
                query_domain += [
                    '|',
                    ('date', '>=', current_fiscalyear_dates['date_from']),
                    ('account_id.include_initial_balance', '=', True),
                ]

            if options_group.get('export_mode') == 'print' and options_group.get('filter_search_bar'):
                if options_group.get('hierarchy'):
                    query_domain += [
                        '|',
                        ('account_id', 'ilike', options_group['filter_search_bar']),
                        ('account_id.id', 'in', SQL(
                            """
                            /*
                            JOIN clause: Check if the account_group include the account_account
                            A group from 10 to 10 include every account with code that begin with 10.
                            If there is an account with a length of 6, it should be included if it's in the range from 100 000 to 109 999 included

                            Where clause: Check if the account_group matches the filter
                            */
                            (SELECT distinct account_account.id
                            FROM account_account
                            LEFT JOIN account_group ON
                                (
                                    LEFT(account_account.code_store->> '%(company_id)s', LENGTH(code_prefix_start)) BETWEEN
                                        code_prefix_start
                                    AND code_prefix_end
                                )
                            WHERE ( account_group.name->> %(lang)s  ILIKE %(filter_search_bar)s
                                OR  account_group.code_prefix_start ILIKE %(filter_search_bar)s)
                            )""",
                            lang=self.env.lang,
                            company_id=self.env.company.id,
                            filter_search_bar="%" + options_group['filter_search_bar'] + "%")),
                    ]
                else:
                    query_domain.append(('account_id', 'ilike', options_group['filter_search_bar']))

            if options_group.get('include_current_year_in_unaff_earnings'):
                query_domain += [('account_id.include_initial_balance', '=', True)]

            query = report._get_report_query(options_group, sum_date_scope, domain=query_domain)
            queries.append(SQL(
                """
                SELECT
                    account_move_line.account_id                            AS groupby,
                    'sum'                                                   AS key,
                    MAX(account_move_line.date)                             AS max_date,
                    %(column_group_key)s                                    AS column_group_key,
                    COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                    SUM(%(debit_select)s)   AS debit,
                    SUM(%(credit_select)s)  AS credit,
                    SUM(%(balance_select)s) AS balance
                FROM %(table_references)s
                %(currency_table_join)s
                WHERE %(search_condition)s
                GROUP BY account_move_line.account_id
                """,
                column_group_key=column_group_key,
                table_references=query.from_clause,
                debit_select=report._currency_table_apply_rate(SQL("account_move_line.debit")),
                credit_select=report._currency_table_apply_rate(SQL("account_move_line.credit")),
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                currency_table_join=report._currency_table_aml_join(options_group),
                search_condition=query.where_clause,
            ))

            # ============================================
            # 2) Get sums for the unaffected earnings.
            # ============================================
            if not options_group.get('general_ledger_strict_range'):
                unaff_earnings_domain = [('account_id.include_initial_balance', '=', False)]

                # The period domain is expressed as:
                # [
                #   ('date' <= fiscalyear['date_from'] - 1),
                #   ('account_id.include_initial_balance', '=', False),
                # ]

                new_options = self._get_options_unaffected_earnings(options_group)
                query = report._get_report_query(new_options, 'strict_range', domain=unaff_earnings_domain)
                queries.append(SQL(
                    """
                    SELECT
                        account_move_line.company_id                            AS groupby,
                        'unaffected_earnings'                                   AS key,
                        NULL                                                    AS max_date,
                        %(column_group_key)s                                    AS column_group_key,
                        COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                        SUM(%(debit_select)s)                                   AS debit,
                        SUM(%(credit_select)s)                                  AS credit,
                        SUM(%(balance_select)s) AS balance
                    FROM %(table_references)s
                    %(currency_table_join)s
                    WHERE %(search_condition)s
                    GROUP BY account_move_line.company_id
                    """,
                    column_group_key=column_group_key,
                    table_references=query.from_clause,
                    debit_select=report._currency_table_apply_rate(SQL("account_move_line.debit")),
                    credit_select=report._currency_table_apply_rate(SQL("account_move_line.credit")),
                    balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                    currency_table_join=report._currency_table_aml_join(options_group),
                    search_condition=query.where_clause,
                ))

        return SQL(" UNION ALL ").join(queries)

    def _get_options_unaffected_earnings(self, options):
        ''' Create options used to compute the unaffected earnings.
        The unaffected earnings are the amount of benefits/loss that have not been allocated to
        another account in the previous fiscal years.
        The resulting dates domain will be:
        [
          ('date' <= fiscalyear['date_from'] - 1),
          ('account_id.include_initial_balance', '=', False),
        ]
        :param options: The report options.
        :return:        A copy of the options.
        '''
        new_options = options.copy()
        new_options.pop('filter_search_bar', None)
        fiscalyear_dates = self.env.company.compute_fiscalyear_dates(fields.Date.from_string(options['date']['date_from']))

        # Trial balance uses the options key, general ledger does not
        new_date_to = fields.Date.from_string(new_options['date']['date_to']) if options.get('include_current_year_in_unaff_earnings') else fiscalyear_dates['date_from'] - timedelta(days=1)

        new_options['date'] = self.env['account.report']._get_dates_period(None, new_date_to, 'single')

        return new_options

    def _get_aml_values(self, report, options, expanded_account_ids, offset=0, limit=None):
        rslt = {account_id: {} for account_id in expanded_account_ids}
        aml_query = self._get_query_amls(report, options, expanded_account_ids, offset=offset, limit=limit)
        self._cr.execute(aml_query)
        aml_results_number = 0
        has_more = False
        for aml_result in self._cr.dictfetchall():
            aml_results_number += 1
            if aml_results_number == limit:
                has_more = True
                break

            # For asset_receivable the name will already contains the ref with the _compute_name
            if aml_result['ref'] and aml_result['account_type'] != 'asset_receivable':
                aml_result['communication'] = f"{aml_result['ref']} - {aml_result['name']}"
            else:
                aml_result['communication'] = aml_result['name']

            # The same aml can return multiple results when using account_report_cash_basis module, if the receivable/payable
            # is reconciled with multiple payments. In this case, the date shown for the move lines actually corresponds to the
            # reconciliation date. In order to keep distinct lines in this case, we include date in the grouping key.
            aml_key = (aml_result['id'], aml_result['date'])

            account_result = rslt[aml_result['account_id']]
            if not aml_key in account_result:
                account_result[aml_key] = {col_group_key: {} for col_group_key in options['column_groups']}

            account_result[aml_key][aml_result['column_group_key']] = aml_result

        return rslt, has_more

    def _get_query_amls(self, report, options, expanded_account_ids, offset=0, limit=None, order_by_account_code=False) -> SQL:
        """ Construct a query retrieving the account.move.lines when expanding a report line with or without the load
        more.
        :param options:               The report options.
        :param expanded_account_ids:  The account.account ids corresponding to consider. If None, match every account.
        :param offset:                The offset of the query (used by the load more).
        :param limit:                 The limit of the query (used by the load more).
        :return:                      (query, params)
        """
        additional_domain = [('account_id', 'in', expanded_account_ids)] if expanded_account_ids is not None else None
        queries = []
        journal_name = self.env['account.journal']._field_to_sql('journal', 'name')
        for column_group_key, group_options in report._split_options_per_column_group(options).items():
            # Get sums for the account move lines.
            # period: [('date' <= options['date_to']), ('date', '>=', options['date_from'])]
            query = report._get_report_query(group_options, domain=additional_domain, date_scope='strict_range')
            account_alias = query.left_join(lhs_alias='account_move_line', lhs_column='account_id', rhs_table='account_account', rhs_column='id', link='account_id')
            account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)
            account_name = self.env['account.account']._field_to_sql(account_alias, 'name')
            account_type = self.env['account.account']._field_to_sql(account_alias, 'account_type')
            if order_by_account_code:
                order_account_by_accounts = self.env['account.account']._order_to_sql(self.env['account.account']._order, query, account_alias)
            query = SQL(
                '''
                SELECT
                    account_move_line.id,
                    account_move_line.date,
                    MIN(account_move_line.date_maturity)    AS date_maturity,
                    MIN(account_move_line.name)             AS name,
                    MIN(account_move_line.ref)              AS ref,
                    MIN(account_move_line.company_id)       AS company_id,
                    MIN(account_move_line.account_id)       AS account_id,
                    MIN(account_move_line.payment_id)       AS payment_id,
                    MIN(account_move_line.partner_id)       AS partner_id,
                    MIN(account_move_line.currency_id)      AS currency_id,
                    SUM(account_move_line.amount_currency)  AS amount_currency,
                    MIN(COALESCE(account_move_line.invoice_date, account_move_line.date))                 AS invoice_date,
                    account_move_line.date                                                                AS date,
                    SUM(%(debit_select)s)                   AS debit,
                    SUM(%(credit_select)s)                  AS credit,
                    SUM(%(balance_select)s)                 AS balance,
                    MIN(move.name)                          AS move_name,
                    MIN(company.currency_id)                AS company_currency_id,
                    MIN(partner.name)                       AS partner_name,
                    MIN(move.move_type)                     AS move_type,
                    MIN(%(account_code)s)                   AS account_code,
                    MIN(%(account_name)s)                   AS account_name,
                    MIN(%(account_type)s)                   AS account_type,
                    MIN(journal.code)                       AS journal_code,
                    MIN(%(journal_name)s)                   AS journal_name,
                    MIN(full_rec.id)                        AS full_rec_name,
                    %(column_group_key)s                    AS column_group_key
                FROM %(table_references)s
                JOIN account_move move                      ON move.id = account_move_line.move_id
                %(currency_table_join)s
                LEFT JOIN res_company company               ON company.id = account_move_line.company_id
                LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
                LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
                LEFT JOIN account_full_reconcile full_rec   ON full_rec.id = account_move_line.full_reconcile_id
                WHERE %(search_condition)s
                GROUP BY %(additional_order_groupby)s account_move_line.id, account_move_line.date
                ORDER BY %(additional_order_groupby)s account_move_line.date, move_name, account_move_line.id
                ''',
                account_code=account_code,
                account_name=account_name,
                account_type=account_type,
                journal_name=journal_name,
                column_group_key=column_group_key,
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(group_options),
                debit_select=report._currency_table_apply_rate(SQL("account_move_line.debit")),
                credit_select=report._currency_table_apply_rate(SQL("account_move_line.credit")),
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                search_condition=query.where_clause,
                additional_order_groupby=SQL('%s,', order_account_by_accounts) if order_by_account_code else SQL('')
            )
            queries.append(query)

        full_query = SQL(" UNION ALL ").join(SQL("(%s)", query) for query in queries)

        if offset:
            full_query = SQL('%s OFFSET %s ', full_query, offset)
        if limit:
            full_query = SQL('%s LIMIT %s ', full_query, limit)

        return full_query

    def _get_initial_balance_values(self, report, account_ids, options):
        """
        Get sums for the initial balance.
        """
        queries = []
        for column_group_key, options_group in report._split_options_per_column_group(options).items():
            new_options = self._get_options_initial_balance(options_group)
            domain = [
                ('account_id', 'in', account_ids),
            ]
            if not new_options.get('general_ledger_strict_range'):
                domain += [
                    '|',
                    ('date', '>=', new_options['date']['date_from']),
                    ('account_id.include_initial_balance', '=', True),
                ]
            if new_options.get('include_current_year_in_unaff_earnings'):
                domain += [('account_id.include_initial_balance', '=', True)]
            query = report._get_report_query(new_options, 'from_beginning', domain=domain)
            queries.append(SQL(
                """
                SELECT
                    account_move_line.account_id                          AS groupby,
                    'initial_balance'                                     AS key,
                    NULL                                                  AS max_date,
                    %(column_group_key)s                                  AS column_group_key,
                    COALESCE(SUM(account_move_line.amount_currency), 0.0) AS amount_currency,
                    SUM(%(debit_select)s)                                 AS debit,
                    SUM(%(credit_select)s)                                AS credit,
                    SUM(%(balance_select)s)                               AS balance
                FROM %(table_references)s
                %(currency_table_join)s
                WHERE %(search_condition)s
                GROUP BY account_move_line.account_id
                """,
                column_group_key=column_group_key,
                table_references=query.from_clause,
                debit_select=report._currency_table_apply_rate(SQL("account_move_line.debit")),
                credit_select=report._currency_table_apply_rate(SQL("account_move_line.credit")),
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                currency_table_join=report._currency_table_aml_join(options_group),
                search_condition=query.where_clause,
            ))

        self._cr.execute(SQL(" UNION ALL ").join(queries))

        init_balance_by_col_group = {
            account_id: {column_group_key: {} for column_group_key in options['column_groups']}
            for account_id in account_ids
        }
        for result in self._cr.dictfetchall():
            init_balance_by_col_group[result['groupby']][result['column_group_key']] = result

        accounts = self.env['account.account'].browse(account_ids)
        return {
            account.id: (account, init_balance_by_col_group[account.id])
            for account in accounts
        }

    def _get_options_initial_balance(self, options):
        """ Create options used to compute the initial balances.
        The initial balances depict the current balance of the accounts at the beginning of
        the selected period in the report.
        The resulting dates domain will be:
        [
            ('date' <= options['date_from'] - 1),
            '|',
            ('date' >= fiscalyear['date_from']),
            ('account_id.include_initial_balance', '=', True)
        ]
        :param options: The report options.
        :return:        A copy of the options.
        """
        #pylint: disable=sql-injection
        new_options = options.copy()
        date_to = new_options['comparison']['periods'][-1]['date_from'] if new_options.get('comparison', {}).get('periods') else new_options['date']['date_from']
        new_date_to = fields.Date.from_string(date_to) - timedelta(days=1)

        # Date from computation
        # We have two case:
        # 1) We are choosing a date that starts at the beginning of a fiscal year and we want the initial period to be
        # the previous fiscal year
        # 2) We are choosing a date that starts in the middle of a fiscal year and in that case we want the initial period
        # to be the beginning of the fiscal year
        date_from = fields.Date.from_string(new_options['date']['date_from'])
        current_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date_from)

        if date_from == current_fiscalyear_dates['date_from']:
            # We want the previous fiscal year
            previous_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date_from - timedelta(days=1))
            new_date_from = previous_fiscalyear_dates['date_from']
            include_current_year_in_unaff_earnings = True
        else:
            # We want the current fiscal year
            new_date_from = current_fiscalyear_dates['date_from']
            include_current_year_in_unaff_earnings = False

        new_options['date'] = self.env['account.report']._get_dates_period(
            new_date_from,
            new_date_to,
            'range',
        )
        new_options['include_current_year_in_unaff_earnings'] = include_current_year_in_unaff_earnings

        return new_options

    ####################################################
    # COLUMN/LINE HELPERS
    ####################################################
    def _get_account_title_line(self, report, options, account, has_lines, eval_dict):
        line_columns = []
        for column in options['columns']:
            col_value = eval_dict.get(column['column_group_key'], {}).get(column['expression_label'])
            col_expr_label = column['expression_label']

            value = None if col_value is None or (col_expr_label == 'amount_currency' and not account.currency_id) else col_value

            line_columns.append(report._build_column_dict(
                value,
                column,
                options=options,
                currency=account.currency_id if col_expr_label == 'amount_currency' else None,
            ))

        line_id = report._get_generic_line_id('account.account', account.id)
        is_in_unfolded_lines = any(
            report._get_res_id_from_line_id(line_id, 'account.account') == account.id
            for line_id in options.get('unfolded_lines')
        )
        return {
            'id': line_id,
            'name': account.display_name,
            'columns': line_columns,
            'level': 1,
            'unfoldable': has_lines,
            'unfolded': has_lines and (is_in_unfolded_lines or options.get('unfold_all')),
            'expand_function': '_report_expand_unfoldable_line_general_ledger',
        }

    def _get_aml_line(self, report, parent_line_id, options, eval_dict, init_bal_by_col_group):
        line_columns = []
        for column in options['columns']:
            col_expr_label = column['expression_label']
            col_value = eval_dict[column['column_group_key']].get(col_expr_label)
            col_currency = None

            if col_value is not None:
                if col_expr_label == 'amount_currency':
                    col_currency = self.env['res.currency'].browse(eval_dict[column['column_group_key']]['currency_id'])
                    col_value = None if col_currency == self.env.company.currency_id else col_value
                elif col_expr_label == 'balance':
                    col_value += (init_bal_by_col_group[column['column_group_key']] or 0)

            line_columns.append(report._build_column_dict(
                col_value,
                column,
                options=options,
                currency=col_currency,
            ))

        aml_id = None
        move_name = None
        caret_type = None
        for column_group_dict in eval_dict.values():
            aml_id = column_group_dict.get('id', '')
            if aml_id:
                if column_group_dict.get('payment_id'):
                    caret_type = 'account.payment'
                else:
                    caret_type = 'account.move.line'
                move_name = column_group_dict['move_name']
                date = str(column_group_dict.get('date', ''))
                break

        return {
            'id': report._get_generic_line_id('account.move.line', aml_id, parent_line_id=parent_line_id, markup=date),
            'caret_options': caret_type,
            'parent_id': parent_line_id,
            'name': move_name or _('Draft Entry'),
            'columns': line_columns,
            'level': 3,
        }

    @api.model
    def _get_total_line(self, report, options, eval_dict):
        line_columns = []
        for column in options['columns']:
            col_value = eval_dict[column['column_group_key']].get(column['expression_label'])
            col_value = None if col_value is None else col_value

            line_columns.append(report._build_column_dict(col_value, column, options=options))

        return {
            'id': report._get_generic_line_id(None, None, markup='total'),
            'name': _('Total'),
            'level': 1,
            'columns': line_columns,
        }

    def caret_option_audit_tax(self, options, params):
        return self.env['account.generic.tax.report.handler'].caret_option_audit_tax(options, params)

    def _report_expand_unfoldable_line_general_ledger(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        def init_load_more_progress(line_dict):
            return {
                column['column_group_key']: line_col.get('no_format', 0)
                for column, line_col in  zip(options['columns'], line_dict['columns'])
                if column['expression_label'] == 'balance'
            }

        report = self.env.ref('account_reports.general_ledger_report')
        model, model_id = report._get_model_info_from_id(line_dict_id)

        if model != 'account.account':
            raise UserError(_("Wrong ID for general ledger line to expand: %s", line_dict_id))

        lines = []

        # Get initial balance
        if offset == 0:
            if unfold_all_batch_data:
                account, init_balance_by_col_group = unfold_all_batch_data['initial_balances'][model_id]
            else:
                account, init_balance_by_col_group = self._get_initial_balance_values(report, [model_id], options)[model_id]

            initial_balance_line = report._get_partner_and_general_ledger_initial_balance_line(options, line_dict_id, init_balance_by_col_group, account.currency_id)

            if initial_balance_line:
                lines.append(initial_balance_line)

                # For the first expansion of the line, the initial balance line gives the progress
                progress = init_load_more_progress(initial_balance_line)

        # Get move lines
        limit_to_load = report.load_more_limit + 1 if report.load_more_limit and options['export_mode'] != 'print' else None
        if unfold_all_batch_data:
            aml_results = unfold_all_batch_data['aml_results'][model_id]
            has_more = unfold_all_batch_data['has_more'].get(model_id, False)
        else:
            aml_results, has_more = self._get_aml_values(report, options, [model_id], offset=offset, limit=limit_to_load)
            aml_results = aml_results[model_id]

        next_progress = progress
        for aml_result in aml_results.values():
            new_line = self._get_aml_line(report, line_dict_id, options, aml_result, next_progress)
            lines.append(new_line)
            next_progress = init_load_more_progress(new_line)

        return {
            'lines': lines,
            'offset_increment': report.load_more_limit,
            'has_more': has_more,
            'progress': next_progress,
        }

    def generate_csv_export(self, options):
        if len(options['column_groups']) > 1:
            raise UserError(_("CSV export only works with one column group"))

        report = self.env['account.report'].browse(options['report_id'])
        return {
            'file_content': self._generate_csv_lazy_export(options),
            'file_type': 'csv',
            'file_name': report.get_default_report_filename(options, 'csv')
        }

    def _generate_csv_lazy_export(self, options):
        with self.pool.cursor() as new_cr:
            self.env.flush_all()
            handler = self.with_env(self.env(cr=new_cr))
            decimal_places_per_cur_id = {
                currency.id: currency.decimal_places
                for currency in handler.env['res.currency'].search([])
            }
            company_currency_id = handler.env.company.currency_id.id

            def csv_format_account_line(account_line):
                cells = list(handler.env['account.account']._split_code_name(account_line['name']))

                for col in account_line['columns']:
                    cell = col['name']
                    if col['figure_type'] == 'monetary' and isinstance(cell, float):
                        currency_id = col['currency'].id if col['currency'] else company_currency_id
                        cell = float_repr(cell, decimal_places_per_cur_id[currency_id])
                    cells.append(cell)

                return csv_format(cells)

            def csv_format_aml_res(aml_res):
                cells = [aml_res.get('move_name', '')]
                for col in options['columns']:
                    cell = aml_res.get(col['expression_label'], '')

                    if col['figure_type'] == 'monetary' and isinstance(cell, float):
                        if col['expression_label'] == 'amount_currency' and aml_res.get('currency_id'):
                            currency_id = aml_res['currency_id']
                            cell = float_repr(cell, decimal_places_per_cur_id[currency_id]) if currency_id != company_currency_id else ''
                        else:
                            cell = float_repr(cell, decimal_places_per_cur_id[company_currency_id])

                    cells.append(cell)
                return csv_format(cells, indent=1)

            def csv_format(cells, indent=0):
                with io.StringIO() as buf:
                    writer = csv.writer(buf, delimiter=',', lineterminator='\n')
                    writer.writerow([''] * indent + cells)
                    return buf.getvalue().encode()

            yield csv_format([_("Code"), _("Name")] + [col['name'] for col in options['columns']])
            report = handler.env['account.report'].browse(options['report_id'])
            agg_lines_options = options | {'export_mode': 'print', 'unfolded_lines': [], 'unfold_all': False}
            agg_lines = report.with_context(no_format=True)._get_lines(agg_lines_options)

            accounts = []
            account_lines = []
            for agg_line in agg_lines:
                line_id = agg_line['id']
                model, account_id = report._get_model_info_from_id(line_id)
                if model == 'account.account':
                    accounts.append(account_id)
                    account_lines.append(agg_line)

            initial_balances = handler._get_initial_balance_values(report, accounts, options)

            aml_query, aml_params = handler._get_query_amls(report, options, accounts, order_by_account_code=True)
            handler.env.cr.execute(aml_query, aml_params)
            account_id = None
            progress = 0
            initial_balance_vals = {}
            account_lines_iter = iter(account_lines)
            while aml_result := handler.env.cr.dictfetchone():
                while account_id is None or account_id != aml_result['account_id']:
                    account_line = next(account_lines_iter)
                    yield csv_format_account_line(account_line)
                    _model, account_id = report._get_model_info_from_id(account_line['id'])
                    if initial_balance_vals := next(iter(initial_balances.get(account_id)[1].values())):
                        progress = initial_balance_vals['balance']
                    else:
                        progress = 0

                if initial_balance_vals:
                    yield csv_format_aml_res(initial_balance_vals | {'move_name': _("Initial Balance")})
                    initial_balance_vals = {}
                if aml_result['ref']:
                    aml_result['communication'] = f"{aml_result['ref']} - {aml_result['name']}"
                else:
                    aml_result['communication'] = aml_result['name']
                progress = aml_result['balance'] = (progress + aml_result['balance'])
                yield csv_format_aml_res(aml_result)

            for account_line in account_lines_iter:
                yield csv_format_account_line(account_line)

            total_line = agg_lines[-1]
            yield csv_format_account_line(total_line)
