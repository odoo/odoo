# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, fields, models
from odoo.tools import date_utils, SQL
from odoo.tools.misc import format_date, get_lang


class L10nVnTaxCustomHandler(models.AbstractModel):
    _name = 'l10n_vn.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Taxes Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        report_lines = self._build_month_lines(report, options)

        if grand_total_line := self._build_grand_total_line(report, options):
            report_lines.append(grand_total_line)

        # Inject sequences on the dynamic lines
        return [(0, line) for line in report_lines]

    # First level, month rows
    def _build_month_lines(self, report, options):
        """ Fetches the months for which we have entries *that have tax grids* and build a report line for each of them. """
        month_lines = []
        queries = []

        # 1) Build the queries to get the months
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            domain = [('move_id.move_type', '=', options['move_type'])]
            query = report._get_report_query(column_group_options, date_scope="strict_range", domain=domain)
            # The joins are there to filter out months for which we would not have any lines in the report.
            queries.append(SQL(
                """
                  SELECT (date_trunc('month', account_move_line.date::date) + interval '1 month' - interval '1 day')::date AS taxable_month,
                         %(column_group_key)s                                                                              AS column_group_key
                    FROM %(table_references)s
                    JOIN account_account_tag_account_move_line_rel account_tag_rel ON account_tag_rel.account_move_line_id = account_move_line.id
                    JOIN account_account_tag account_tag ON account_tag.id = account_tag_rel.account_account_tag_id
                   WHERE %(search_condition)s
                GROUP BY taxable_month
                ORDER BY taxable_month DESC
                """,
                column_group_key=column_group_key,
                table_references=query.from_clause,
                search_condition=query.where_clause,
            ))

        self.env.cr.execute(SQL(" UNION ALL ").join(queries))

        # 2) Make the lines
        unfold_all = options['export_mode'] == 'print' or options.get('unfold_all')
        for res in self._cr.dictfetchall():
            line_id = report._get_generic_line_id('', '', markup=str(res['taxable_month']))
            month_lines.append({
                'id': line_id,
                'name': format_date(self.env, res['taxable_month'], date_format='MMMM y'),
                'unfoldable': True,
                'unfolded': line_id in options['unfolded_lines'] or unfold_all,
                'columns': [report._build_column_dict(None, _column) for _column in options['columns']],
                'level': 0,
                'expand_function': '_report_expand_unfoldable_line_l10n_vn_expand_month',
            })

        return month_lines

    # Second level, tax group rows
    def _report_expand_unfoldable_line_l10n_vn_expand_month(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        """ Used to expand a month line and load the second level, being the tax groups lines. """
        report = self.env['account.report'].browse(options['report_id'])
        month = report._get_markup(line_dict_id)
        tax_group_lines_values = self._query_tax_groups(options, report, month, offset)
        return self._get_report_expand_unfoldable_line_value(report, options, line_dict_id, progress, tax_group_lines_values,
                                                             report_line_method=self._get_report_line_tax_group)

    def _query_tax_groups(self, options, report, month, offset):
        """ Query the values for the tax group line.
        The tax group line will sum up the values for the different columns, while being filtered by the month only.
        """
        limit = report.load_more_limit + 1 if report.load_more_limit and options['export_mode'] != 'print' else None
        # Month is already set to the last day of the month.
        end_date = fields.Date.from_string(month)
        start_date = date_utils.start_of(end_date, 'month')
        queries = []
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            domain = [
                ('move_id.move_type', '=', options['move_type']),
                # Make sure to only fetch records that are in the parent's row month
                ('date', '>=', start_date),
                ('date', '<=', end_date),
            ]
            query = report._get_report_query(column_group_options, date_scope="strict_range", domain=domain)
            tail_query = report._get_engine_query_tail(offset, limit)
            lang = self.env.user.lang or get_lang(self.env).code
            if self.pool['account.account.tag'].name.translate:
                account_tag_name = SQL(
                    "COALESCE(account_tag.name->>%(lang)s, account_tag.name->>'en_US')", lang=lang)
            else:
                account_tag_name = SQL.identifier('account_tag', 'name')
            queries.append(SQL(
                """
                  SELECT %(column_group_key)s AS column_group_key,
                         REGEXP_REPLACE(%(account_tag_name)s, '^[+-]', '')                                                  AS tag_name,
                         SUM(account_move_line.tax_base_amount)                                                             AS tax_base_amount,
                         SUM(%(balance_select)s
                             * CASE WHEN account_tag.tax_negate THEN -1 ELSE 1 END
                             * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                         )                                                                                                  AS balance
                    FROM %(table_references)s
                    JOIN res_partner p ON p.id = account_move_line__move_id.partner_id
                    JOIN res_partner cp ON cp.id = p.commercial_partner_id
                    JOIN account_account_tag_account_move_line_rel account_tag_rel ON account_tag_rel.account_move_line_id = account_move_line.id
                    JOIN account_account_tag account_tag ON account_tag.id = account_tag_rel.account_account_tag_id
                    %(currency_table_join)s
                   WHERE %(search_condition)s
                GROUP BY %(account_tag_name)s
                %(tail_query)s
                """,
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                column_group_key=column_group_key,
                account_tag_name=account_tag_name,
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(column_group_options),
                search_condition=query.where_clause,
                tail_query=tail_query,
            ))

        self.env.cr.execute(SQL(" UNION ALL ").join(queries))
        return self._process_tax_group_lines(self.env.cr.dictfetchall(), options)

    def _process_tax_group_lines(self, data_dict, options):
        """ Taking in the values from the database, this will construct the column values by using the tax groups and
        tax grid mapping set in the option of each report section.
        """
        lines_values = {}
        for values in data_dict:
            for tax_group, tax_group_values in options['tax_groups'].items():
                if tax_group not in lines_values:
                    lines_values[tax_group] = {
                        'name': tax_group_values['name'],
                        values['column_group_key']: {
                            'column_group_key': values['column_group_key'],
                        }
                    }
                self._eval_report_grids_map(options, tax_group, values, column_values=lines_values[tax_group][values['column_group_key']])
        return lines_values

    def _get_report_line_tax_group(self, report, options, tax_group, line_values, parent_line_id):
        """ Format the given values to match the report line format. """
        line_columns = self._get_line_column(report, options, line_values)
        line_id = report._get_generic_line_id('', '', markup=tax_group, parent_line_id=parent_line_id)
        unfold_all = options['export_mode'] == 'print' or options.get('unfold_all')
        return {
            'id': line_id,
            'parent_id': parent_line_id,
            'name': line_values['name'],
            'unfoldable': True,
            'unfolded': line_id in options['unfolded_lines'] or unfold_all,
            'columns': line_columns,
            'level': 1,
            'expand_function': '_report_expand_unfoldable_line_l10n_vn_expand_tax_group',
        }

    def _report_expand_unfoldable_line_l10n_vn_expand_tax_group(self, line_dict_id, groupby, options, progess, offset, unfold_all_batch_data=None):
        """ Used to expand a tax group line and load the third level, being the account moves lines. """
        report = self.env['account.report'].browse(options['report_id'])
        month = report._parse_line_id(line_dict_id)[1][0]
        tax_group = report._get_markup(line_dict_id)
        lines_values = self._query_moves(options, report, tax_group, month, offset)
        return self._get_report_expand_unfoldable_line_value(report, options, line_dict_id, progess, lines_values, report_line_method=self._get_report_line_move)

    def _query_moves(self, options, report, tax_group, month, offset):
        """ Fetches the moves for a given month and returns a dictionary mapping partner ids to line values. """
        limit = report.load_more_limit + 1 if report.load_more_limit and options['export_mode'] != 'print' else None
        end_date = fields.Date.from_string(month)
        start_date = date_utils.start_of(end_date, 'month')
        tax_groups = [grid for grids in options['tax_groups'][tax_group]['report_grids_map'].values() for grid in grids]
        queries = []
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            domain = [
                ('move_id.move_type', '=', options['move_type']),
                # Make sure to only fetch records that are in the parent's row month
                ('date', '>=', start_date),
                ('date', '<=', end_date),
            ]
            query = report._get_report_query(column_group_options, date_scope="strict_range", domain=domain)
            tail_query = report._get_engine_query_tail(offset, limit)
            lang = self.env.user.lang or get_lang(self.env).code
            invoice_number_column = SQL('l10n_vn_e_invoice_number' if options['move_type'] == 'out_invoice' else 'payment_reference')
            if self.pool['account.account.tag'].name.translate:
                account_tag_name = SQL("COALESCE(account_tag.name->>%(lang)s, account_tag.name->>'en_US')", lang=lang)
            else:
                account_tag_name = SQL.identifier('account_tag', 'name')
            tax_groups_condition = SQL("REGEXP_REPLACE(%(account_tag_name)s, '^[+-]', '') = ANY(%(tax_groups)s)",
                                       account_tag_name=account_tag_name,
                                       tax_groups=tax_groups)
            queries.append(SQL(
                """
                  SELECT %(column_group_key)s                                                                               AS column_group_key,
                         partner.name                                                                                       AS partner_name,
                         partner.vat                                                                                        AS vat,
                         REGEXP_REPLACE(%(account_tag_name)s, '^[+-]', '')                                                  AS tag_name,
                         account_move_line__move_id.id                                                                      AS move_id,
                         account_move_line__move_id.name                                                                    AS move_name,
                         account_move_line__move_id.ref                                                                     AS move_ref,
                         account_move_line__move_id.%(invoice_number_column)s                                               AS invoice_number,
                         account_move_line__move_id.invoice_date                                                            AS invoice_date,
                         SUM(%(balance_select)s
                             * CASE WHEN account_tag.tax_negate THEN -1 ELSE 1 END
                             * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                         )                                                                                                  AS balance
                    FROM %(table_references)s
                    JOIN res_partner partner ON partner.id = account_move_line.partner_id
                    JOIN account_account_tag_account_move_line_rel account_tag_rel ON account_tag_rel.account_move_line_id = account_move_line.id
                    JOIN account_account_tag account_tag ON account_tag.id = account_tag_rel.account_account_tag_id
                    %(currency_table_join)s
                    WHERE %(search_condition)s AND %(tax_groups_condition)s
                GROUP BY partner.id, account_move_line__move_id.id, %(account_tag_name)s
                %(tail_query)s
                """,
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                column_group_key=column_group_key,
                account_tag_name=account_tag_name,
                invoice_number_column=invoice_number_column,
                table_references=query.from_clause,
                search_condition=query.where_clause,
                currency_table_join=report._currency_table_aml_join(column_group_options),
                tax_groups_condition=tax_groups_condition,
                tail_query=tail_query,
            ))

        self.env.cr.execute(SQL(" UNION ALL ").join(queries))
        return self._process_moves(self.env.cr.dictfetchall(), tax_group, options)

    def _process_moves(self, data_dict, tax_group, options):
        """ Process the data_dict and group the lines in four categories """
        lines_values = {}
        for values in data_dict:
            if values['move_id'] not in lines_values:
                lines_values[values['move_id']] = {
                    'name': values['move_name'],
                    values['column_group_key']: {
                        'column_group_key': values['column_group_key'],
                        'move_id': values['move_id'],
                        'move_name': values['move_name'],
                        'ref': values['move_ref'],
                        'invoice_number': values['invoice_number'],
                        'invoice_date': values['invoice_date'],
                        'partner_id': values['partner_name'],
                        'tax_id': values['vat'],
                    }
                }
            self._eval_report_grids_map(options, tax_group, values, column_values=lines_values[values['move_id']][values['column_group_key']])

        return self._filter_lines_with_values(options, tax_group, lines_values)

    def _get_report_line_move(self, report, options, move_id, line_values, parent_line_id):
        """ Format the given values to match the report line format. """
        report = self.env['account.report'].browse(options['report_id'])
        line_columns = self._get_line_column(report, options, line_values)
        line_id = report._get_generic_line_id('account.move', move_id, parent_line_id=parent_line_id)
        unfold_all = options['export_mode'] == 'print' or options.get('unfold_all')
        return {
            'id': line_id,
            'parent_id': parent_line_id,
            'name': line_values['name'],
            'unfoldable': True,
            'unfolded': line_id in options['unfolded_lines'] or unfold_all,
            'columns': line_columns,
            'level': 2,
            'caret_options': 'account.move',
            'expand_function': '_report_expand_unfoldable_line_l10n_vn_expand_move',
        }

    def _report_expand_unfoldable_line_l10n_vn_expand_move(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        """ Used to expand a move line and load the fourth level, being the account tax lines. """
        report = self.env['account.report'].browse(options['report_id'])
        month = report._parse_line_id(line_dict_id)[1][0]
        tax_group = report._parse_line_id(line_dict_id)[2][0]
        move_id = report._get_res_id_from_line_id(line_dict_id, 'account.move')
        lines_values = self._query_tax_lines(options, report, move_id, tax_group, month, offset)
        return self._get_report_expand_unfoldable_line_value(report, options, line_dict_id, progress, lines_values, report_line_method=self._get_report_line_tax)

    def _query_tax_lines(self, options, report, move_id, tax_group, month, offset):
        """ Query the values for the partner line.
        The move line will sum up the values for the different columns, while being filtered for the given month only.
        """
        limit = report.load_more_limit + 1 if report.load_more_limit and options['export_mode'] != 'print' else None
        end_date = fields.Date.from_string(month)
        start_date = date_utils.start_of(end_date, 'month')
        tax_groups = [grid for grids in options['tax_groups'][tax_group]['report_grids_map'].values() for grid in grids]
        queries = []
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            domain = [
                ('move_id.move_type', '=', options['move_type']),
                # Make sure to only fetch records that are in the parent's row month
                ('date', '>=', start_date),
                ('date', '<=', end_date),
                ('move_id', '=', move_id),
            ]
            query = report._get_report_query(column_group_options, date_scope="strict_range", domain=domain)
            tail_query = report._get_engine_query_tail(offset, limit)
            lang = self.env.user.lang or get_lang(self.env).code
            if self.pool['account.account.tag'].name.translate:
                account_tag_name = SQL("COALESCE(account_tag.name->>%(lang)s, account_tag.name->>'en_US')", lang=lang)
            else:
                account_tag_name = SQL.identifier('account_tag', 'name')
            tax_groups_condition = SQL("REGEXP_REPLACE(%(account_tag_name)s, '^[+-]', '') = ANY(%(tax_groups)s)",
                                       account_tag_name=account_tag_name,
                                       tax_groups=tax_groups)
            if self.pool['account.tax'].description.translate:
                account_tax_description = SQL("COALESCE(account_tax.description->>%(lang)s, account_tax.description->>'en_US')", lang=lang)
            else:
                account_tax_description = SQL.identifier('account_tax', 'description')
            queries.append(SQL(
                """
                  SELECT %(column_group_key)s                                                                               AS column_group_key,
                         account_tax.id                                                                                     AS tax_id,
                         REGEXP_REPLACE(%(account_tax_description)s, '(<([^>]+)>)', '', 'g')                                AS tax_description,
                         REGEXP_REPLACE(%(account_tag_name)s, '^[+-]', '')                                                  AS tag_name,
                         account_move_line.tax_base_amount                                                                  AS untaxed_amount,
                         SUM(%(balance_select)s
                             * CASE WHEN account_tag.tax_negate THEN -1 ELSE 1 END
                             * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                         )                                                                                                  AS balance
                    FROM %(table_references)s
                    JOIN account_account_tag_account_move_line_rel account_tag_rel ON account_tag_rel.account_move_line_id = account_move_line.id
                    JOIN account_account_tag account_tag ON account_tag.id = account_tag_rel.account_account_tag_id
                    JOIN account_tax account_tax ON account_tax.id = account_move_line.tax_line_id
                    %(currency_table_join)s
                   WHERE %(search_condition)s AND %(tax_groups_condition)s
                GROUP BY %(account_tag_name)s, account_tax.id, account_move_line.id
                %(tail_query)s
                """,
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                column_group_key=column_group_key,
                account_tax_description=account_tax_description,
                account_tag_name=account_tag_name,
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(column_group_options),
                search_condition=query.where_clause,
                tax_groups_condition=tax_groups_condition,
                tail_query=tail_query,
            ))

        self.env.cr.execute(SQL(" UNION ALL ").join(queries))
        return self._process_tax_lines(self.env.cr.dictfetchall(), tax_group, options)

    def _process_tax_lines(self, data_dict, tax_group, options):
        """ Taking in the values from the database, this will construct the column values by using the tax grid mapping
        set in the option of each report section.
        """
        lines_values = {}
        for values in data_dict:
            if values['tax_id'] not in lines_values:
                lines_values[values['tax_id']] = {
                    'name': values['tax_description'],
                    values['column_group_key']: {
                        'column_group_key': values['column_group_key'],
                        # Because we group by tax line, we need to find the untaxed amount from the tax
                        'untaxed_amount': values['untaxed_amount'],
                    }
                }
            self._eval_report_grids_map(options, tax_group, values, column_values=lines_values[values['tax_id']][values['column_group_key']])

        return self._filter_lines_with_values(options, tax_group, lines_values)

    def _get_report_line_tax(self, report, options, tax_id, line_values, parent_line_id):
        """ Format the given values to match the report line format. """
        line_columns = self._get_line_column(report, options, line_values)
        line_id = report._get_generic_line_id('account.tax', tax_id, parent_line_id=parent_line_id)
        return {
            'id': line_id,
            'parent_id': parent_line_id,
            'name': line_values['name'],
            'unfoldable': False,
            'unfolded': False,
            'columns': line_columns,
            'level': 3,
            'caret_options': 'account.tax',
        }

    def _build_grand_total_line(self, report, options):
        """ The grand total line is the sum of all values in the given reporting period. """
        queries = []
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            domain = [('move_id.move_type', '=', options['move_type'])]
            query = report._get_report_query(column_group_options, date_scope="strict_range", domain=domain)
            lang = self.env.user.lang or get_lang(self.env).code
            if self.pool['account.account.tag'].name.translate:
                account_tag_name = SQL("COALESCE(account_tag.name->>%(lang)s, account_tag.name->>'en_US')", lang=lang)
            else:
                account_tag_name = SQL.identifier('account_tag', 'name')
            queries.append(SQL(
                """
                  SELECT %(column_group_key)s                                                                               AS column_group_key,
                         REGEXP_REPLACE(%(account_tag_name)s, '^[+-]', '')                                                  AS tag_name,
                         SUM(%(balance_select)s
                             * CASE WHEN account_tag.tax_negate THEN -1 ELSE 1 END
                             * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                         )                                                                                                  AS balance
                    FROM %(table_references)s
                    JOIN account_account_tag_account_move_line_rel account_tag_rel ON account_tag_rel.account_move_line_id = account_move_line.id
                    JOIN account_account_tag account_tag ON account_tag.id = account_tag_rel.account_account_tag_id
                    %(currency_table_join)s
                   WHERE %(search_condition)s
                GROUP BY column_group_key, %(account_tag_name)s
                """,
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                column_group_key=column_group_key,
                account_tag_name=account_tag_name,
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(column_group_options),
                search_condition=query.where_clause,
            ))
        self.env.cr.execute(SQL(" UNION ALL ").join(queries))
        results = self.env.cr.dictfetchall()
        return results and self._get_report_line_grand_total(report, options, self._process_grand_total_line(report, options, results))

    def _process_grand_total_line(self, report, options, data_dict):
        """ Taking in the values from the database, this will construct the column values by using the tax grid mapping
        set in the option of each report section.
        """
        lines_values = {}
        for values in data_dict:
            if values['column_group_key'] not in lines_values:
                lines_values[values['column_group_key']] = lines_values
            # Sum the balances on the right expression label.
            # We use a map of tax grids to do that easily
            for tax_group in options['tax_groups']:
                self._eval_report_grids_map(options, tax_group, values, column_values=lines_values[values['column_group_key']])
        return lines_values

    def _get_report_line_grand_total(self, report, options, data):
        """ Format the given values to match the report line format. """
        return {
            'id': report._get_generic_line_id('', '', markup='grand_total'),
            'name': _('Grand Total'),
            'unfoldable': False,
            'unfolded': False,
            'columns': self._get_line_column(report, options, data),
            'level': 0,
        }

    def _get_report_expand_unfoldable_line_value(self, report, options, line_dict_id, progress, lines_values, *, report_line_method):
        lines = []
        has_more = False
        treated_results_count = 0
        next_progress = progress

        for line_key, line_values in lines_values.items():
            if options['export_mode'] != 'print' and report.load_more_limit and treated_results_count == report.load_more_limit:
                # We loaded one more than the limit on purpose: this way we know we need a "load more" line
                has_more = True
                break

            new_line = report_line_method(report, options, line_key, line_values, parent_line_id=line_dict_id)
            lines.append(new_line)
            next_progress = {
                column['column_group_key']: line_col.get('no_format', 0)
                for column, line_col in zip(options['columns'], new_line['columns'])
                if column['expression_label'] == 'balance'
            }
            treated_results_count += 1

        return {
            'lines': lines,
            'offset_increment': treated_results_count,
            'has_more': has_more,
            'progress': next_progress,
        }

    def _get_line_column(self, report, options, data):
        line_columns = []
        for column in options['columns']:
            col_value = data[column['column_group_key']].get(column['expression_label'])
            line_columns.append(report._build_column_dict(
                col_value=col_value or '',
                col_data=column,
                options=options,
            ))
        return line_columns

    def _eval_report_grids_map(self, options, tax_group, data, *, column_values):
        """ Evaluate the report grids map for the given tax group and lines values. """
        report_grids_map = options['tax_groups'][tax_group]['report_grids_map']
        for expression_label, grids in report_grids_map.items():
            if expression_label not in column_values:
                column_values[expression_label] = 0
            if data['tag_name'] in grids:  # In this report, we always sum, so it's easy
                column_values[expression_label] += data['balance']

    def _filter_lines_with_values(self, options, tax_group, lines_values, ignored_grids=[]):
        lines_with_values = {}
        report_grids_map = options['tax_groups'][tax_group]['report_grids_map']
        for line, value in lines_values.items():
            for column_group_key in options['column_groups']:
                if any(value[column_group_key][grid] != 0 for grid in report_grids_map if grid not in ignored_grids):
                    lines_with_values[line] = value

        return lines_with_values


class SalesTaxCustomHandler(models.AbstractModel):
    _name = 'l10n_vn.sales.tax.report.handler'
    _inherit = 'l10n_vn.tax.report.handler'
    _description = 'Taxes Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options.update({
            'move_type': 'out_invoice',
            'tax_groups': {
                'tax_0': {
                    'name': _('VAT on sales of goods and services 0%'),
                    'report_grids_map': {
                        'untaxed_amount': ["Untaxed sales of goods and services taxed 0%"],
                        'tax_amount': [],
                    },
                },
                'tax_5': {
                    'name': _('VAT on sales of goods and services 5%'),
                    'report_grids_map': {
                        'untaxed_amount': ["Untaxed sales of goods and services taxed 5%"],
                        'tax_amount': ["VAT on sales of goods and services 5%"],
                    },
                },
                'tax_8': {
                    'name': _('VAT on sales of goods and services 8%'),
                    'report_grids_map': {
                        'untaxed_amount': ["Untaxed sales of goods and services taxed 8%"],
                        'tax_amount': ["VAT on sales of goods and services 8%"],
                    },
                },
                'tax_10': {
                    'name': _('VAT on sales of goods and services 10%'),
                    'report_grids_map': {
                        'untaxed_amount': ["Untaxed sales of goods and services taxed 10%"],
                        'tax_amount': ["VAT on sales of goods and services 10%"],
                    }
                },
                'tax_exempt': {
                    'name': _('VAT Exemption on sales of goods and services'),
                    'report_grids_map': {
                        'untaxed_amount': ["Untaxed sales of goods and services taxed VAT Exemption"],
                        'tax_amount': [],
                    }
                },
            }
        })


