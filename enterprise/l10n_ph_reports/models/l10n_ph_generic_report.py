# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, models
from odoo.osv import expression
from odoo.tools.sql import SQL


class L10nPhGenericCustomHandler(models.AbstractModel):
    _name = 'l10n_ph.generic.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Philippines Generic Report Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        report_lines = self._build_month_lines(report, options)
        if grand_total_line := self._build_grand_total_line(report, options):
            report_lines.append(grand_total_line)

        # Inject sequences on the dynamic lines
        return [(0, line) for line in report_lines]

    def _get_options_domain(self, options):
        options_domain = []
        if 'journal_type' in options:
            if options['journal_type'] == 'sale':
                payment_type = 'inbound'
                opposite_payment_type = 'outbound'
                credit_note_type = 'out_refund'
                move_types = self.env['account.move'].get_sale_types(include_receipts=True)
            else:
                payment_type = 'outbound'
                opposite_payment_type = 'inbound'
                credit_note_type = 'in_refund'
                move_types = self.env['account.move'].get_purchase_types(include_receipts=True)
            options_domain = [("move_id.move_type", "in", move_types)]
            origin_payment_domain_invoice = expression.AND([
                [("invoice_ids.move_type", "in", move_types)],
                [("payment_type", "=", payment_type)],
            ])
            options_domain = expression.OR([options_domain, [("move_id.origin_payment_id", "any", origin_payment_domain_invoice)]])
            origin_payment_domain_credit_note = expression.AND([
                [("invoice_ids.move_type", "=", credit_note_type)],
                [("payment_type", "=", opposite_payment_type)],
            ])
            options_domain = expression.OR([options_domain, [("move_id.origin_payment_id", "any", origin_payment_domain_credit_note)]])
        if 'include_no_tin' in options and not options['include_no_tin']:
            options_domain = expression.AND([options_domain, [("move_id.partner_id.vat", "!=", False)]])
        return options_domain

    def _get_report_query(self, report, column_group_options, with_base_lines=True, with_tax_lines=True, extra_domain=None):
        """
        Build on top of the query from account_report._get_report_query in order to add generic conditions and joins.
        This will add WHERE for the extra options specific to our PH reports, as well as joins providing correct access
        to account_tax and account_tag for each line.
        Using this will ensure that the query properly support withholding taxes on both invoices and payment, as well as
        other taxes as needed, and will always correctly filter based on the options.
        """
        options_domain = self._get_options_domain(column_group_options)
        if extra_domain:
            options_domain = expression.AND([options_domain, extra_domain])
        query = report._get_report_query(column_group_options, date_scope="strict_range", domain=options_domain)

        query.add_join(
            kind='JOIN',
            alias='account_tag_rel',
            table='account_account_tag_account_move_line_rel',
            condition=SQL("account_tag_rel.account_move_line_id = account_move_line.id"),
        )
        query.add_join(
            kind='JOIN',
            alias='account_tag',
            table='account_account_tag',
            condition=SQL("account_tag.id = account_tag_rel.account_account_tag_id"),
        )
        table_join_conditions = []
        if with_base_lines:
            query.add_join(
                kind='LEFT JOIN',
                alias='tax_rel',
                table='account_move_line_account_tax_rel',
                condition=SQL("account_move_line.id = tax_rel.account_move_line_id"),
            )
            table_join_conditions.append(SQL("account_tax.id = tax_rel.account_tax_id"))
        if with_tax_lines:
            table_join_conditions.append(SQL("account_tax.id = account_move_line.tax_line_id"))
        query.add_join(
            kind='JOIN',
            alias='account_tax',
            table='account_tax',
            condition=SQL(" OR ").join(table_join_conditions),
        )
        # Otherwise you could have duplicated rows as the tax & tags are not "linked" in the joins.
        query.add_where("""EXISTS (
            SELECT 1
            FROM account_tax_repartition_line atrl
            JOIN account_account_tag_account_tax_repartition_line_rel aatatrlr ON atrl.id = aatatrlr.account_tax_repartition_line_id
            WHERE atrl.tax_id = account_tax.id AND aatatrlr.account_account_tag_id = account_tag.id
        )""")

        return query

    def _build_month_lines(self, report, options):
        # TO OVERRIDE
        return []

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

    def _get_line_columns(self, report, options, data):
        line_columns = []
        for column in options['columns']:
            col_value = data[column['column_group_key']].get(column['expression_label'])
            line_columns.append(report._build_column_dict(
                col_value=col_value or '',
                col_data=column,
                options=options,
            ))
        return line_columns

    def _eval_report_grids_map(self, options, data, *, column_values):
        """ Evaluate the report grids map for the given tax group and lines values. """
        # Sum the balances on the right expression label.
        # We use a map of tax grids to do that easily
        report_grids_map = options['report_grids_map']
        for expression_label, grids in report_grids_map.items():
            if expression_label not in column_values:
                column_values[expression_label] = 0
            if data['tag_name'] in grids:  # In this report, we always sum, so it's easy
                column_values[expression_label] += data['balance']

    def _filter_lines_with_values(self, options, lines_values, ignored_grids=[]):
        lines_with_values = {}
        report_grids_map = options['report_grids_map']
        for line, value in lines_values.items():
            for column_group_key in options['column_groups']:
                if any(value[column_group_key][grid] != 0 for grid in report_grids_map if grid not in ignored_grids):
                    lines_with_values[line] = value

        return lines_with_values

    def _get_grand_total_line_domain(self, options):
        # Note: no longer used, removed in 19
        if options['journal_type'] == 'sale':
            move_types = self.env['account.move'].get_sale_types(include_receipts=True)
        else:
            move_types = self.env['account.move'].get_purchase_types(include_receipts=True)
        return [('move_id.move_type', 'in', move_types)]

    # Grand total
    def _build_grand_total_line(self, report, options):
        """ The grand total line is the sum of all values in the given reporting period. """
        queries = []
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            query = self._get_report_query(report, column_group_options)
            account_tag_name = self.env['account.account.tag']._field_to_sql('account_tag', 'name', query)
            queries.append(SQL(
                """
                  SELECT %(column_group_key)s                                                                               AS column_group_key,
                         REGEXP_REPLACE(%(account_tag_name)s, '^[+-]', '')                                                  AS tag_name,
                         SUM(%(balance_select)s
                             * CASE WHEN account_tag.tax_negate THEN -1 ELSE 1 END
                             * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                         )                                                                                                  AS balance
                    FROM %(table_references)s
                    %(currency_table_join)s
                   WHERE %(search_condition)s
                GROUP BY column_group_key, %(account_tag_name)s
                """,
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                column_group_key=column_group_key,
                account_tag_name=account_tag_name,
                currency_table_join=report._currency_table_aml_join(column_group_options),
                table_references=query.from_clause,
                search_condition=query.where_clause,
            ))
        self.env.cr.execute(SQL(" UNION ALL ").join(queries))
        results = self.env.cr.dictfetchall()
        return results and self._get_report_line_grand_total(report, options, self._process_grand_total_line(results, options))

    def _process_grand_total_line(self, data_dict, options):
        """ Taking in the values from the database, this will construct the column values by using the tax grid mapping
        set in the option of each report section.
        """
        lines_values = {}
        for values in data_dict:
            if values['column_group_key'] not in lines_values:
                lines_values[values['column_group_key']] = lines_values
            self._eval_report_grids_map(options, values, column_values=lines_values[values['column_group_key']])
        return lines_values

    def _get_report_line_grand_total(self, report, options, res):
        """ Format the given values to match the report line format. """
        line_columns = self._get_line_columns(report, options, res)
        line_id = report._get_generic_line_id('', '', markup='grand_total')
        return {
            'id': line_id,
            'name': _('Grand Total'),
            'unfoldable': False,
            'unfolded': False,
            'columns': line_columns,
            'level': 0,
        }
