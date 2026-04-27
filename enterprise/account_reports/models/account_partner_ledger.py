# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _, fields
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import SQL

from datetime import timedelta
from collections import defaultdict
from copy import deepcopy


class PartnerLedgerCustomHandler(models.AbstractModel):
    _name = 'account.partner.ledger.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Partner Ledger Custom Handler'

    def _get_custom_display_config(self):
        return {
            'css_custom_class': 'partner_ledger',
            'components': {
                'AccountReportLineCell': 'account_reports.PartnerLedgerLineCell',
            },
            'templates': {
                'AccountReportFilters': 'account_reports.PartnerLedgerFilters',
                'AccountReportLineName': 'account_reports.PartnerLedgerLineName',
            },
        }

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        partner_lines, totals_by_column_group = self._build_partner_lines(report, options)
        lines = report._regroup_lines_by_name_prefix(options, partner_lines, '_report_expand_unfoldable_line_partner_ledger_prefix_group', 0)

        # Inject sequence on dynamic lines
        lines = [(0, line) for line in lines]

        # Report total line.
        lines.append((0, self._get_report_line_total(options, totals_by_column_group)))

        return lines

    def _build_partner_lines(self, report, options, level_shift=0):
        lines = []

        totals_by_column_group = {
            column_group_key: {
                total: 0.0
                for total in ['debit', 'credit', 'amount', 'balance']
            }
            for column_group_key in options['column_groups']
        }

        partners_results = self._query_partners(report, options)

        search_filter = options.get('filter_search_bar', '')
        accept_unknown_in_filter = search_filter.lower() in self._get_no_partner_line_label().lower()
        for partner, results in partners_results:
            if options['export_mode'] == 'print' and search_filter and not partner and not accept_unknown_in_filter:
                # When printing and searching for a specific partner, make it so we only show its lines, not the 'Unknown Partner' one, that would be
                # shown in case a misc entry with no partner was reconciled with one of the target partner's entries.
                continue

            partner_values = defaultdict(dict)
            for column_group_key in options['column_groups']:
                partner_sum = results.get(column_group_key, {})

                partner_values[column_group_key]['debit'] = partner_sum.get('debit', 0.0)
                partner_values[column_group_key]['credit'] = partner_sum.get('credit', 0.0)
                partner_values[column_group_key]['amount'] = partner_sum.get('amount', 0.0)
                partner_values[column_group_key]['balance'] = partner_sum.get('balance', 0.0)

                totals_by_column_group[column_group_key]['debit'] += partner_values[column_group_key]['debit']
                totals_by_column_group[column_group_key]['credit'] += partner_values[column_group_key]['credit']
                totals_by_column_group[column_group_key]['amount'] += partner_values[column_group_key]['amount']
                totals_by_column_group[column_group_key]['balance'] += partner_values[column_group_key]['balance']

            lines.append(self._get_report_line_partners(options, partner, partner_values, level_shift=level_shift))

        return lines, totals_by_column_group

    def _report_expand_unfoldable_line_partner_ledger_prefix_group(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        report = self.env['account.report'].browse(options['report_id'])
        matched_prefix = report._get_prefix_groups_matched_prefix_from_line_id(line_dict_id)

        prefix_domain = [('partner_id.name', '=ilike', f'{matched_prefix}%')]
        if self._get_no_partner_line_label().upper().startswith(matched_prefix):
            prefix_domain = expression.OR([prefix_domain, [('partner_id', '=', None)]])

        expand_options = {
            **options,
            'forced_domain': options.get('forced_domain', []) + prefix_domain
        }
        parent_level = len(matched_prefix) * 2
        partner_lines, dummy = self._build_partner_lines(report, expand_options, level_shift=parent_level)

        for partner_line in partner_lines:
            partner_line['id'] = report._build_subline_id(line_dict_id, partner_line['id'])
            partner_line['parent_id'] = line_dict_id

        lines = report._regroup_lines_by_name_prefix(
            options,
            partner_lines,
            '_report_expand_unfoldable_line_partner_ledger_prefix_group',
            parent_level,
            matched_prefix=matched_prefix,
            parent_line_dict_id=line_dict_id,
        )

        return {
            'lines': lines,
            'offset_increment': len(lines),
            'has_more': False,
        }

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        domain = []

        company_ids = report.get_report_company_ids(options)
        exch_code = self.env['res.company'].browse(company_ids).mapped('currency_exchange_journal_id')
        if exch_code:
            domain += ['!', '&', '&', '&', ('credit', '=', 0.0), ('debit', '=', 0.0), ('amount_currency', '!=', 0.0), ('journal_id', 'in', exch_code.ids)]

        if options['export_mode'] == 'print' and options.get('filter_search_bar'):
            domain += [
                '|', ('matched_debit_ids.debit_move_id.partner_id.name', 'ilike', options['filter_search_bar']),
                '|', ('matched_credit_ids.credit_move_id.partner_id.name', 'ilike', options['filter_search_bar']),
                '|', ('partner_id.name', 'ilike', options['filter_search_bar']),
                ('partner_id', '=', False),
            ]

        options['forced_domain'] = options.get('forced_domain', []) + domain

        if self.env.user.has_group('base.group_multi_currency'):
            options['multi_currency'] = True
        else:
            options['columns'] = [col for col in options['columns'] if col['expression_label'] != 'amount_currency']

        if not self.env.ref('account_reports.customer_statement_report', raise_if_not_found=False):
            # Deprecated, will be removed in master
            columns_to_hide = []
            options['hide_account'] = (previous_options or {}).get('hide_account', False)
            columns_to_hide += ['journal_code', 'account_code', 'matching_number'] if options['hide_account'] else []

            options['hide_debit_credit'] = (previous_options or {}).get('hide_debit_credit', False)
            columns_to_hide += ['debit', 'credit'] if options['hide_debit_credit'] else ['amount']

            options['columns'] = [col for col in options['columns'] if col['expression_label'] not in columns_to_hide]

            options['buttons'].append({
                'name': _('Send'),
                'action': 'action_send_statements',
                'sequence': 90,
                'always_show': True,
            })

    def _custom_unfold_all_batch_data_generator(self, report, options, lines_to_expand_by_function):
        partner_ids_to_expand = []

        # Regular case
        for line_dict in lines_to_expand_by_function.get('_report_expand_unfoldable_line_partner_ledger', []):
            markup, model, model_id = self.env['account.report']._parse_line_id(line_dict['id'])[-1]
            if model == 'res.partner':
                partner_ids_to_expand.append(model_id)
            elif markup == 'no_partner':
                partner_ids_to_expand.append(None)

        # In case prefix groups are used
        no_partner_line_label = self._get_no_partner_line_label().upper()
        partner_prefix_domains = []
        for line_dict in lines_to_expand_by_function.get('_report_expand_unfoldable_line_partner_ledger_prefix_group', []):
            prefix = report._get_prefix_groups_matched_prefix_from_line_id(line_dict['id'])
            partner_prefix_domains.append([('name', '=ilike', f'{prefix}%')])

            # amls without partners are regrouped "Unknown Partner", which is also used to create prefix groups
            if no_partner_line_label.startswith(prefix):
                partner_ids_to_expand.append(None)

        if partner_prefix_domains:
            partner_ids_to_expand += self.env['res.partner'].with_context(active_test=False).search(expression.OR(partner_prefix_domains)).ids

        return {
            'initial_balances': self._get_initial_balance_values(partner_ids_to_expand, options) if partner_ids_to_expand else {},

            # load_more_limit cannot be passed to this call, otherwise it won't be applied per partner but on the whole result.
            # We gain perf from batching, but load every result, even if the limit restricts them later.
            'aml_values': self._get_aml_values(options, partner_ids_to_expand) if partner_ids_to_expand else {},
        }

    def _get_report_send_recipients(self, options):
        # Deprecated, to be moved to customer statement handler in master
        partners = options.get('partner_ids', [])
        if not partners:
            report = self.env['account.report'].browse(options['report_id'])
            self._cr.execute(self._get_query_sums(report, options))
            partners = [row['groupby'] for row in self._cr.dictfetchall() if row['groupby']]
        return self.env['res.partner'].browse(partners)

    def action_send_statements(self, options):
        # Deprecated, to be moved to customer statement handler in master
        template = self.env.ref('account_reports.email_template_customer_statement', False)
        partners = self.env['res.partner'].browse(options.get('partner_ids', []))
        return {
            'name': _("Send %s Statement", partners.name) if len(partners) == 1 else _("Send Partner Ledgers"),
            'type': 'ir.actions.act_window',
            'views': [[False, 'form']],
            'res_model': 'account.report.send',
            'target': 'new',
            'context': {
                'default_mail_template_id': template.id if template else False,
                'default_report_options': options,
            },
        }

    @api.model
    def action_open_partner(self, options, params):
        dummy, record_id = self.env['account.report']._get_model_info_from_id(params['id'])
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': record_id,
            'views': [[False, 'form']],
            'view_mode': 'form',
            'target': 'current',
        }

    def _query_partners(self, report, options):
        """ Executes the queries and performs all the computation.
        :return:        A list of tuple (partner, column_group_values) sorted by the table's model _order:
                        - partner is a res.parter record.
                        - column_group_values is a dict(column_group_key, fetched_values), where
                            - column_group_key is a string identifying a column group, like in options['column_groups']
                            - fetched_values is a dictionary containing:
                                - sum:                              {'debit': float, 'credit': float, 'balance': float}
                                - (optional) initial_balance:       {'debit': float, 'credit': float, 'balance': float}
                                - (optional) lines:                 [line_vals_1, line_vals_2, ...]
        """
        def assign_sum(row):
            fields_to_assign = ['balance', 'debit', 'credit', 'amount']
            if any(not company_currency.is_zero(row[field]) for field in fields_to_assign):
                groupby_partners.setdefault(row['groupby'], defaultdict(lambda: defaultdict(float)))
                for field in fields_to_assign:
                    groupby_partners[row['groupby']][row['column_group_key']][field] += row[field]

        company_currency = self.env.company.currency_id

        # Execute the queries and dispatch the results.
        query = self._get_query_sums(report, options)

        groupby_partners = {}

        self._cr.execute(query)
        for res in self._cr.dictfetchall():
            assign_sum(res)

        # Correct the sums per partner, for the lines without partner reconciled with a line having a partner
        self._add_sums_of_lines_without_partners(options, groupby_partners)

        # Retrieve the partners to browse.
        # groupby_partners.keys() contains all account ids affected by:
        # - the amls in the current period.
        # - the amls affecting the initial balance.
        if groupby_partners:
            # Note a search is done instead of a browse to preserve the table ordering.
            partners = self.env['res.partner'].with_context(active_test=False).search_fetch([('id', 'in', list(groupby_partners.keys()))], ["id", "name", "trust", "company_registry", "vat"])
        else:
            partners = []

        # Add 'Partner Unknown' if needed
        if None in groupby_partners.keys():
            partners = [p for p in partners] + [None]

        return [(partner, groupby_partners[partner.id if partner else None]) for partner in partners]

    def _get_query_sums(self, report, options) -> SQL:
        """ Construct a query retrieving all the aggregated sums to build the report. It includes:
        - sums for all partners.
        - sums for the initial balances.
        :param options:             The report options.
        :return:                    query as SQL object
        """
        queries = []

        # Create the currency table.
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            query = report._get_report_query(column_group_options, 'from_beginning')
            date_from = options['date']['date_from']
            queries.append(SQL(
                """
                (WITH partner_sums AS (
                    SELECT
                        account_move_line.partner_id            AS groupby,
                        %(column_group_key)s                    AS column_group_key,
                        SUM(%(debit_select)s)                   AS debit,
                        SUM(%(credit_select)s)                  AS credit,
                        SUM(%(balance_select)s)                 AS amount,
                        SUM(%(balance_select)s)                 AS balance,
                        BOOL_AND(account_move_line.reconciled)  AS all_reconciled,
                        MAX(account_move_line.date)             AS latest_date
                    FROM %(table_references)s
                    %(currency_table_join)s
                    WHERE %(search_condition)s
                    GROUP BY account_move_line.partner_id
                )
                SELECT *
                FROM partner_sums
                WHERE partner_sums.balance != 0
                OR partner_sums.all_reconciled = FALSE
                OR partner_sums.latest_date >= %(date_from)s
                )""",
                column_group_key=column_group_key,
                debit_select=report._currency_table_apply_rate(SQL("account_move_line.debit")),
                credit_select=report._currency_table_apply_rate(SQL("account_move_line.credit")),
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(column_group_options),
                search_condition=query.where_clause,
                date_from=date_from,
            ))

        return SQL(' UNION ALL ').join(queries)

    def _get_initial_balance_values(self, partner_ids, options):
        queries = []
        report = self.env.ref('account_reports.partner_ledger_report')
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            # Get sums for the initial balance.
            # period: [('date' <= options['date_from'] - 1)]
            new_options = self._get_options_initial_balance(column_group_options)
            query = report._get_report_query(new_options, 'from_beginning', domain=[('partner_id', 'in', partner_ids)])
            queries.append(SQL(
                """
                SELECT
                    account_move_line.partner_id,
                    %(column_group_key)s          AS column_group_key,
                    SUM(%(debit_select)s)         AS debit,
                    SUM(%(credit_select)s)        AS credit,
                    SUM(%(balance_select)s)       AS amount,
                    SUM(%(balance_select)s)       AS balance
                FROM %(table_references)s
                %(currency_table_join)s
                WHERE %(search_condition)s
                GROUP BY account_move_line.partner_id
                """,
                column_group_key=column_group_key,
                debit_select=report._currency_table_apply_rate(SQL("account_move_line.debit")),
                credit_select=report._currency_table_apply_rate(SQL("account_move_line.credit")),
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(column_group_options),
                search_condition=query.where_clause,
            ))

        self._cr.execute(SQL(" UNION ALL ").join(queries))

        init_balance_by_col_group = {
            partner_id: {column_group_key: defaultdict(float) for column_group_key in options['column_groups']}
            for partner_id in partner_ids
        }
        for result in self._cr.dictfetchall():
            init_balance_by_col_group[result['partner_id']][result['column_group_key']] = result

        # Correct the sums per partner, for the lines without partner reconciled with a line having a partner
        new_options = self._get_options_initial_balance(options)
        self._add_sums_of_lines_without_partners(new_options, init_balance_by_col_group)

        return init_balance_by_col_group

    def _get_options_initial_balance(self, options):
        """ Create options used to compute the initial balances for each partner.
        The resulting dates domain will be:
        [('date' <= options['date_from'] - 1)]
        :param options: The report options.
        :return:        A copy of the options, modified to match the dates to use to get the initial balances.
        """
        new_date_to = fields.Date.from_string(options['date']['date_from']) - timedelta(days=1)
        new_options = deepcopy(options)
        new_options['date']['date_from'] = False
        new_options['date']['date_to'] = fields.Date.to_string(new_date_to)
        for column_group in new_options['column_groups'].values():
            column_group['forced_options']['date'] = new_options['date']
        return new_options

    def _add_sums_of_lines_without_partners(self, options, result_dict):
        fields2inverse = {
            'balance': ('balance', -1),
            'debit': ('credit', 1),
            'amount': ('amount', 1),
            'credit': ('debit', 1),
        }
        query = self._get_sums_without_partner(options)
        self._cr.execute(query)
        rows = self._cr.dictfetchall()
        for row in rows:
            for field, (inverse_field, inverse_sign) in fields2inverse.items():
                if partner_vals := result_dict.get(row['groupby']):
                    partner_vals[row['column_group_key']][field] += row[field]
                if no_partner_vals := result_dict.get(None):
                    # Debit/credit are inverted for the unknown partner as the computation is made regarding the balance of the known partner
                    no_partner_vals[row['column_group_key']][inverse_field] += inverse_sign * row[field]

    def _get_sums_without_partner(self, options):
        """ Get the sum of lines without partner reconciled with a line with a partner, grouped by partner. Those lines
        should be considered as belonging to the partner for the reconciled amount as it may clear some of the partner
        invoice/bill and they have to be accounted in the partner balance."""
        queries = []
        report = self.env.ref('account_reports.partner_ledger_report')
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            query = report._get_report_query(column_group_options, 'from_beginning')
            queries.append(SQL(
                """
                SELECT
                    %(column_group_key)s        AS column_group_key,
                    aml_with_partner.partner_id AS groupby,
                    SUM(%(debit_select)s)       AS debit,
                    SUM(%(credit_select)s)      AS credit,
                    SUM(%(balance_select)s)     AS amount,
                    SUM(%(balance_select)s)     AS balance
                FROM %(table_references)s
                JOIN account_partial_reconcile partial
                    ON account_move_line.id = partial.debit_move_id OR account_move_line.id = partial.credit_move_id
                JOIN account_move_line aml_with_partner ON
                    (aml_with_partner.id = partial.debit_move_id OR aml_with_partner.id = partial.credit_move_id)
                    AND aml_with_partner.partner_id IS NOT NULL
                %(currency_table_join)s
                WHERE partial.max_date <= %(date_to)s AND %(search_condition)s
                    AND account_move_line.partner_id IS NULL
                GROUP BY aml_with_partner.partner_id
                """,
                column_group_key=column_group_key,
                debit_select=report._currency_table_apply_rate(SQL("CASE WHEN aml_with_partner.balance > 0 THEN 0 ELSE partial.amount END")),
                credit_select=report._currency_table_apply_rate(SQL("CASE WHEN aml_with_partner.balance < 0 THEN 0 ELSE partial.amount END")),
                balance_select=report._currency_table_apply_rate(SQL("-SIGN(aml_with_partner.balance) * partial.amount")),
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(column_group_options, aml_alias=SQL("aml_with_partner")),
                date_to=column_group_options['date']['date_to'],
                search_condition=query.where_clause,
            ))

        return SQL(" UNION ALL ").join(queries)

    def _report_expand_unfoldable_line_partner_ledger(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        report = self.env['account.report'].browse(options['report_id'])
        markup, model, record_id = report._parse_line_id(line_dict_id)[-1]

        if model != 'res.partner':
            raise UserError(_("Wrong ID for partner ledger line to expand: %s", line_dict_id))

        prefix_groups_count = 0
        for markup, dummy1, dummy2 in report._parse_line_id(line_dict_id):
            if isinstance(markup, dict) and 'groupby_prefix_group' in markup:
                prefix_groups_count += 1
        level_shift = prefix_groups_count * 2

        lines = []

        # Get initial balance
        if offset == 0 and not options.get('hide_initial_balance'):
            if unfold_all_batch_data:
                init_balance_by_col_group = unfold_all_batch_data['initial_balances'][record_id]
            else:
                init_balance_by_col_group = self._get_initial_balance_values([record_id], options)[record_id]
            initial_balance_line = report._get_partner_and_general_ledger_initial_balance_line(options, line_dict_id, init_balance_by_col_group, level_shift=level_shift)
            if initial_balance_line:
                lines.append(initial_balance_line)

                # For the first expansion of the line, the initial balance line gives the progress
                progress = self._init_load_more_progress(options, initial_balance_line)

        limit_to_load = report.load_more_limit + 1 if report.load_more_limit and options['export_mode'] != 'print' else None

        if unfold_all_batch_data:
            aml_results = unfold_all_batch_data['aml_values'][record_id]
        else:
            aml_results = self._get_aml_values(options, [record_id], offset=offset, limit=limit_to_load)[record_id]

        aml_report_lines, next_progress, treated_results_count, has_more = self._get_partner_aml_report_lines(report, options, line_dict_id, aml_results, progress, offset, level_shift=level_shift)
        lines.extend(aml_report_lines)

        return {
            'lines': lines,
            'offset_increment': treated_results_count,
            'has_more': has_more,
            'progress': next_progress
        }

    def _init_load_more_progress(self, options, line_dict):
        return {
            column['column_group_key']: line_col.get('no_format', 0)
            for column, line_col in zip(options['columns'], line_dict['columns'])
            if column['expression_label'] == 'balance'
        }

    def _get_partner_aml_report_lines(self, report, options, partner_line_id, aml_results, progress, offset=0, level_shift=0):
        lines = []
        has_more = False
        treated_results_count = 0
        next_progress = progress
        for result in aml_results:
            if self._is_report_limit_reached(report, options, treated_results_count):
                # We loaded one more than the limit on purpose: this way we know we need a "load more" line
                has_more = True
                break

            new_line = self._get_report_line_move_line(options, result, partner_line_id, next_progress, level_shift=level_shift)
            lines.append(new_line)
            next_progress = self._init_load_more_progress(options, new_line)
            treated_results_count += 1
        return lines, next_progress, treated_results_count, has_more

    def _is_report_limit_reached(self, report, options, results_count):
        return options['export_mode'] != 'print' and report.load_more_limit and results_count == report.load_more_limit

    def _get_additional_column_aml_values(self):
        """
        Allows customization of additional fields in the partner ledger query.

        This method is intended to be overridden by other modules to add custom fields
        to the partner ledger query, e.g. SQL("account_move_line.date AS date,").

        By default, it returns an empty SQL object.
        """
        return SQL()

    def _get_order_by_aml_values(self):
        return SQL('account_move_line.date, account_move_line.id')

    def _get_aml_values(self, options, partner_ids, offset=0, limit=None):
        rslt = {partner_id: [] for partner_id in partner_ids}

        partner_ids_wo_none = [x for x in partner_ids if x]
        directly_linked_aml_partner_clauses = []
        indirectly_linked_aml_partner_clause = SQL('aml_with_partner.partner_id IS NOT NULL')
        if None in partner_ids:
            directly_linked_aml_partner_clauses.append(SQL('account_move_line.partner_id IS NULL'))
        if partner_ids_wo_none:
            directly_linked_aml_partner_clauses.append(SQL('account_move_line.partner_id IN %s', tuple(partner_ids_wo_none)))
            indirectly_linked_aml_partner_clause = SQL('aml_with_partner.partner_id IN %s', tuple(partner_ids_wo_none))
        directly_linked_aml_partner_clause = SQL('(%s)', SQL(' OR ').join(directly_linked_aml_partner_clauses))

        queries = []
        journal_name = self.env['account.journal']._field_to_sql('journal', 'name')
        report = self.env.ref('account_reports.partner_ledger_report')
        additional_columns = self._get_additional_column_aml_values()
        order_by = self._get_order_by_aml_values()
        for column_group_key, group_options in report._split_options_per_column_group(options).items():
            query = report._get_report_query(group_options, 'strict_range')
            account_alias = query.left_join(lhs_alias='account_move_line', lhs_column='account_id', rhs_table='account_account', rhs_column='id', link='account_id')
            account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)
            account_name = self.env['account.account']._field_to_sql(account_alias, 'name')

            # For the move lines directly linked to this partner
            # ruff: noqa: FURB113
            queries.append(SQL(
                '''
                SELECT
                    account_move_line.id,
                    COALESCE(account_move_line.date_maturity, account_move_line.date) AS date_maturity,
                    account_move_line.name,
                    account_move_line.ref,
                    account_move_line.company_id,
                    account_move_line.account_id,
                    account_move_line.payment_id,
                    account_move_line.partner_id,
                    account_move_line.currency_id,
                    account_move_line.amount_currency,
                    account_move_line.matching_number,
                    %(additional_columns)s
                    COALESCE(account_move_line.invoice_date, account_move_line.date) AS invoice_date,
                    %(debit_select)s                                                 AS debit,
                    %(credit_select)s                                                AS credit,
                    %(balance_select)s                                               AS amount,
                    %(balance_select)s                                               AS balance,
                    account_move.name                                                AS move_name,
                    account_move.move_type                                           AS move_type,
                    %(account_code)s                                                 AS account_code,
                    %(account_name)s                                                 AS account_name,
                    journal.code                                                     AS journal_code,
                    %(journal_name)s                                                 AS journal_name,
                    %(column_group_key)s                                             AS column_group_key,
                    'directly_linked_aml'                                            AS key,
                    0                                                                AS partial_id
                    %(extra_select)s
                FROM %(table_references)s
                JOIN account_move ON account_move.id = account_move_line.move_id
                %(currency_table_join)s
                LEFT JOIN res_company company               ON company.id = account_move_line.company_id
                LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
                LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
                WHERE %(search_condition)s AND %(directly_linked_aml_partner_clause)s
                ORDER BY %(order_by)s
                ''',
                additional_columns=additional_columns,
                debit_select=report._currency_table_apply_rate(SQL("account_move_line.debit")),
                credit_select=report._currency_table_apply_rate(SQL("account_move_line.credit")),
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                account_code=account_code,
                account_name=account_name,
                journal_name=journal_name,
                column_group_key=column_group_key,
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(group_options),
                search_condition=query.where_clause,
                directly_linked_aml_partner_clause=directly_linked_aml_partner_clause,
                order_by=order_by,
                extra_select=SQL(' ').join(self._get_aml_value_extra_select()),
            ))

            # For the move lines linked to no partner, but reconciled with this partner. They will appear in grey in the report
            queries.append(SQL(
                '''
                SELECT
                    account_move_line.id,
                    COALESCE(account_move_line.date_maturity, account_move_line.date) AS date_maturity,
                    account_move_line.name,
                    account_move_line.ref,
                    account_move_line.company_id,
                    account_move_line.account_id,
                    account_move_line.payment_id,
                    aml_with_partner.partner_id,
                    account_move_line.currency_id,
                    account_move_line.amount_currency,
                    account_move_line.matching_number,
                    %(additional_columns)s
                    COALESCE(account_move_line.invoice_date, account_move_line.date) AS invoice_date,
                    %(debit_select)s                                                 AS debit,
                    %(credit_select)s                                                AS credit,
                    %(balance_select)s                                               AS amount,
                    %(balance_select)s                                               AS balance,
                    account_move.name                                                AS move_name,
                    account_move.move_type                                           AS move_type,
                    %(account_code)s                                                 AS account_code,
                    %(account_name)s                                                 AS account_name,
                    journal.code                                                     AS journal_code,
                    %(journal_name)s                                                 AS journal_name,
                    %(column_group_key)s                                             AS column_group_key,
                    'indirectly_linked_aml'                                          AS key,
                    partial.id                                                       AS partial_id
                    %(extra_select)s
                FROM %(table_references)s
                    %(currency_table_join)s,
                    account_partial_reconcile partial,
                    account_move,
                    account_move_line aml_with_partner,
                    account_journal journal
                WHERE
                    (account_move_line.id = partial.debit_move_id OR account_move_line.id = partial.credit_move_id)
                    AND account_move_line.partner_id IS NULL
                    AND account_move.id = account_move_line.move_id
                    AND (aml_with_partner.id = partial.debit_move_id OR aml_with_partner.id = partial.credit_move_id)
                    AND %(indirectly_linked_aml_partner_clause)s
                    AND journal.id = account_move_line.journal_id
                    AND %(account_alias)s.id = account_move_line.account_id
                    AND %(search_condition)s
                    AND partial.max_date BETWEEN %(date_from)s AND %(date_to)s
                ORDER BY %(order_by)s
                ''',
                additional_columns=additional_columns,
                debit_select=report._currency_table_apply_rate(SQL("CASE WHEN aml_with_partner.balance > 0 THEN 0 ELSE partial.amount END")),
                credit_select=report._currency_table_apply_rate(SQL("CASE WHEN aml_with_partner.balance < 0 THEN 0 ELSE partial.amount END")),
                balance_select=report._currency_table_apply_rate(SQL("-SIGN(aml_with_partner.balance) * partial.amount")),
                account_code=account_code,
                account_name=account_name,
                journal_name=journal_name,
                column_group_key=column_group_key,
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(group_options),
                indirectly_linked_aml_partner_clause=indirectly_linked_aml_partner_clause,
                account_alias=SQL.identifier(account_alias),
                search_condition=query.where_clause,
                date_from=group_options['date']['date_from'],
                date_to=group_options['date']['date_to'],
                order_by=order_by,
                extra_select=SQL(' ').join(self._get_aml_value_extra_select()),
            ))

        query = SQL(" UNION ALL ").join(SQL("(%s)", query) for query in queries)

        if offset:
            query = SQL('%s OFFSET %s ', query, offset)

        if limit:
            query = SQL('%s LIMIT %s ', query, limit)

        self._cr.execute(query)
        for aml_result in self._cr.dictfetchall():
            if aml_result['key'] == 'indirectly_linked_aml':

                # Append the line to the partner found through the reconciliation.
                if aml_result['partner_id'] in rslt:
                    rslt[aml_result['partner_id']].append(aml_result)

                # Balance it with an additional line in the Unknown Partner section but having reversed amounts.
                if None in rslt:
                    rslt[None].append({
                        **aml_result,
                        'debit': aml_result['credit'],
                        'credit': aml_result['debit'],
                        'amount': aml_result['credit'] - aml_result['debit'],
                        'balance': -aml_result['balance'],
                    })
            else:
                rslt[aml_result['partner_id']].append(aml_result)

        return rslt

    def _get_aml_value_extra_select(self):
        """ Hook method to add extra select fields to the aml queries. """
        return []

    ####################################################
    # COLUMNS/LINES
    ####################################################
    def _get_report_line_partners(self, options, partner, partner_values, level_shift=0):
        company_currency = self.env.company.currency_id

        partner_data = next(iter(partner_values.values()))
        unfoldable = not company_currency.is_zero(partner_data.get('debit', 0) or partner_data.get('credit', 0))
        column_values = []
        report = self.env['account.report'].browse(options['report_id'])
        for column in options['columns']:
            col_expr_label = column['expression_label']
            value = None if options.get('hide_partner_totals') else partner_values[column['column_group_key']].get(col_expr_label)
            unfoldable = unfoldable or (col_expr_label in ('debit', 'credit', 'amount') and not company_currency.is_zero(value))
            column_values.append(report._build_column_dict(value, column, options=options))


        line_id = report._get_generic_line_id('res.partner', partner.id) if partner else report._get_generic_line_id('res.partner', None, markup='no_partner')

        return {
            'id': line_id,
            'name': partner is not None and (partner.name or '')[:128] or self._get_no_partner_line_label(),
            'columns': column_values,
            'level': 1 + level_shift,
            'trust': partner.trust if partner else None,
            'unfoldable': unfoldable,
            'unfolded': line_id in options['unfolded_lines'] or options['unfold_all'],
            'expand_function': '_report_expand_unfoldable_line_partner_ledger',
        }

    def _get_no_partner_line_label(self):
        return _('Unknown Partner')

    @api.model
    def _format_aml_name(self, line_name, move_ref, move_name=None):
        ''' Format the display of an account.move.line record. As its very costly to fetch the account.move.line
        records, only line_name, move_ref, move_name are passed as parameters to deal with sql-queries more easily.

        :param line_name:   The name of the account.move.line record.
        :param move_ref:    The reference of the account.move record.
        :param move_name:   The name of the account.move record.
        :return:            The formatted name of the account.move.line record.
        '''
        return self.env['account.move.line']._format_aml_name(line_name, move_ref, move_name=move_name)

    def _get_report_line_move_line(self, options, aml_query_result, partner_line_id, init_bal_by_col_group, level_shift=0):
        if aml_query_result['payment_id']:
            caret_type = 'account.payment'
        else:
            caret_type = 'account.move.line'

        columns = []
        report = self.env['account.report'].browse(options['report_id'])
        for column in options['columns']:
            col_expr_label = column['expression_label']

            if col_expr_label not in aml_query_result:
                raise UserError(_("The column '%s' is not available for this report.", col_expr_label))

            col_value = aml_query_result[col_expr_label] if column['column_group_key'] == aml_query_result['column_group_key'] else None

            if col_value is None:
                columns.append(report._build_column_dict(None, None))
            else:
                currency = False

                if col_expr_label == 'balance':
                    col_value += init_bal_by_col_group[column['column_group_key']]

                if col_expr_label == 'amount_currency':
                    currency = self.env['res.currency'].browse(aml_query_result['currency_id'])

                    if currency == self.env.company.currency_id:
                        col_value = ''

                columns.append(report._build_column_dict(col_value, column, options=options, currency=currency))

        return {
            'id': report._get_generic_line_id('account.move.line', aml_query_result['id'], parent_line_id=partner_line_id, markup=aml_query_result['partial_id']),
            'parent_id': partner_line_id,
            'name': self._format_aml_name(aml_query_result['name'], aml_query_result['ref'], aml_query_result['move_name']),
            'columns': columns,
            'caret_options': caret_type,
            'level': 3 + level_shift,
        }

    def _get_report_line_total(self, options, totals_by_column_group):
        column_values = []
        report = self.env['account.report'].browse(options['report_id'])
        for column in options['columns']:
            col_value = totals_by_column_group[column['column_group_key']].get(column['expression_label'])
            column_values.append(report._build_column_dict(col_value, column, options=options))

        return {
            'id': report._get_generic_line_id(None, None, markup='total'),
            'name': _('Total'),
            'level': 1,
            'columns': column_values,
        }

    def open_journal_items(self, options, params):
        params['view_ref'] = 'account.view_move_line_tree_grouped_partner'
        report = self.env['account.report'].browse(options['report_id'])
        action = report.open_journal_items(options=options, params=params)
        action.get('context', {}).update({'search_default_group_by_account': 0})
        return action
