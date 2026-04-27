from odoo import api, fields, models, _
from odoo.tools import SQL


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        if not options.get('l10n_co_reports_groupby_partner_id'):
            return super()._dynamic_lines_generator(report, options, all_column_groups_expression_totals, warnings)

        lines_groupby_account, total_line = self._l10n_co_reports_get_lines_group_by_account_and_partner(report, options)

        # Order lines by account code
        sorted_lines = [
            line
            for account_key in sorted(lines_groupby_account, key=lambda account: account.code)
            for line in lines_groupby_account[account_key]
        ]
        sorted_lines.append(total_line)

        return [(0, line) for line in sorted_lines]

    def _l10n_co_reports_get_lines_group_by_account_and_partner(self, report, options):
        # Returns
        #   - A dict representing the lines that need to be added to the report, grouped by account
        #   - The final line with the total amounts
        # Note: All moves without partner are grouped into a single line at the end of each list

        def custom_sort_key(line):
            # Order lines alphabetically by partner name, with the parent line on top and the line without partner at the bottom
            custom_partner_id = line['l10n_co_partner_id']
            custom_partner_id = 0 if custom_partner_id else 1
            return not line['is_parent'], custom_partner_id, line['l10n_co_partner_name']

        lines_groupby_account = {}
        for (account, partner_id), column_group_results in self._l10n_co_reports_query_values(report, options):
            eval_dict = {}
            partner_name = ''
            partner_vat = ''
            for column_group_key, results in column_group_results.items():
                account_sum = results.get('sum', {})
                account_un_earn = results.get('unaffected_earnings', {})

                if not partner_name:
                    partner_name = account_sum.get('partner_name', '') or account_un_earn.get('partner_name', '')

                if not partner_vat:
                    partner_vat = account_sum.get('partner_vat', '') or account_un_earn.get('partner_vat', '')

                eval_dict[column_group_key] = {
                    'amount_currency': account_sum.get('amount_currency', 0.0) + account_un_earn.get('amount_currency', 0.0),
                    'debit': account_sum.get('debit', 0.0) + account_un_earn.get('debit', 0.0),
                    'credit': account_sum.get('credit', 0.0) + account_un_earn.get('credit', 0.0),
                    'balance': account_sum.get('balance', 0.0) + account_un_earn.get('balance', 0.0),
                }

            lines_groupby_account.setdefault(account, []).append(
                self._l10n_co_reports_get_account_title_line(report, options, account, partner_id, partner_name, partner_vat, eval_dict)
            )

        for account, partner_lines in lines_groupby_account.items():
            parent_line_col_values = [
                sum(partner_line['columns'][i]['no_format'] or 0.0 for partner_line in partner_lines if partner_line['columns'][i]['expression_label'] not in ('partner_vat', 'partner_name'))
                for i in range(len(options['columns']))
            ]

            parent_line = self._l10n_co_reports_get_empty_parent_line(report, options, account, parent_line_col_values)
            parent_line['id'] = report._get_generic_line_id('account.account', account.id)

            for partner_line in partner_lines:
                partner_line['parent_id'] = parent_line['id']

            partner_lines.append(parent_line)
            partner_lines.sort(key=custom_sort_key)

        total_line = self._l10n_co_reports_get_total_line(report, options)

        return lines_groupby_account, total_line

    @api.model
    def _l10n_co_reports_get_empty_parent_line(self, report, options, account, parent_line_col_values):
        line_columns = []
        for i, column in enumerate(options['columns']):
            if column['expression_label'] == 'partner_name':
                line_columns.append(report._build_column_dict(
                    '',
                    column,
                    options=options,
                ))
                continue
            if column['expression_label'] == 'partner_vat':
                line_columns.append(report._build_column_dict(
                    '',
                    column,
                    options=options,
                ))
                continue

            col_value = parent_line_col_values[i]
            col_expr_label = column['expression_label']

            line_columns.append(report._build_column_dict(
                col_value,
                column,
                options=options,
                currency=account.currency_id if col_expr_label == 'amount_currency' else None,
            ))

        return {
            'name': f'{account.code} {account.name}',
            'search_key': account.code,
            'columns': line_columns,
            'level': 1,
            'unfoldable': False,
            'unfolded': False,
            'l10n_co_partner_name': '',
            'l10n_co_partner_id': '',
            'is_parent': True,
        }

    @api.model
    def _l10n_co_reports_get_account_title_line(self, report, options, account, partner_id, partner_name, partner_vat, eval_dict):
        line_columns = []
        for column in options['columns']:
            if column['expression_label'] == 'partner_name':
                line_columns.append(report._build_column_dict(
                    partner_name if partner_id else _('(None)'),
                    column,
                    options=options,
                ))
                continue
            if column['expression_label'] == 'partner_vat':
                line_columns.append(report._build_column_dict(
                    partner_vat,
                    column,
                    options=options,
                ))
                continue

            col_value = eval_dict.get(column['column_group_key'], {}).get(column['expression_label'])
            col_expr_label = column['expression_label']
            col_value = 0.0 if col_value is None or (col_expr_label == 'amount_currency' and not account.currency_id) else col_value

            line_columns.append(report._build_column_dict(
                col_value,
                column,
                options=options,
                currency=account.currency_id if col_expr_label == 'amount_currency' else None,
            ))

        line_id = report._get_generic_line_id('res.partner', partner_id, markup='account_id:' + str(account.id))
        return {
            'id': line_id,
            'name': f'{account.code} {account.name}',
            'search_key': account.code,
            'columns': line_columns,
            'level': 3,
            'unfoldable': False,
            'unfolded': False,
            'l10n_co_partner_name': partner_name,
            'l10n_co_partner_id': partner_id,
            'is_parent': False,
        }

    @api.model
    def _l10n_co_reports_get_total_line(self, report, options):
        total_line_columns = []
        for i, column in enumerate(options['columns']):
            total_line_columns.append(report._build_column_dict(
                '' if column['expression_label'] in ('partner_name', 'partner_vat') else 0.0,
                column,
                options=options,
            ))

        return {
            'id': report._get_generic_line_id(None, None, markup='total'),
            'name': _('Total'),
            'class': 'total',
            'level': 1,
            'columns': total_line_columns,
        }

    def _l10n_co_reports_query_values(self, report, options):
        accounts_partners_keys = set()
        accounts_partners_map = {}
        companies_map = {}

        aml_query, aml_params = self._l10n_co_reports_get_query_amls(report, options)
        self._cr.execute(aml_query, aml_params)

        for res in self._cr.dictfetchall():
            column_group_key = res['column_group_key']
            key = res['key']
            partner_id = res['partner_id']
            res['partner_vat'] = res['partner_vat'] or ''

            if key == 'sum':
                if res['account_type'] == 'equity_unaffected':
                    partner_id = None  # Remove partner details for unaffected earnings
                    res['partner_vat'] = ''

                account_id = res['groupby']
                groupby_key = (account_id, partner_id)
                accounts_partners_keys.add(groupby_key)
                accounts_partners_map.setdefault(groupby_key, {col_group_key: {} for col_group_key in options['column_groups']})
                accounts_partners_map[groupby_key][column_group_key][key] = res

            elif key == 'unaffected_earnings':
                company_id = res['groupby']
                companies_map.setdefault(company_id, {col_group_key: {} for col_group_key in options['column_groups']})
                companies_map[company_id][column_group_key] = res

        # Converts the unaffected earnings of the query to the proper unaffected account of the company.
        # The subgroup per partner no longer applies for unaffected earnings
        if companies_map:
            unaffected_accounts = self.env['account.account'].search([
                ('account_type', '=', 'equity_unaffected'),
                ('company_ids', 'in', list(companies_map.keys())),
            ])
            company_unaffected_account_map = {}
            for account in unaffected_accounts:
                for company in account.company_ids:
                    company_unaffected_account_map[company.id] = account

            for company_id, company_data in companies_map.items():
                account = company_unaffected_account_map[company_id]
                groupby_key = (account.id, None)  # Use None instead of partner_id
                accounts_partners_map.setdefault(groupby_key, {col_group_key: {} for col_group_key in options['column_groups']})
                for column_group_key in options['column_groups']:
                    if 'unaffected_earnings' not in accounts_partners_map[groupby_key][column_group_key]:
                        accounts_partners_map[groupby_key][column_group_key]['unaffected_earnings'] = companies_map[company_id][column_group_key]
                accounts_partners_keys.add(groupby_key)

        account_partner_keys = {(self.env['account.account'].browse(account_id), partner_id) for account_id, partner_id in accounts_partners_keys}
        return [(account_partner_key, accounts_partners_map[account_partner_key[0].id, account_partner_key[1]]) for account_partner_key in account_partner_keys]

    def _l10n_co_reports_get_query_amls(self, report, options):
        options_by_column_group = report._split_options_per_column_group(options)
        queries = []

        # ===============================================================
        # 1) Get sums for all (accounts, partners) existing combinations
        # ===============================================================
        for column_group_key, options_group in options_by_column_group.items():
            # Sum is computed including the initial balance of the accounts configured to do so, unless a special option key is used
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

            # Exclude move lines with P&L accounts from initial balance if they belong to a previous fiscal year
            if options_group.get('include_current_year_in_unaff_earnings'):
                query_domain += [('account_id.include_initial_balance', '=', True)]

            query = report._get_report_query(options_group, sum_date_scope, domain=query_domain)
            queries.append(SQL(
                '''
                    SELECT
                        account.id                                              AS groupby,
                        account.account_type                                    AS account_type,
                        partner.id                                              AS partner_id,
                        'sum'                                                   AS key,
                        MAX(account_move_line.date)                             AS max_date,
                        %(column_group_key)s                                    AS column_group_key,
                        COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                        SUM(%(debit_select)s)                                   AS debit,
                        SUM(%(credit_select)s)                                  AS credit,
                        SUM(%(balance_select)s)                                 AS balance,
                        partner.name                                            AS partner_name,
                        partner.vat                                             AS partner_vat
                    FROM %(table_references)s
                    LEFT JOIN res_company company               ON company.id = account_move_line.company_id
                    LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
                    LEFT JOIN account_account account           ON account.id = account_move_line.account_id
                    LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
                    LEFT JOIN account_full_reconcile full_rec   ON full_rec.id = account_move_line.full_reconcile_id
                    %(currency_table_join)s
                    WHERE %(search_condition)s
                    GROUP BY account.id, partner.id
                ''',
                table_references=query.from_clause,
                search_condition=query.where_clause,
                column_group_key=column_group_key,
                debit_select=report._currency_table_apply_rate(SQL("account_move_line.debit")),
                credit_select=report._currency_table_apply_rate(SQL("account_move_line.credit")),
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                currency_table_join=report._currency_table_aml_join(options_group),
            ))

            # ============================================
            # 2) Unaffected earnings.
            # ============================================
            if not options_group.get('general_ledger_strict_range'):
                # Apply to initial balance and end balance and only focus on unaffected earnings

                unaff_earnings_domain = [('account_id.include_initial_balance', '=', False)]

                # The period domain is expressed as:
                # [
                #   ('date' <= fiscalyear['date_from'] - 1),
                #   ('account_id.include_initial_balance', '=', False),
                # ]

                new_options = self._get_options_unaffected_earnings(options_group)
                query = report._get_report_query(new_options, 'strict_range', domain=unaff_earnings_domain)
                queries.append(SQL(
                    '''
                        SELECT
                            company.id                                              AS groupby,
                            NULL                                                    AS account_type,
                            NULL                                                    AS partner_id,
                            'unaffected_earnings'                                   AS key,
                            NULL                                                    AS max_date,
                            %(column_group_key)s                                    AS column_group_key,
                            COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                            SUM(%(debit_select)s)                                   AS debit,
                            SUM(%(credit_select)s)                                  AS credit,
                            SUM(%(balance_select)s)                                 AS balance,
                            NULL                                                    AS partner_name,
                            NULL                                                    AS partner_vat
                        FROM %(table_references)s
                        LEFT JOIN res_company company               ON company.id = account_move_line.company_id
                        LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
                        LEFT JOIN account_account account           ON account.id = account_move_line.account_id
                        LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
                        LEFT JOIN account_full_reconcile full_rec   ON full_rec.id = account_move_line.full_reconcile_id
                        %(currency_table_join)s
                        WHERE %(search_condition)s
                        GROUP BY company.id
                    ''',
                    table_references=query.from_clause,
                    search_condition=query.where_clause,
                    column_group_key=column_group_key,
                    debit_select=report._currency_table_apply_rate(SQL("account_move_line.debit")),
                    credit_select=report._currency_table_apply_rate(SQL("account_move_line.credit")),
                    balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                    currency_table_join=report._currency_table_aml_join(options_group),
                ))

        return SQL(" UNION ALL ").join(queries)