class PurchaseTaxCustomHandler(models.AbstractModel):
    _name = 'l10n_vn.purchase.tax.report.handler'
    _inherit = 'l10n_vn.tax.report.handler'
    _description = 'Taxes Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options.update({
            'move_type': 'in_invoice',
            'tax_groups': {
                'tax_0': {
                    'name': _('VAT on purchase of goods and services 0%'),
                    'report_grids_map': {
                        'untaxed_amount': ["Untaxed Purchase of Goods and Services taxed 0%", "tax_purchase_import_0_base"],
                        'tax_amount': [],
                    },
                },
                'tax_5': {
                    'name': _('VAT on purchase of goods and services 5%'),
                    'report_grids_map': {
                        'untaxed_amount': ["Untaxed Purchase of Goods and Services taxed 5%", "tax_purchase_import_5_base"],
                        'tax_amount': ["VAT on purchase of goods and services 5%", "tax_purchase_import_5"],
                    },
                },
                'tax_8': {
                    'name': _('VAT on purchase of goods and services 8%'),
                    'report_grids_map': {
                        'untaxed_amount': ["Untaxed Purchase of Goods and Services taxed 8%", "tax_purchase_import_8_base"],
                        'tax_amount': ["VAT on purchase of goods and services 8%", "tax_purchase_import_8"],
                    },
                },
                'tax_10': {
                    'name': _('VAT on purchase of goods and services 10%'),
                    'report_grids_map': {
                        'untaxed_amount': ["Untaxed Purchase of Goods and Services taxed 10%", "tax_purchase_import_10_base"],
                        'tax_amount': ["VAT on purchase of goods and services 10%", "tax_purchase_import_10"],
                    }
                },
                'tax_exempt': {
                    'name': _('VAT on Purchase of Goods and Services Tax Exempt'),
                    'report_grids_map': {
                        'untaxed_amount': ["Untaxed Purchase of Goods and Services taxed VAT Exemption"],
                        'tax_amount': [],
                    }
                },
            }
        })
