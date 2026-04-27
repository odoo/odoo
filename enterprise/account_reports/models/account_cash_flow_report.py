from odoo import models, _
from odoo.tools import SQL, Query


class CashFlowReportCustomHandler(models.AbstractModel):
    _name = 'account.cash.flow.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Cash Flow Report Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        # Compute the cash flow report using the direct method: https://www.investopedia.com/terms/d/direct_method.asp
        lines = []

        layout_data = self._get_layout_data()
        report_data = self._get_report_data(report, options, layout_data)

        for layout_line_id, layout_line_data in layout_data.items():
            lines.append((0, self._get_layout_line(report, options, layout_line_id, layout_line_data, report_data)))

            if layout_line_id in report_data and 'aml_groupby_account' in report_data[layout_line_id]:
                aml_data_values = report_data[layout_line_id]['aml_groupby_account'].values()

                aml_data_values_with_account_code = []
                aml_data_values_without_account_code = []

                for aml_data in aml_data_values:
                    if aml_data['account_code'] is not None:
                        aml_data_values_with_account_code.append(aml_data)
                    else:
                        aml_data_values_without_account_code.append(aml_data)

                for aml_data in (sorted(aml_data_values_with_account_code, key=lambda x: x['account_code'])
                                 + aml_data_values_without_account_code):
                    lines.append((0, self._get_aml_line(report, options, aml_data)))

        unexplained_difference_line = self._get_unexplained_difference_line(report, options, report_data)

        if unexplained_difference_line:
            lines.append((0, unexplained_difference_line))

        return lines

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        report._init_options_journals(options, previous_options=previous_options, additional_journals_domain=[('type', 'in', ('bank', 'cash', 'general'))])

    def _get_report_data(self, report, options, layout_data):
        report_data = {}

        payment_account_ids = self._get_account_ids(report, options)
        if not payment_account_ids:
            return report_data

        # Compute 'Cash and cash equivalents, beginning of period'
        for aml_data in self._compute_liquidity_balance(report, options, payment_account_ids, 'to_beginning_of_period'):
            self._add_report_data('opening_balance', aml_data, layout_data, report_data)
            self._add_report_data('closing_balance', aml_data, layout_data, report_data)

        # Compute 'Cash and cash equivalents, closing balance'
        for aml_data in self._compute_liquidity_balance(report, options, payment_account_ids, 'strict_range'):
            self._add_report_data('closing_balance', aml_data, layout_data, report_data)

        tags_ids = self._get_tags_ids()
        cashflow_tag_ids = self._get_cashflow_tag_ids()

        # Process liquidity moves
        for aml_groupby_account in self._get_liquidity_moves(report, options, payment_account_ids, cashflow_tag_ids):
            for aml_data in aml_groupby_account.values():
                self._dispatch_aml_data(tags_ids, aml_data, layout_data, report_data)

        # Process reconciled moves
        for aml_groupby_account in self._get_reconciled_moves(report, options, payment_account_ids, cashflow_tag_ids):
            for aml_data in aml_groupby_account.values():
                self._dispatch_aml_data(tags_ids, aml_data, layout_data, report_data)

        return report_data

    def _add_report_data(self, layout_line_id, aml_data, layout_data, report_data):
        """
        Add or update the report_data dictionnary with aml_data.

        report_data is a dictionnary where the keys are keys from _cash_flow_report_get_layout_data() (used for mapping)
        and the values can contain 2 dictionnaries:
            * (required) 'balance' where the key is the column_group_key and the value is the balance of the line
            * (optional) 'aml_groupby_account' where the key is an account_id and the values are the aml data
        """
        def _report_update_parent(layout_line_id, aml_column_group_key, aml_balance, layout_data, report_data):
            # Update the balance in report_data of the parent of the layout_line_id recursively (Stops when the line has no parent)
            if 'parent_line_id' in layout_data[layout_line_id]:
                parent_line_id = layout_data[layout_line_id]['parent_line_id']

                report_data.setdefault(parent_line_id, {'balance': {}})
                report_data[parent_line_id]['balance'].setdefault(aml_column_group_key, 0.0)
                report_data[parent_line_id]['balance'][aml_column_group_key] += aml_balance

                _report_update_parent(parent_line_id, aml_column_group_key, aml_balance, layout_data, report_data)

        aml_column_group_key = aml_data['column_group_key']
        aml_account_id = aml_data['account_id']
        aml_account_code = aml_data['account_code']
        aml_account_name = aml_data['account_name']
        aml_balance = aml_data['balance']
        aml_account_tag = aml_data.get('account_tag_id', None)

        if self.env.company.currency_id.is_zero(aml_balance):
            return

        report_data.setdefault(layout_line_id, {
            'balance': {},
            'aml_groupby_account': {},
        })

        report_data[layout_line_id]['aml_groupby_account'].setdefault(aml_account_id, {
            'parent_line_id': layout_line_id,
            'account_id': aml_account_id,
            'account_code': aml_account_code,
            'account_name': aml_account_name,
            'account_tag_id': aml_account_tag,
            'level': layout_data[layout_line_id]['level'] + 1,
            'balance': {},
        })

        report_data[layout_line_id]['balance'].setdefault(aml_column_group_key, 0.0)
        report_data[layout_line_id]['balance'][aml_column_group_key] += aml_balance

        report_data[layout_line_id]['aml_groupby_account'][aml_account_id]['balance'].setdefault(aml_column_group_key, 0.0)
        report_data[layout_line_id]['aml_groupby_account'][aml_account_id]['balance'][aml_column_group_key] += aml_balance

        _report_update_parent(layout_line_id, aml_column_group_key, aml_balance, layout_data, report_data)

    def _get_tags_ids(self):
        ''' Get a dict to pass on to _dispatch_aml_data containing information mapping account tags to report lines. '''
        return {
            'operating': self.env.ref('account.account_tag_operating').id,
            'investing': self.env.ref('account.account_tag_investing').id,
            'financing': self.env.ref('account.account_tag_financing').id,
        }

    def _get_cashflow_tag_ids(self):
        ''' Get the list of account tags that are relevant for the cash flow report. '''
        return self._get_tags_ids().values()

    def _dispatch_aml_data(self, tags_ids, aml_data, layout_data, report_data):
        # Dispatch the aml_data in the correct layout_line
        if aml_data['account_account_type'] == 'asset_receivable':
            self._add_report_data('advance_payments_customer', aml_data, layout_data, report_data)
        elif aml_data['account_account_type'] == 'liability_payable':
            self._add_report_data('advance_payments_suppliers', aml_data, layout_data, report_data)
        elif aml_data['balance'] < 0:
            if aml_data['account_tag_id'] == tags_ids['operating']:
                self._add_report_data('paid_operating_activities', aml_data, layout_data, report_data)
            elif aml_data['account_tag_id'] == tags_ids['investing']:
                self._add_report_data('investing_activities_cash_out', aml_data, layout_data, report_data)
            elif aml_data['account_tag_id'] == tags_ids['financing']:
                self._add_report_data('financing_activities_cash_out', aml_data, layout_data, report_data)
            else:
                self._add_report_data('unclassified_activities_cash_out', aml_data, layout_data, report_data)
        elif aml_data['balance'] > 0:
            if aml_data['account_tag_id'] == tags_ids['operating']:
                self._add_report_data('received_operating_activities', aml_data, layout_data, report_data)
            elif aml_data['account_tag_id'] == tags_ids['investing']:
                self._add_report_data('investing_activities_cash_in', aml_data, layout_data, report_data)
            elif aml_data['account_tag_id'] == tags_ids['financing']:
                self._add_report_data('financing_activities_cash_in', aml_data, layout_data, report_data)
            else:
                self._add_report_data('unclassified_activities_cash_in', aml_data, layout_data, report_data)

    # -------------------------------------------------------------------------
    # QUERIES
    # -------------------------------------------------------------------------
    def _get_account_ids(self, report, options):
        ''' Retrieve all accounts to be part of the cash flow statement and also the accounts making them.

        :param options: The report options.
        :return:        payment_account_ids: A tuple containing all account.account's ids being used in a liquidity journal.
        '''
        # Fetch liquidity accounts:
        # Accounts being used by at least one bank/cash journal.
        selected_journal_ids = [j['id'] for j in report._get_options_journals(options)]

        where_clause = "account_journal.id IN %s" if selected_journal_ids else "account_journal.type IN ('bank', 'cash', 'general')"
        where_params = [tuple(selected_journal_ids)] if selected_journal_ids else []

        self._cr.execute(f'''
            SELECT
                array_remove(ARRAY_AGG(DISTINCT account_account.id), NULL),
                array_remove(ARRAY_AGG(DISTINCT account_payment_method_line.payment_account_id), NULL)
            FROM account_journal
            JOIN res_company
                ON account_journal.company_id = res_company.id
            LEFT JOIN account_payment_method_line
                ON account_journal.id = account_payment_method_line.journal_id
            LEFT JOIN account_account
                ON account_journal.default_account_id = account_account.id
                   AND account_account.account_type IN ('asset_cash', 'liability_credit_card')
            WHERE {where_clause}
        ''', where_params)

        res = self._cr.fetchall()[0]
        payment_account_ids = set((res[0] or []) + (res[1] or []))

        if not payment_account_ids:
            return ()

        return tuple(payment_account_ids)

    def _get_move_ids_query(self, report, payment_account_ids, column_group_options) -> SQL:
        ''' Get all liquidity moves to be part of the cash flow statement.
        :param payment_account_ids: A tuple containing all account.account's ids being used in a liquidity journal.
        :return: query: The SQL query to retrieve the move IDs.
        '''

        query = report._get_report_query(column_group_options, 'strict_range', [('account_id', 'in', list(payment_account_ids))])
        return SQL(
            '''
            SELECT
                array_agg(DISTINCT account_move_line.move_id) AS move_id
            FROM %(table_references)s
            WHERE %(search_condition)s
            ''',
            table_references=query.from_clause,
            search_condition=query.where_clause,
        )

    def _compute_liquidity_balance(self, report, options, payment_account_ids, date_scope):
        ''' Compute the balance of all liquidity accounts to populate the following sections:
            'Cash and cash equivalents, beginning of period' and 'Cash and cash equivalents, closing balance'.

        :param options:                 The report options.
        :param payment_account_ids:     A tuple containing all account.account's ids being used in a liquidity journal.
        :return:                        A list of tuple (account_id, account_code, account_name, balance).
        '''
        queries = []

        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            query = report._get_report_query(column_group_options, date_scope, domain=[('account_id', 'in', payment_account_ids)])
            account_alias = query.join(lhs_alias='account_move_line', lhs_column='account_id', rhs_table='account_account', rhs_column='id', link='account_id')
            account_name = self.env['account.account']._field_to_sql(account_alias, 'name')
            account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)

            queries.append(SQL(
                '''
                SELECT
                    %(column_group_key)s AS column_group_key,
                    account_move_line.account_id,
                    %(account_code)s AS account_code,
                    %(account_name)s AS account_name,
                    SUM(%(balance_select)s) AS balance
                FROM %(table_references)s
                %(currency_table_join)s
                WHERE %(search_condition)s
                GROUP BY account_move_line.account_id, %(account_code)s, %(account_name)s
                ''',
                column_group_key=column_group_key,
                account_code=account_code,
                account_name=account_name,
                table_references=query.from_clause,
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                currency_table_join=report._currency_table_aml_join(column_group_options),
                search_condition=query.where_clause,
            ))

        self._cr.execute(SQL(' UNION ALL ').join(queries))

        return self._cr.dictfetchall()

    def _get_liquidity_moves(self, report, options, payment_account_ids, cash_flow_tag_ids):
        ''' Fetch all information needed to compute lines from liquidity moves.
        The difficulty is to represent only the not-reconciled part of balance.

        :param options:                 The report options.
        :param payment_account_ids:     A tuple containing all account.account's ids being used in a liquidity journal.
        :return:                        A list of tuple (account_id, account_code, account_name, account_type, amount).
        '''

        reconciled_aml_groupby_account = {}

        queries = []

        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            move_ids_query = self._get_move_ids_query(report, payment_account_ids, column_group_options)
            query = Query(self.env, 'account_move_line')
            account_alias = query.join(lhs_alias='account_move_line', lhs_column='account_id', rhs_table='account_account', rhs_column='id', link='account_id')
            account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)
            account_name = self.env['account.account']._field_to_sql(account_alias, 'name')
            account_type = SQL.identifier(account_alias, 'account_type')

            queries.append(SQL(
                '''
                (WITH payment_move_ids AS (%(move_ids_query)s)
                -- Credit amount of each account
                SELECT
                    %(column_group_key)s AS column_group_key,
                    account_move_line.account_id,
                    %(account_code)s AS account_code,
                    %(account_name)s AS account_name,
                    %(account_type)s AS account_account_type,
                    account_account_account_tag.account_account_tag_id AS account_tag_id,
                    SUM(%(partial_amount_select)s) AS balance
                FROM %(from_clause)s
                %(currency_table_join)s
                LEFT JOIN account_partial_reconcile
                    ON account_partial_reconcile.credit_move_id = account_move_line.id
                LEFT JOIN account_account_account_tag
                    ON account_account_account_tag.account_account_id = account_move_line.account_id
                    AND account_account_account_tag.account_account_tag_id IN %(cash_flow_tag_ids)s
                WHERE account_move_line.move_id IN (SELECT unnest(payment_move_ids.move_id) FROM payment_move_ids)
                    AND account_move_line.account_id NOT IN %(payment_account_ids)s
                    AND account_partial_reconcile.max_date BETWEEN %(date_from)s AND %(date_to)s
                GROUP BY account_move_line.company_id, account_move_line.account_id, %(account_code)s, %(account_name)s, account_account_type, account_account_account_tag.account_account_tag_id

                UNION ALL

                -- Debit amount of each account
                SELECT
                    %(column_group_key)s AS column_group_key,
                    account_move_line.account_id,
                    %(account_code)s AS account_code,
                    %(account_name)s AS account_name,
                    %(account_type)s AS account_account_type,
                    account_account_account_tag.account_account_tag_id AS account_tag_id,
                    -SUM(%(partial_amount_select)s) AS balance
                FROM %(from_clause)s
                %(currency_table_join)s
                LEFT JOIN account_partial_reconcile
                    ON account_partial_reconcile.debit_move_id = account_move_line.id
                LEFT JOIN account_account_account_tag
                    ON account_account_account_tag.account_account_id = account_move_line.account_id
                    AND account_account_account_tag.account_account_tag_id IN %(cash_flow_tag_ids)s
                WHERE account_move_line.move_id IN (SELECT unnest(payment_move_ids.move_id) FROM payment_move_ids)
                    AND account_move_line.account_id NOT IN %(payment_account_ids)s
                    AND account_partial_reconcile.max_date BETWEEN %(date_from)s AND %(date_to)s
                GROUP BY account_move_line.company_id, account_move_line.account_id, %(account_code)s, %(account_name)s, account_account_type, account_account_account_tag.account_account_tag_id

                UNION ALL

                -- Total amount of each account
                SELECT
                    %(column_group_key)s AS column_group_key,
                    account_move_line.account_id AS account_id,
                    %(account_code)s AS account_code,
                    %(account_name)s AS account_name,
                    %(account_type)s AS account_account_type,
                    account_account_account_tag.account_account_tag_id AS account_tag_id,
                    SUM(%(aml_balance_select)s) AS balance
                FROM %(from_clause)s
                %(currency_table_join)s
                LEFT JOIN account_account_account_tag
                    ON account_account_account_tag.account_account_id = account_move_line.account_id
                    AND account_account_account_tag.account_account_tag_id IN %(cash_flow_tag_ids)s
                WHERE account_move_line.move_id IN (SELECT unnest(payment_move_ids.move_id) FROM payment_move_ids)
                    AND account_move_line.account_id NOT IN %(payment_account_ids)s
                GROUP BY account_move_line.account_id, %(account_code)s, %(account_name)s, account_account_type, account_account_account_tag.account_account_tag_id)
                ''',
                column_group_key=column_group_key,
                move_ids_query=move_ids_query,
                account_code=account_code,
                account_name=account_name,
                account_type=account_type,
                from_clause=query.from_clause,
                currency_table_join=report._currency_table_aml_join(column_group_options),
                partial_amount_select=report._currency_table_apply_rate(SQL("account_partial_reconcile.amount")),
                aml_balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                cash_flow_tag_ids=tuple(cash_flow_tag_ids),
                payment_account_ids=payment_account_ids,
                date_from=column_group_options['date']['date_from'],
                date_to=column_group_options['date']['date_to'],
            ))

        self._cr.execute(SQL(' UNION ALL ').join(queries))

        for aml_data in self._cr.dictfetchall():
            reconciled_aml_groupby_account.setdefault(aml_data['account_id'], {})
            reconciled_aml_groupby_account[aml_data['account_id']].setdefault(aml_data['column_group_key'], {
                'column_group_key': aml_data['column_group_key'],
                'account_id': aml_data['account_id'],
                'account_code': aml_data['account_code'],
                'account_name': aml_data['account_name'],
                'account_account_type': aml_data['account_account_type'],
                'account_tag_id': aml_data['account_tag_id'],
                'balance': 0.0,
            })

            reconciled_aml_groupby_account[aml_data['account_id']][aml_data['column_group_key']]['balance'] -= aml_data['balance']

        return list(reconciled_aml_groupby_account.values())

    def _get_reconciled_moves(self, report, options, payment_account_ids, cash_flow_tag_ids):
        ''' Retrieve all moves being not a liquidity move to be shown in the cash flow statement.
        Each amount must be valued at the percentage of what is actually paid.
        E.g. An invoice of 1000 being paid at 50% must be valued at 500.

        :param options:                 The report options.
        :param payment_account_ids:     A tuple containing all account.account's ids being used in a liquidity journal.
        :return:                        A list of tuple (account_id, account_code, account_name, account_type, amount).
        '''

        reconciled_account_ids = {column_group_key: set() for column_group_key in options['column_groups']}
        reconciled_percentage_per_move = {column_group_key: {} for column_group_key in options['column_groups']}
        currency_table = report._get_currency_table(options)

        queries = []

        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            move_ids_query = self._get_move_ids_query(report, payment_account_ids, column_group_options)

            queries.append(SQL(
                '''
                (WITH payment_move_ids AS (%(move_ids_query)s)
                SELECT
                    %(column_group_key)s AS column_group_key,
                    debit_line.move_id,
                    debit_line.account_id,
                    SUM(%(partial_amount)s) AS balance
                FROM account_move_line AS credit_line
                LEFT JOIN account_partial_reconcile
                    ON account_partial_reconcile.credit_move_id = credit_line.id
                JOIN %(currency_table)s
                    ON account_currency_table.company_id = account_partial_reconcile.company_id
                    AND account_currency_table.rate_type = 'current' -- For payable/receivable accounts it'll always be 'current' anyway
                INNER JOIN account_move_line AS debit_line
                    ON debit_line.id = account_partial_reconcile.debit_move_id
                WHERE credit_line.move_id IN (SELECT unnest(payment_move_ids.move_id) FROM payment_move_ids)
                    AND credit_line.account_id NOT IN %(payment_account_ids)s
                    AND credit_line.credit > 0.0
                    AND debit_line.move_id NOT IN (SELECT unnest(payment_move_ids.move_id) FROM payment_move_ids)
                    AND account_partial_reconcile.max_date BETWEEN %(date_from)s AND %(date_to)s
                GROUP BY debit_line.move_id, debit_line.account_id

                UNION ALL

                SELECT
                    %(column_group_key)s AS column_group_key,
                    credit_line.move_id,
                    credit_line.account_id,
                    -SUM(%(partial_amount)s) AS balance
                FROM account_move_line AS debit_line
                LEFT JOIN account_partial_reconcile
                    ON account_partial_reconcile.debit_move_id = debit_line.id
                JOIN %(currency_table)s
                    ON account_currency_table.company_id = account_partial_reconcile.company_id
                    AND account_currency_table.rate_type = 'current' -- For payable/receivable accounts it'll always be 'current' anyway
                INNER JOIN account_move_line AS credit_line
                    ON credit_line.id = account_partial_reconcile.credit_move_id
                WHERE debit_line.move_id IN (SELECT unnest(payment_move_ids.move_id) FROM payment_move_ids)
                    AND debit_line.account_id NOT IN %(payment_account_ids)s
                    AND debit_line.debit > 0.0
                    AND credit_line.move_id NOT IN (SELECT unnest(payment_move_ids.move_id) FROM payment_move_ids)
                    AND account_partial_reconcile.max_date BETWEEN %(date_from)s AND %(date_to)s
                GROUP BY credit_line.move_id, credit_line.account_id)
                ''',
                move_ids_query=move_ids_query,
                column_group_key=column_group_key,
                payment_account_ids=payment_account_ids,
                date_from=column_group_options['date']['date_from'],
                date_to=column_group_options['date']['date_to'],
                currency_table=currency_table,
                partial_amount=report._currency_table_apply_rate(SQL("account_partial_reconcile.amount")),
            ))

        self._cr.execute(SQL(' UNION ALL ').join(queries))

        for aml_data in self._cr.dictfetchall():
            reconciled_percentage_per_move[aml_data['column_group_key']].setdefault(aml_data['move_id'], {})
            reconciled_percentage_per_move[aml_data['column_group_key']][aml_data['move_id']].setdefault(aml_data['account_id'], [0.0, 0.0])
            reconciled_percentage_per_move[aml_data['column_group_key']][aml_data['move_id']][aml_data['account_id']][0] += aml_data['balance']

            reconciled_account_ids[aml_data['column_group_key']].add(aml_data['account_id'])

        if not reconciled_percentage_per_move:
            return []

        queries = []

        for column in options['columns']:
            queries.append(SQL(
                '''
                SELECT
                    %(column_group_key)s AS column_group_key,
                    account_move_line.move_id,
                    account_move_line.account_id,
                    SUM(%(balance_select)s) AS balance
                FROM account_move_line
                JOIN %(currency_table)s
                    ON account_currency_table.company_id = account_move_line.company_id
                    AND account_currency_table.rate_type = 'current' -- For payable/receivable accounts it'll always be 'current' anyway
                WHERE account_move_line.move_id IN %(move_ids)s
                    AND account_move_line.account_id IN %(account_ids)s
                GROUP BY account_move_line.move_id, account_move_line.account_id
                ''',
                column_group_key=column['column_group_key'],
                currency_table=currency_table,
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                move_ids=tuple(reconciled_percentage_per_move[column['column_group_key']].keys()) or (None,),
                account_ids=tuple(reconciled_account_ids[column['column_group_key']]) or (None,)
            ))

        self._cr.execute(SQL(' UNION ALL ').join(queries))

        for aml_data in self._cr.dictfetchall():
            if aml_data['account_id'] in reconciled_percentage_per_move[aml_data['column_group_key']][aml_data['move_id']]:
                reconciled_percentage_per_move[aml_data['column_group_key']][aml_data['move_id']][aml_data['account_id']][1] += aml_data['balance']

        reconciled_aml_per_account = {}

        queries = []

        query = Query(self.env, 'account_move_line')
        account_alias = query.join(lhs_alias='account_move_line', lhs_column='account_id', rhs_table='account_account', rhs_column='id', link='account_id')
        account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)
        account_name = self.env['account.account']._field_to_sql(account_alias, 'name')
        account_type = SQL.identifier(account_alias, 'account_type')

        for column in options['columns']:
            queries.append(SQL(
                '''
                SELECT
                    %(column_group_key)s AS column_group_key,
                    account_move_line.move_id,
                    account_move_line.account_id,
                    %(account_code)s AS account_code,
                    %(account_name)s AS account_name,
                    %(account_type)s AS account_account_type,
                    account_account_account_tag.account_account_tag_id AS account_tag_id,
                    SUM(%(balance_select)s) AS balance
                FROM %(from_clause)s
                %(currency_table_join)s
                LEFT JOIN account_account_account_tag
                    ON account_account_account_tag.account_account_id = account_move_line.account_id
                    AND account_account_account_tag.account_account_tag_id IN %(cash_flow_tag_ids)s
                WHERE account_move_line.move_id IN %(move_ids)s
                GROUP BY account_move_line.move_id, account_move_line.account_id, %(account_code)s, %(account_name)s, account_account_type, account_account_account_tag.account_account_tag_id
                ''',
                column_group_key=column['column_group_key'],
                account_code=account_code,
                account_name=account_name,
                account_type=account_type,
                from_clause=query.from_clause,
                currency_table_join=report._currency_table_aml_join(options),
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                cash_flow_tag_ids=tuple(cash_flow_tag_ids),
                move_ids=tuple(reconciled_percentage_per_move[column['column_group_key']].keys()) or (None,)
            ))

        self._cr.execute(SQL(' UNION ALL ').join(queries))

        for aml_data in self._cr.dictfetchall():
            aml_column_group_key = aml_data['column_group_key']
            aml_move_id = aml_data['move_id']
            aml_account_id = aml_data['account_id']
            aml_account_code = aml_data['account_code']
            aml_account_name = aml_data['account_name']
            aml_account_account_type = aml_data['account_account_type']
            aml_account_tag_id = aml_data['account_tag_id']
            aml_balance = aml_data['balance']

            # Compute the total reconciled for the whole move.
            total_reconciled_amount = 0.0
            total_amount = 0.0

            for reconciled_amount, amount in reconciled_percentage_per_move[aml_column_group_key][aml_move_id].values():
                total_reconciled_amount += reconciled_amount
                total_amount += amount

            # Compute matched percentage for each account.
            if total_amount and aml_account_id not in reconciled_percentage_per_move[aml_column_group_key][aml_move_id]:
                # Lines being on reconciled moves but not reconciled with any liquidity move must be valued at the
                # percentage of what is actually paid.
                reconciled_percentage = total_reconciled_amount / total_amount
                aml_balance *= reconciled_percentage
            elif not total_amount and aml_account_id in reconciled_percentage_per_move[aml_column_group_key][aml_move_id]:
                # The total amount to reconcile is 0. In that case, only add entries being on these accounts. Otherwise,
                # this special case will lead to an unexplained difference equivalent to the reconciled amount on this
                # account.
                # E.g:
                #
                # Liquidity move:
                # Account         | Debit     | Credit
                # --------------------------------------
                # Bank            |           | 100
                # Receivable      | 100       |
                #
                # Reconciled move:                          <- reconciled_amount=100, total_amount=0.0
                # Account         | Debit     | Credit
                # --------------------------------------
                # Receivable      |           | 200
                # Receivable      | 200       |             <- Only the reconciled part of this entry must be added.
                aml_balance = -reconciled_percentage_per_move[aml_column_group_key][aml_move_id][aml_account_id][0]
            else:
                # Others lines are not considered.
                continue

            reconciled_aml_per_account.setdefault(aml_account_id, {})
            reconciled_aml_per_account[aml_account_id].setdefault(aml_column_group_key, {
                'column_group_key': aml_column_group_key,
                'account_id': aml_account_id,
                'account_code': aml_account_code,
                'account_name': aml_account_name,
                'account_account_type': aml_account_account_type,
                'account_tag_id': aml_account_tag_id,
                'balance': 0.0,
            })

            reconciled_aml_per_account[aml_account_id][aml_column_group_key]['balance'] -= aml_balance

        return list(reconciled_aml_per_account.values())

    # -------------------------------------------------------------------------
    # COLUMNS / LINES
    # -------------------------------------------------------------------------
    def _get_layout_data(self):
        # Indentation of the following dict reflects the structure of the report.
        return {
            'opening_balance': {'name': _('Cash and cash equivalents, beginning of period'), 'level': 0},
            'net_increase': {'name': _('Net increase in cash and cash equivalents'), 'level': 0, 'unfolded': True},
                'operating_activities': {'name': _('Cash flows from operating activities'), 'level': 2, 'parent_line_id': 'net_increase', 'class': 'fw-bold', 'unfolded': True},
                    'advance_payments_customer': {'name': _('Advance Payments received from customers'), 'level': 4, 'parent_line_id': 'operating_activities'},
                    'received_operating_activities': {'name': _('Cash received from operating activities'), 'level': 4, 'parent_line_id': 'operating_activities'},
                    'advance_payments_suppliers': {'name': _('Advance payments made to suppliers'), 'level': 4, 'parent_line_id': 'operating_activities'},
                    'paid_operating_activities': {'name': _('Cash paid for operating activities'), 'level': 4, 'parent_line_id': 'operating_activities'},
                'investing_activities': {'name': _('Cash flows from investing & extraordinary activities'), 'level': 2, 'parent_line_id': 'net_increase', 'class': 'fw-bold', 'unfolded': True},
                    'investing_activities_cash_in': {'name': _('Cash in'), 'level': 4, 'parent_line_id': 'investing_activities'},
                    'investing_activities_cash_out': {'name': _('Cash out'), 'level': 4, 'parent_line_id': 'investing_activities'},
                'financing_activities': {'name': _('Cash flows from financing activities'), 'level': 2, 'parent_line_id': 'net_increase', 'class': 'fw-bold', 'unfolded': True},
                    'financing_activities_cash_in': {'name': _('Cash in'), 'level': 4, 'parent_line_id': 'financing_activities'},
                    'financing_activities_cash_out': {'name': _('Cash out'), 'level': 4, 'parent_line_id': 'financing_activities'},
                'unclassified_activities': {'name': _('Cash flows from unclassified activities'), 'level': 2, 'parent_line_id': 'net_increase', 'class': 'fw-bold', 'unfolded': True},
                    'unclassified_activities_cash_in': {'name': _('Cash in'), 'level': 4, 'parent_line_id': 'unclassified_activities'},
                    'unclassified_activities_cash_out': {'name': _('Cash out'), 'level': 4, 'parent_line_id': 'unclassified_activities'},
            'closing_balance': {'name': _('Cash and cash equivalents, closing balance'), 'level': 0},
        }

    def _get_layout_line(self, report, options, layout_line_id, layout_line_data, report_data):
        line_id = report._get_generic_line_id(None, None, markup=layout_line_id)
        unfoldable = 'aml_groupby_account' in report_data[layout_line_id] if layout_line_id in report_data else False

        column_values = []

        for column in options['columns']:
            expression_label = column['expression_label']
            column_group_key = column['column_group_key']

            value = report_data[layout_line_id][expression_label].get(column_group_key, 0.0) if layout_line_id in report_data else 0.0

            column_values.append(report._build_column_dict(value, column, options=options))

        return {
            'id': line_id,
            'name': layout_line_data['name'],
            'level': layout_line_data['level'],
            'class': layout_line_data.get('class', ''),
            'columns': column_values,
            'unfoldable': unfoldable,
            'unfolded': line_id in options['unfolded_lines'] or layout_line_data.get('unfolded') or (options.get('unfold_all') and unfoldable),
        }

    def _get_aml_line(self, report, options, aml_data):
        parent_line_id = report._get_generic_line_id(None, None, aml_data['parent_line_id'])
        line_id = report._get_generic_line_id('account.account', aml_data['account_id'], parent_line_id=parent_line_id)

        column_values = []

        for column in options['columns']:
            expression_label = column['expression_label']
            column_group_key = column['column_group_key']

            value = aml_data[expression_label].get(column_group_key, 0.0)

            column_values.append(report._build_column_dict(value, column, options=options))

        return {
            'id': line_id,
            'name': f"{aml_data['account_code']} {aml_data['account_name']}" if aml_data['account_code'] else aml_data['account_name'],
            'caret_options': 'account.account',
            'level': aml_data['level'],
            'parent_id': parent_line_id,
            'columns': column_values,
        }

    def _get_unexplained_difference_line(self, report, options, report_data):
        unexplained_difference = False
        column_values = []

        for column in options['columns']:
            expression_label = column['expression_label']
            column_group_key = column['column_group_key']

            opening_balance = report_data['opening_balance'][expression_label].get(column_group_key, 0.0) if 'opening_balance' in report_data else 0.0
            closing_balance = report_data['closing_balance'][expression_label].get(column_group_key, 0.0) if 'closing_balance' in report_data else 0.0
            net_increase = report_data['net_increase'][expression_label].get(column_group_key, 0.0) if 'net_increase' in report_data else 0.0

            balance = closing_balance - opening_balance - net_increase

            if not self.env.company.currency_id.is_zero(balance):
                unexplained_difference = True

            column_values.append(report._build_column_dict(
                balance,
                {
                    'figure_type': 'monetary',
                    'expression_label': 'balance',
                },
                options=options,
            ))

        if unexplained_difference:
            return {
                'id': report._get_generic_line_id(None, None, markup='unexplained_difference'),
                'name': 'Unexplained Difference',
                'level': 1,
                'columns': column_values,
            }
