# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.tools import format_date, date_utils, get_lang
from collections import defaultdict
from odoo.exceptions import UserError, RedirectWarning

import json
import datetime


class JournalReportCustomHandler(models.AbstractModel):
    _name = 'account.journal.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Journal Report Custom Handler'

    def _get_custom_display_config(self):
        return {
            'css_custom_class': 'journal_report',
            'components': {
                'AccountReportLine': 'account_reports.JournalReportLine',
            },
            'templates': {
                'AccountReportFilters': 'account_reports.JournalReportFilters',
                'AccountReportHeader': 'account_reports.JournalReportHeader',
                'AccountReportLineName': 'account_reports.JournalReportLineName',
            },
            'pdf_export': {
                'pdf_export_main_table_header': 'account_reports.journal_report_pdf_export_main_table_header',
                'pdf_export_filters': 'account_reports.journal_report_pdf_export_filters',
                'pdf_export_main_table_body': 'account_reports.journal_report_pdf_export_main_table_body',
            },
        }

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        """ Returns the first level of the report, journal lines. """
        journal_query_res = self._query_journal(options)

        # Set the options with the journals that should be unfolded by default.
        lines = []
        unfolded_journals = []
        for journal_index, (journal_id, journal_vals) in enumerate(journal_query_res.items()):
            journal_key = report._get_generic_line_id('account.journal', journal_id)
            unfolded = journal_key in options.get('unfolded_lines') or options.get('unfold_all')
            if unfolded:
                unfolded_journals.append(unfolded)
            lines.append(self._get_journal_line(options, journal_key, journal_vals, unfolded, is_first_journal=len(unfolded_journals) == 1))
        global_tax_summary_lines = self._get_global_tax_summary_lines(options)
        lines.extend(global_tax_summary_lines)

        return [(0, line) for line in lines]

    def _get_global_tax_summary_lines(self, options):
        # It is faster to first check that we need a tax section; this avoids computing a tax report for nothing.
        aml_has_tax_domain = [('tax_ids', '!=', False)]
        if options.get('date', {}).get('date_from'):
            aml_has_tax_domain.append(('date', '>=', options['date']['date_from']))
        if options.get('date', {}).get('date_to'):
            aml_has_tax_domain.append(('date', '<=', options['date']['date_to']))
        has_tax = bool(self.env['account.move.line'].search_count(aml_has_tax_domain, limit=1))
        if not has_tax:
            return []

        report = self.env.ref('account_reports.journal_report')
        tax_data = {
            'date_from': options.get('date', {}).get('date_from'),
            'date_to': options.get('date', {}).get('date_to'),
        }
        # This is a special line with a special template to render it.
        # It will contain two tables, which are the tax report and tax grid summary sections.
        tax_report_lines = self._get_generic_tax_summary_for_sections(options, tax_data)

        tax_non_deductible_column = any(line.get('tax_non_deductible_no_format') for lines_per_country in tax_report_lines.values() for line in lines_per_country)
        tax_deductible_column = any(line.get('tax_deductible_no_format') for lines_per_country in tax_report_lines.values() for line in lines_per_country)
        tax_due_column = any(line.get('tax_due_no_format') for lines_per_country in tax_report_lines.values() for line in lines_per_country)
        extra_columns = int(tax_non_deductible_column) + int(tax_deductible_column) + int(tax_due_column)

        tax_grid_summary_lines = self._get_tax_grids_summary(options, tax_data)

        if not tax_report_lines and not tax_grid_summary_lines:
            return []

        return [
            {
                'id': report._get_generic_line_id(False, False, markup='tax_report_section_heading'),
                'name': _('Global Tax Summary'),
                'level': 0,
                'columns': [],
                'unfoldable': False,
                'page_break': True,
                'colspan': len(options['columns']) + 1  # We want it to take the whole line. It makes it easier to unfold it.
            },
            {
                'id': report._get_generic_line_id(False, False, markup='tax_report_section'),
                'name': '',
                'is_tax_section_line': True,
                'tax_report_lines': tax_report_lines,
                'tax_non_deductible_column': tax_non_deductible_column,
                'tax_deductible_column': tax_deductible_column,
                'tax_due_column': tax_due_column,
                'extra_columns': extra_columns,
                'tax_grid_summary_lines': tax_grid_summary_lines,
                'date_from': tax_data['date_from'],
                'date_to': tax_data['date_to'],
                'columns': [],
                'colspan': len(options['columns']) + 1,
                'level': 3,
                'class': 'o_account_reports_ja_subtable',
            },
        ]

    def _custom_options_initializer(self, report, options, previous_options=None):
        """ Initialize the options for the journal report. """
        # This dictionnary makes it possible to make options unavailable for the report. The structure of the dictionnary is
        # { <type: str - Name of the disabled option>: <type: tuple - tuple containing striclty two elements, a and b> }
        # with a <type: list - list of the keys that must be reached in the options dictionnary to get the value to test>
        # and b <type: list - list of the values that are authorized for the said option>
        restricted_options = {
            _("Analytic Accounts Groupby"): (['analytic_accounts_groupby'], []),
            _("Analytic Plans Groupby"): (['analytic_plans_groupby'], []),
            _("Horizontal Grouping"): (['selected_horizontal_group_id'], []),
            _("Period comparison"): (['comparison', 'filter'], ['no_comparison']),
        }
        for name, (path, authorized_value) in restricted_options.items():
            option = options
            while path and option:
                option = option.get(path.pop(0))

            if option and (not authorized_value or option not in authorized_value):
                raise UserError(name + _(" is not supported by the Journal Report"))

        super()._custom_options_initializer(report, options, previous_options=previous_options)
        # Initialise the custom options for this report.
        custom_filters = {
            'sort_by_date': False,
            'group_by_months': False,
            'show_payment_lines': True,
        }
        for name, default_val in custom_filters.items():
            options[name] = (previous_options or {}).get(name, default_val)

        # if no journal is selected (so, all are) and no other line is unfolded, unfold the first journal
        # Ensure that all selected journals are unfolded by default
        available_journal_ids = {j['id'] for j in options['journals']}
        selected_journal_ids = {j['id'] for j in options['journals'] if j.get('selected', False)}
        any_unfolded_journal = any(report._parse_line_id(unfolded_line)[-1][1] == 'account.journal' for unfolded_line in options['unfolded_lines'] if report._parse_line_id(unfolded_line)[-1][2] in available_journal_ids)
        unfolded_lines = options['unfolded_lines']
        if selected_journal_ids:
            for journal_id in selected_journal_ids:
                line_id = report._get_generic_line_id('account.journal', journal_id)
                if line_id not in unfolded_lines:
                    unfolded_lines.append(line_id)
        elif not any_unfolded_journal and not options['export_mode'] == 'print':
            line_id = report._get_generic_line_id('account.journal', next(iter(available_journal_ids)))
            if line_id not in unfolded_lines:
                unfolded_lines.append(line_id)

        if self.user_has_groups('base.group_multi_currency'):
            options['multi_currency'] = True

    def _custom_line_postprocessor(self, report, options, lines, warnings=None):
        if options['export_mode'] != 'print':
            return lines
        new_lines = []
        for line in lines:
            model_info = self.env['account.report']._get_model_info_from_id(line['id'])
            if model_info[0] == 'account.journal' and line.get('unfolded', False) or model_info[0] != 'account.journal':
                new_lines.append(line)
        return new_lines

    def _query_journal(self, options):
        params = []
        queries = []
        report = self.env.ref('account_reports.journal_report')
        if self.pool['account.journal'].name.translate:
            lang = self.env.user.lang or get_lang(self.env).code
            j_name = f"COALESCE(j.name->>'{lang}', j.name->>'en_US')"
        else:
            j_name = "j.name"

        for column_group_key, options_group in report._split_options_per_column_group(options).items():
            tables, where_clause, where_params = report._query_get(options_group, 'strict_range')
            params.append(column_group_key)
            params += where_params
            queries.append(f"""
                SELECT
                    %s as column_group_key,
                    j.id,
                    {j_name} as name,
                    j.code,
                    j.type,
                    j.currency_id,
                    journal_curr.name as currency_name,
                    cp.currency_id as company_currency
                FROM {tables}
                JOIN account_journal j ON j.id = account_move_line.journal_id
                JOIN res_company cp ON cp.id = j.company_id
                LEFT JOIN res_currency journal_curr on journal_curr.id = j.currency_id
                WHERE {where_clause}
                GROUP BY
                    j.id, {j_name}, j.code, j.type, j.currency_id, journal_curr.name, cp.currency_id
                ORDER BY j.id
            """)

        rslt = {}
        self._cr.execute(" UNION ALL ".join(queries), params)
        for journal_res in self._cr.dictfetchall():
            if journal_res['id'] not in rslt:
                rslt[journal_res['id']] = {col_group_key: {} for col_group_key in options['column_groups']}
            rslt[journal_res['id']][journal_res['column_group_key']] = journal_res

        return rslt

    ##########################################################################
    # Get lines methods
    ##########################################################################

    def _get_lines_for_group(self, options, parent_line_id, journal, progress, offset):
        """ Create the report lines for a group of moves. A group is either a journal, or a month if the report is grouped by month."""

        def cumulate_balance(line, current_balances, is_unreconciled_payment):
            # For bank journals, we want to cumulate the balances and display their evolution line by line until the end.
            for column_group_key in options['column_groups']:
                # For bank journals, we want to cumulate the balances and display their evolution line by line until the end.
                if journal.type == 'bank' and line[column_group_key]['account_type'] not in ('liability_credit_card', 'asset_cash') and not is_unreconciled_payment:
                    current_balances[column_group_key] += -line[column_group_key]['balance']
                    line[column_group_key]['cumulated_balance'] = current_balances[column_group_key]

        lines, after_load_more_lines = [], []
        current_balances, next_progress = {}, {}
        # Treated result count also consider the lines not rendered in the report, and is used for the query offset.
        # Rendered line count does not consider the lines not rendered, and allows to stop rendering more when the quota has been reached.
        treated_results_count = 0
        has_more_lines = False

        eval_dict = self._query_aml(options, offset, journal)
        if offset == 0:
            lines.append(self._get_columns_line(options, parent_line_id, journal.type))

        if journal.type == 'bank':
            # Get initial balance, only if the journal is of type 'bank', and we have no offset yet (first unfolding)
            if offset == 0:
                if journal.type == 'bank':
                    init_balance_by_col_group = self._get_journal_initial_balance(options, journal.id)
                    initial_balance_line = self._get_journal_balance_line(
                        options, parent_line_id, init_balance_by_col_group, is_starting_balance=True)
                    if initial_balance_line:
                        lines.append(initial_balance_line)
                        # For the first expansion of the line, the initial balance line gives the progress
                        progress = {
                            column['column_group_key']: line_col.get('no_format', 0.0)
                            for column, line_col in zip(options['columns'], initial_balance_line['columns'])
                            if column['expression_label'] == 'additional_col_1'
                        }
            # Weither we just fetched them or not, the balance is now in the progress.
            for column_group_key in options['column_groups']:
                current_balances[column_group_key] = progress.get(column_group_key, 0.0)

        # Group the lines by moves, to simplify the following code.
        line_dict_grouped = self._group_lines_by_move(options, eval_dict, parent_line_id)

        report = self.env.ref('account_reports.journal_report')

        treated_amls_count = 0
        for move_key, move_line_vals_list in line_dict_grouped.items():
            # All move lines for a move will share static values, like if the move is multicurrency, the journal,..
            # These can be fetched using any column groups or lines for this move.
            first_move_line = move_line_vals_list[0]
            general_line_vals = next(col_group_val for col_group_val in first_move_line.values())
            if report.load_more_limit and len(move_line_vals_list) + treated_amls_count > report.load_more_limit and options['export_mode'] != 'print':
                # This element won't generate a line now, but we use it to know that we'll need to add a load_more line.
                has_more_lines = True
                if treated_amls_count == 0:
                    # A single move lines count exceed the load more limit, we need to raise to inform the user
                    msg = _("The 'load more limit' setting of this report is too low to display all the lines of the entry you're trying to show.")
                    if self.env.user.has_group('account.group_account_manager'):
                        action = {
                            "view_mode": "form",
                            "res_model": "account.report",
                            "type": "ir.actions.act_window",
                            "res_id" : report.id,
                            "views": [[self.env.ref("account_reports.account_report_form").id, "form"]],
                        }
                        title = _('Go to report configuration')

                        raise RedirectWarning(msg, action, title)
                    raise UserError(msg)
                break
            is_unreconciled_payment = journal.type == 'bank' and not any(line for line in move_line_vals_list if next(col_group_val for col_group_val in line.values())['account_type'] in ('liability_credit_card', 'asset_cash'))
            if journal.type == 'bank':
                cumulate_balance(first_move_line, current_balances, is_unreconciled_payment)

            # Do not display payments move on bank journal if the options isn't enabled.
            if not options.get('show_payment_lines') and is_unreconciled_payment:
                treated_results_count += len(move_line_vals_list)   # used to get the offset
                continue
            # Create the first line separately, as we want to give it some specific behavior and styling
            lines.append(self._get_first_move_line(options, parent_line_id, move_key, first_move_line, is_unreconciled_payment))
            treated_amls_count += len(move_line_vals_list)
            treated_results_count += 1
            for line_index, move_line_vals in enumerate(move_line_vals_list[1:]):
                if journal.type == 'bank':
                    cumulate_balance(move_line_vals, current_balances, is_unreconciled_payment)
                line = self._get_aml_line(options, parent_line_id, move_line_vals, line_index, journal, is_unreconciled_payment)
                treated_results_count += 1
                if line:
                    lines.append(line)

                multicurrency_name = self._get_aml_line_name(options, journal, -1, first_move_line, is_unreconciled_payment)
                # Add a currency line if we have a foreign currency on the move but no place to put this info beforehand in the name of a line.
                # This can happen if we have two lines only and a ref: the ref take the name of the second line and we need a new one for the currency.
                if general_line_vals['is_multicurrency'] \
                        and len(move_line_vals_list) == 2 \
                        and self.user_has_groups('base.group_multi_currency') \
                        and lines[-1]['name'] != multicurrency_name \
                        and journal.type != 'bank':
                    lines.append({
                        'id': report._get_generic_line_id('account.move.line', general_line_vals['move_id'], parent_line_id=parent_line_id, markup='amount_currency_total'),
                        'name': multicurrency_name,
                        'level': 3,
                        'parent_id': parent_line_id,
                        'columns': [{} for column in options['columns']],
                    })
                if journal.type == 'bank':
                    next_progress = {
                        column['column_group_key']: line_col.get('no_format', 0.0)
                        for column, line_col in zip(options['columns'], lines[-1]['columns'])
                        if column['expression_label'] == 'additional_col_1'
                    }
        # If we have no offsets, check if we can create a tax line: This line will contain two tables, one for the tax summary and one for the tax grid summary.
        if offset == 0:
            # It is faster to first check that we need a tax section; this avoids computing a tax report for nothing.
            aml_has_tax_domain = [('journal_id', '=', journal.id), ('tax_ids', '!=', False)]
            if options.get('date', {}).get('date_from'):
                aml_has_tax_domain.append(('date', '>=', options['date']['date_from']))
            if options.get('date', {}).get('date_to'):
                aml_has_tax_domain.append(('date', '<=', options['date']['date_to']))
            journal_has_tax = bool(self.env['account.move.line'].search_count(aml_has_tax_domain, limit=1))
            if journal_has_tax:
                tax_data = {
                    'date_from': options.get('date', {}).get('date_from'),
                    'date_to': options.get('date', {}).get('date_to'),
                    'journal_id': journal.id,
                    'journal_type': journal.type,
                }
                # This is a special line with a special template to render it.
                # It will contain two tables, which are the tax report and tax grid summary sections.
                tax_report_lines = self._get_generic_tax_summary_for_sections(options, tax_data)

                tax_non_deductible_column = any(line.get('tax_non_deductible_no_format') for country in tax_report_lines.values() for line in country)
                tax_deductible_column = any(line.get('tax_deductible_no_format') for country in tax_report_lines.values() for line in country)
                tax_due_column = any(line.get('tax_due_no_format') for country in tax_report_lines.values() for line in country)
                extra_columns = int(tax_non_deductible_column) + int(tax_deductible_column) + int(tax_due_column)

                tax_grid_summary_lines = self._get_tax_grids_summary(options, tax_data)
                if tax_report_lines or tax_grid_summary_lines:
                    after_load_more_lines.append({
                        'id': report._get_generic_line_id(False, False, parent_line_id=parent_line_id, markup='tax_report_section'),
                        'name': '',
                        'parent_id': parent_line_id,
                        'journal_id': journal.id,
                        'is_tax_section_line': True,
                        'tax_report_lines': tax_report_lines,
                        'tax_non_deductible_column': tax_non_deductible_column,
                        'tax_deductible_column': tax_deductible_column,
                        'tax_due_column': tax_due_column,
                        'extra_columns': extra_columns,
                        'tax_grid_summary_lines': tax_grid_summary_lines,
                        'date_from': tax_data['date_from'],
                        'date_to': tax_data['date_to'],
                        'columns': [],
                        'colspan': len(options['columns']) + 1,
                        'level': 3,
                    })

        return lines, after_load_more_lines, has_more_lines, treated_results_count, next_progress, current_balances

    def _get_columns_line(self, options, parent_key, journal_type):
        """ returns the line displaying the columns used by the journal.
        The report isn't using the table header, as different journal type needs different columns.

        :param options: The report options
        :param parent_key: the key of the parent line, journal or month
        :param journal_type: the journal type
        """
        columns = []
        has_multicurrency = self.user_has_groups('base.group_multi_currency')
        report = self.env['account.report'].browse(options['report_id'])

        # code assumes additional_col_1 & additional_col_2 are last columns, but since no sequences are set on columns,
        # it might happen (i.e. after db update from 16 to 17) that that's not the case.
        options['columns'] = sorted(options['columns'], key=lambda col: col.get('expression_label') in ['additional_col_1', 'additional_col_2'])
        for column in options['columns']:
            if column['expression_label'] == 'additional_col_1':
                if journal_type in ['sale', 'purchase']:
                    col_value = _('Taxes')
                elif journal_type == 'bank':
                    col_value = _('Balance')
                else:
                    col_value = ''
            elif column['expression_label'] == 'additional_col_2':
                if journal_type in ['sale', 'purchase']:
                    col_value = _('Tax Grids')
                elif journal_type == 'bank' and has_multicurrency:
                    col_value = _('Amount In Currency')
                else:
                    col_value = ''
            elif column['expression_label'] == 'invoice_date':
                col_value = column['name'] if journal_type in ['sale', 'purchase', 'general'] else ''

            else:
                col_value = column['name']

            columns.append(report._build_column_dict(col_value, column, options=options))

        return {
            'id': report._get_generic_line_id(None, None, parent_line_id=parent_key, markup='headers'),
            'name': _('Name'),
            'columns': columns,
            'level': 3,
            'parent_id': parent_key,
        }

    def _get_journal_line(self, options, line_id, eval_dict, unfolded, is_first_journal):
        """ returns the line that is representing a journal in the report.

        :param options: The report options
        :param line_id: The line id for this journal
        :param eval_dict: The values for this journal
        :param is_first_journal: If this is the first journal in the report or not. Additional journals will have a page break used when printing in PDF.
        """
        # The column group does not matter for these values: any group will share the same journal.
        journal_vals = next(col_group_val for col_group_val in eval_dict.values())
        has_foreign_currency = journal_vals['currency_id'] and journal_vals['currency_id'] != journal_vals['company_currency']
        return {
            'id': line_id,
            'name': f"{journal_vals['name']} ({journal_vals['code']}){' ' + journal_vals['currency_name'] if has_foreign_currency else ''}",
            'level': 0,
            'columns': [],
            'unfoldable': True,
            'unfolded': unfolded,
            'journal_id': journal_vals['id'],
            'journal_type': journal_vals['type'],
            'page_break': unfolded and not is_first_journal,
            'expand_function': '_report_expand_unfoldable_line_journal_report' if not options['group_by_months'] else '_report_expand_unfoldable_line_journal_report_expand_journal_line_by_month',
            'colspan': len(options['columns']) + 1  # We want it to take the whole line. It makes it easier to unfold it.
        }

    def _report_expand_unfoldable_line_journal_report(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data):
        report = self.env['account.report'].browse(options['report_id'])
        new_options = options.copy()
        if options['group_by_months']:
            # If grouped by month, we get the journal info from the parent line.
            parsed_line_id = report._parse_line_id(line_dict_id)
            model = parsed_line_id[-2][1]
            journal_id = parsed_line_id[-2][2]

            # We force the date in the options to be the ones for this month.
            year, month = parsed_line_id[-1][0].split(' ')[1:]
            date = datetime.date(int(year), int(month), 1)
            new_options['date'] = {
                'mode': 'range',
                'date_from': date_utils.start_of(date, 'month'),
                'date_to': date_utils.end_of(date, 'month'),
            }
        else:
            model, journal_id = report._get_model_info_from_id(line_dict_id)

        if model != 'account.journal':
            raise UserError(_('Trying to use the journal line expand function on a line that is not linked to a journal.'))

        lines = []
        journal = self.env[model].browse(journal_id)

        # Get move lines
        new_lines, after_load_more_lines, has_more, treated_results_count, next_progress, ending_balance_by_col_group = self._get_lines_for_group(new_options, line_dict_id, journal, progress, offset)
        lines.extend(new_lines)
        if not has_more and journal.type == 'bank' and ending_balance_by_col_group:
            ending_balance_line = self._get_journal_balance_line(new_options, line_dict_id, ending_balance_by_col_group, is_starting_balance=False)
            if ending_balance_line:
                lines.append(ending_balance_line)

        return {
            'lines': lines,
            'after_load_more_lines': after_load_more_lines,
            'offset_increment': treated_results_count,
            'has_more': has_more,
            'progress': next_progress,
        }

    def _report_expand_unfoldable_line_journal_report_expand_journal_line_by_month(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data):
        model, record_id = self.env['account.report']._get_model_info_from_id(line_dict_id)

        if model != 'account.journal':
            raise UserError(_('Trying to use the journal line expand function on a line that is not linked to a journal.'))

        lines = []
        journal = self.env[model].browse(record_id)
        aml_results = self._query_months(options, line_dict_id, offset, journal)
        lines.extend(self._get_month_lines(options, line_dict_id, aml_results, progress, offset))

        return {
            'lines': lines,
        }

    def _get_month_lines(self, options, line_dict_id, aml_results, progress, offset):
        report = self.env['account.report'].browse(options['report_id'])
        lines = []

        for month, months_with_vals in aml_results.items():
            for month_vals in months_with_vals.values():
                date = datetime.datetime.strptime(month, '%m %Y').date()
                line_id = report._get_generic_line_id(None, None, parent_line_id=line_dict_id, markup=f'month_line {date.year} {date.month}')
                lines.append({
                    'id': line_id,
                    'name': month_vals['display_month'],
                    'level': 2,
                    'columns': [],
                    'unfoldable': True,
                    'unfolded': line_id in options.get('unfolded_lines') or options.get('unfold_all'),
                    'parent_id': line_dict_id,
                    'colspan': len(options['columns']) + 1,
                    'expand_function': '_report_expand_unfoldable_line_journal_report',
                })
        return lines

    def _get_journal_initial_balance(self, options, journal_id, date_month=False):
        queries = []
        params = []
        report = self.env.ref('account_reports.journal_report')
        for column_group_key, options_group in report._split_options_per_column_group(options).items():
            new_options = self.env['account.general.ledger.report.handler']._get_options_initial_balance(options_group)  # Same options as the general ledger
            tables, where_clause, where_params = report._query_get(new_options, 'normal', domain=[('journal_id', '=', journal_id)])
            params.append(column_group_key)
            params += where_params
            queries.append(f"""
                SELECT
                    %s AS column_group_key,
                    sum("account_move_line".balance) as balance
                FROM {tables}
                JOIN account_journal journal ON journal.id = "account_move_line".journal_id AND "account_move_line".account_id = journal.default_account_id
                WHERE {where_clause}
                GROUP BY journal.id
            """)

        self._cr.execute(" UNION ALL ".join(queries), params)

        init_balance_by_col_group = {column_group_key: 0.0 for column_group_key in options['column_groups']}
        for result in self._cr.dictfetchall():
            init_balance_by_col_group[result['column_group_key']] = result['balance']

        return init_balance_by_col_group

    def _get_journal_balance_line(self, options, parent_line_id, eval_dict, is_starting_balance=True):
        """ Returns the line holding information about either the starting, or ending balance of a bank journal in the selected period.

        :param options: dictionary containing the options for the current report
        :param parent_key: the key of the parent line, either the journal or the month
        :param balance: the starting/ending balance of the journal
        :param is_starting_balance: whether the balance is the starting or ending balance. Used for formatting.
        """
        line_columns = []
        report = self.env['account.report'].browse(options['report_id'])

        for column in options['columns']:
            if column['expression_label'] == 'credit':  # Add a text in the credit column
                col_name = _('Starting Balance:') if is_starting_balance else _('Ending Balance:')
            elif column['expression_label'] == 'additional_col_1':
                col_name = eval_dict[column['column_group_key']]
            else:
                col_name = ''

            line_columns.append(report._build_column_dict(col_name, column, options=options))

        return {
            'id': report._get_generic_line_id(None, None, parent_line_id=parent_line_id, markup='initial' if is_starting_balance else 'final'),
            'name': '',
            'parent_id': parent_line_id,
            'columns': line_columns,
            'level': 3,
        }

    def _get_first_move_line(self, options, parent_key, line_key, values, is_unreconciled_payment):
        """ Returns the first line of a move.
        It is different from the other lines, as it contains more information such as the date, partner, and a link to the move itself.

        :param options: The report options.
        :param parent_key: The id of the lines that should be parenting the aml lines. Should be the group line (either the journal, or month).
        :param line_key: The id of the move line itself.
        :param values: The values of the move line.
        :param new_balance: The new balance of the move line, if any. Use to display the cumulated balance for bank journals.
        """
        report = self.env['account.report'].browse(options['report_id'])
        # Helps to format the line. If a line is linked to a partner but the account isn't receivable or payable, we want to display it in blue.
        columns = []
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            values = values[column_group_key]

            for column in options['columns']:
                if column.get('expression_label') not in ['additional_col_1', 'additional_col_2']:
                    if column.get('expression_label') == 'account':
                        col_value = '%s %s' % (values['account_code'], values['partner_name'] or values['account_name'])
                    elif column.get('expression_label') == 'label':
                        col_value = values['name']
                    elif column.get('expression_label') == 'invoice_date':
                        if values['journal_type'] in ('sale', 'purchase'):
                            col_value = values['invoice_date'] if values['debit'] or values['credit'] else ''
                        elif values['journal_code'] == 'POSS':
                            col_value = values['date']
                        else:
                            col_value = ''
                    else:
                        col_value = values[column.get('expression_label')]

                    columns.append(report._build_column_dict(col_value, column, options=options))
                else:
                    balance = False if column_group_options.get('show_payment_lines') and is_unreconciled_payment else values.get('cumulated_balance')
                    columns += self._get_move_line_additional_col(column_group_options, balance, values, is_unreconciled_payment)
                    break

        return {
            'id': line_key,
            'name': values['move_name'],
            'level': 3,
            'date': format_date(self.env, values['date']),
            'columns': columns,
            'parent_id': parent_key,
            'move_id': values['move_id'],
        }

    def _get_aml_line(self, options, parent_key, eval_dict, line_index, journal, is_unreconciled_payment):
        """ Returns the line of an account move line.

        :param options: The report options.
        :param parent_key: The id of the lines that should be parenting the aml lines. Should be the group line (either the journal, or month).
        :param values: The values of the move line.
        :param current_balance: The current balance of the move line, if any. Use to display the cumulated balance for bank journals.
        :param line_index: The index of the line in the move line list. Used to write additional information in the name, such as the move reference, or the ammount in currency.
        """
        report = self.env['account.report'].browse(options['report_id'])
        columns = []
        general_vals = next(col_group_val for col_group_val in eval_dict.values())
        if general_vals['journal_type'] == 'bank' and general_vals['account_type'] in ('liability_credit_card', 'asset_cash'):
            # Do not display bank account lines for bank journals
            return None

        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            values = eval_dict[column_group_key]

            for column in options['columns']:
                if column.get('expression_label') not in ['additional_col_1', 'additional_col_2']:
                    if column.get('expression_label') == 'account':
                        if values['journal_type'] == 'bank':  # For additional lines still showing in the bank journal, make sure to use the partner on the account if available.
                            col_value = '%s %s' % (values['account_code'], values['partner_name'] or values['account_name'])
                        elif values['journal_type'] == 'sale':
                            if values['debit']:
                                col_value = '%s %s' % (values['account_code'], values['partner_name'] or values['account_name'])
                            else:
                                col_value = '%s %s' % (values['account_code'], values['account_name'])
                        else:
                            col_value = '%s %s' % (values['account_code'], values['account_name'])
                    elif column.get('expression_label') == 'label':
                        col_value = values['name']
                    elif column.get('expression_label') == 'invoice_date':
                        col_value = ''
                    else:
                        col_value = values[column.get('expression_label')]

                    columns.append(report._build_column_dict(col_value, column, options=options))
                else:
                    balance = False if column_group_options.get('show_payment_lines') and is_unreconciled_payment else values.get('cumulated_balance')
                    columns += self._get_move_line_additional_col(column_group_options, balance, values, is_unreconciled_payment)
                    break

        return {
            'id': report._get_generic_line_id('account.move.line', values['move_line_id'], parent_line_id=parent_key),
            'name': self._get_aml_line_name(options, journal, line_index, eval_dict, is_unreconciled_payment),
            'level': 3,
            'parent_id': parent_key,
            'columns': columns,
        }

    def _get_aml_line_name(self, options, journal, line_index, values, is_unreconciled_payment):
        """ Returns the information to write as the name of the move lines, if needed.
        Typically, this is the move reference, or the amount in currency if we are in a multicurrency environment and the move is using a foreign currency.

        :param options: The report options.
        :param line_index: The index of the line in the move line list. We always want the reference second if existing and the amount in currency third if needed.
        :param values: The values of the move line.
        """
        # Returns the first occurrence. There is only one column group anyway.
        for column_group_key in options['column_groups']:
            if journal.type == 'bank' or not (self.user_has_groups('base.group_multi_currency') and values[column_group_key]['is_multicurrency']):
                amount_currency_name = ''
            else:
                amount_currency_name = _(
                    'Amount in currency: %s',
                    self.env['account.report']._format_value(
                        options,
                        values[column_group_key]['amount_currency_total'],
                        currency=self.env['res.currency'].browse(values[column_group_key]['move_currency']),
                        blank_if_zero=False,
                        figure_type='monetary'
                    )
                )
            if line_index == 0:
                res = values[column_group_key]['reference'] or amount_currency_name
                # if the invoice ref equals the payment ref then let's not repeat the information
                return res if res != values[column_group_key]['move_name'] else ''
            elif line_index == 1:
                return values[column_group_key]['reference'] and amount_currency_name or ''
            elif line_index == -1:  # Only when we create a line just for the amount currency. It's the only time we always want the amount.
                return amount_currency_name
            else:
                return ''

    def _get_move_line_additional_col(self, options, current_balance, values, is_unreconciled_payment):
        """ Returns the additional columns to be displayed on an account move line.
        These are the column coming after the debit and credit columns.
        For a sale or purchase journal, they will contain the taxes' information.
        For a bank journal, they will contain the cumulated amount.

        :param current_balance: The current balance of the move line, if any.
        :param values: The values of the move line.
        """
        report = self.env['account.report']
        additional_col = [
            report._build_column_dict('', {'figure_type': 'string', 'expression_label': 'additional_col_1'}, options=options),
            report._build_column_dict('', {'figure_type': 'string', 'expression_label': 'additional_col_2'}, options=options),
        ]
        if values['journal_type'] in ['sale', 'purchase']:
            tax_val = ''
            if values['taxes']:
                # Display the taxes affecting the line, formatted as such: "T: t1, t2"
                tax_val = _('T: %s', ', '.join(values['taxes']))
            elif values['tax_base_amount']:
                # Display the base amount on wich this tax line is based off, formatted as such: "B: $0.0"
                tax_val = _('B: %s', report._format_value(options, values['tax_base_amount'], blank_if_zero=False, figure_type='monetary'))
            additional_col = [
                report._build_column_dict(tax_val, {'figure_type': 'string', 'expression_label': 'additional_col_1'}, options=options),
                report._build_column_dict(', '.join(values['tax_grids']), {'figure_type': 'string', 'expression_label': 'additional_col_2'}, options=options),
            ]
        elif values['journal_type'] == 'bank':
            if values['account_type'] not in ('liability_credit_card', 'asset_cash') and current_balance:
                additional_col = [
                    report._build_column_dict(current_balance, {'figure_type': 'monetary', 'expression_label': 'additional_col_1'}, options=options),
                    report._build_column_dict('', {'figure_type': 'string', 'expression_label': 'additional_col_2'}, options=options),
                ]
            if self.user_has_groups('base.group_multi_currency') and values['move_line_currency'] != values['company_currency']:
                amount = -values['amount_currency'] if not is_unreconciled_payment else values['amount_currency']
                additional_col[-1] = report._build_column_dict(
                    amount,
                    {
                        'figure_type': 'monetary',
                        'expression_label': 'additional_col_2',
                    },
                    options=options,
                    currency=self.env['res.currency'].browse(values['move_line_currency']),
                )

        return additional_col

    ##########################################################################
    # Helper methods
    ##########################################################################

    def _get_generic_tax_report_options(self, options, data):
        """
        Return an option dictionnary set to fetch the reports with the parameters needed for this journal.
        The important bits are the journals, date, and fetch the generic tax reports that contains all taxes.
        We also provide the information about wether to take all entries or only posted ones.
        """
        generix_tax_report = self.env.ref('account.generic_tax_report')
        previous_option = options.copy()
        # Force the dates to the selected ones. Allows to get it correctly when grouped by months
        previous_option.update({
            'selected_variant_id': generix_tax_report.id,
            'date_from': data.get('date_from'),
            'date_to': data.get('date_to'),
        })
        tax_report_options = generix_tax_report.get_options(previous_option)
        # Even though it doesn't have a journal selector, we can force a journal in the options to only get the lines for a specific journal.
        if data.get('journal_id') or data.get('journal_type'):
            tax_report_options['journals'] = [{
                'id': data.get('journal_id'),
                'model': 'account.journal',
                'type': data.get('journal_type'),
                'selected': True,
            }]
        else:
            tax_report_options['journals'] = options.get('journals')
        return tax_report_options

    def _group_lines_by_move(self, options, eval_dict, parent_line_id):
        report = self.env['account.report'].browse(options['report_id'])
        grouped_dict = defaultdict(list)
        for move_line_vals in eval_dict.values():
            # We don't care about which column group is used for the id as it will be the same for all of them.
            move_id = next(col_group_val for col_group_val in move_line_vals.values())['move_id']
            move_key = report._get_generic_line_id('account.move', move_id, parent_line_id=parent_line_id)
            grouped_dict[move_key].append(move_line_vals)
        return grouped_dict

    ####################################################
    # Queries
    ####################################################

    def _query_aml(self, options, offset=0, journal=False):
        params = []
        queries = []
        lang = self.env.user.lang or get_lang(self.env).code
        acc_name = f"COALESCE(acc.name->>'{lang}', acc.name->>'en_US')" if \
            self.pool['account.account'].name.translate else 'acc.name'
        j_name = f"COALESCE(j.name->>'{lang}', j.name->>'en_US')" if \
            self.pool['account.journal'].name.translate else 'j.name'
        tax_name = f"COALESCE(tax.name->>'{lang}', tax.name->>'en_US')" if \
            self.pool['account.tax'].name.translate else 'tax.name'
        tag_name = f"COALESCE(tag.name->>'{lang}', tag.name->>'en_US')" if \
            self.pool['account.account.tag'].name.translate else 'tag.name'
        report = self.env.ref('account_reports.journal_report')
        for column_group_key, options_group in report._split_options_per_column_group(options).items():
            # Override any forced options: We want the ones given in the options
            options_group['date'] = options['date']
            tables, where_clause, where_params = report._query_get(options_group, 'strict_range', domain=[('journal_id', '=', journal.id)])
            sort_by_date = options_group.get('sort_by_date')
            params.append(column_group_key)
            params += where_params

            limit_to_load = report.load_more_limit + 1 if report.load_more_limit and options['export_mode'] != 'print' else None

            params += [limit_to_load, offset]
            queries.append(f"""
                SELECT
                    %s AS column_group_key,
                    "account_move_line".id as move_line_id,
                    "account_move_line".name,
                    "account_move_line".date,
                    "account_move_line".invoice_date,
                    "account_move_line".amount_currency,
                    "account_move_line".tax_base_amount,
                    "account_move_line".currency_id as move_line_currency,
                    "account_move_line".amount_currency,
                    am.id as move_id,
                    am.name as move_name,
                    am.journal_id,
                    am.currency_id as move_currency,
                    am.amount_total_in_currency_signed as amount_currency_total,
                    am.currency_id != cp.currency_id as is_multicurrency,
                    p.name as partner_name,
                    acc.code as account_code,
                    {acc_name} as account_name,
                    acc.account_type as account_type,
                    COALESCE("account_move_line".debit, 0) as debit,
                    COALESCE("account_move_line".credit, 0) as credit,
                    COALESCE("account_move_line".balance, 0) as balance,
                    {j_name} as journal_name,
                    j.code as journal_code,
                    j.type as journal_type,
                    j.currency_id as journal_currency,
                    journal_curr.name as journal_currency_name,
                    cp.currency_id as company_currency,
                    CASE WHEN j.type = 'sale' THEN am.payment_reference WHEN j.type = 'purchase' THEN am.ref ELSE '' END as reference,
                    array_remove(array_agg(DISTINCT {tax_name}), NULL) as taxes,
                    array_remove(array_agg(DISTINCT {tag_name}), NULL) as tax_grids
                FROM {tables}
                JOIN account_move am ON am.id = "account_move_line".move_id
                JOIN account_account acc ON acc.id = "account_move_line".account_id
                LEFT JOIN res_partner p ON p.id = "account_move_line".partner_id
                JOIN account_journal j ON j.id = am.journal_id
                JOIN res_company cp ON cp.id = am.company_id
                LEFT JOIN account_move_line_account_tax_rel aml_at_rel ON aml_at_rel.account_move_line_id = "account_move_line".id
                LEFT JOIN account_tax parent_tax ON parent_tax.id = aml_at_rel.account_tax_id and parent_tax.amount_type = 'group'
                LEFT JOIN account_tax_filiation_rel tax_filiation_rel ON tax_filiation_rel.parent_tax = parent_tax.id
                LEFT JOIN account_tax tax ON (tax.id = aml_at_rel.account_tax_id and tax.amount_type != 'group') or tax.id = tax_filiation_rel.child_tax
                LEFT JOIN account_account_tag_account_move_line_rel tag_rel ON tag_rel.account_move_line_id = "account_move_line".id
                LEFT JOIN account_account_tag tag on tag_rel.account_account_tag_id = tag.id
                LEFT JOIN res_currency journal_curr on journal_curr.id = j.currency_id
                WHERE {where_clause}
                GROUP BY "account_move_line".id, am.id, p.id, acc.id, j.id, cp.id, journal_curr.id
                ORDER BY j.id, CASE when am.name = '/' then 1 else 0 end,
                {" am.date, am.name," if sort_by_date else " am.name , am.date,"}
                CASE acc.account_type
                    WHEN 'liability_payable' THEN 1
                    WHEN 'asset_receivable' THEN 1
                    WHEN 'liability_credit_card' THEN 5
                    WHEN 'asset_cash' THEN 5
                    ELSE 2
               END,
               "account_move_line".tax_line_id NULLS FIRST
               LIMIT %s
               OFFSET %s
            """)

        # 1.2.Fetch data from DB
        rslt = {}
        self._cr.execute('(' + ') UNION ALL ('.join(queries) + ')', params)
        for aml_result in self._cr.dictfetchall():
            rslt.setdefault(aml_result['move_line_id'], {col_group_key: {} for col_group_key in options['column_groups']})
            rslt[aml_result['move_line_id']][aml_result['column_group_key']] = aml_result

        return rslt

    def _query_months(self, options, line_id=False, offset=0, journal=False):
        params = []
        queries = []
        report = self.env.ref('account_reports.journal_report')
        for column_group_key, options_group in report._split_options_per_column_group(options).items():
            tables, where_clause, where_params = report._query_get(options_group, 'strict_range', domain=[('journal_id', '=', journal.id)])
            params.append(column_group_key)
            params += where_params
            # Fetch all months for which we have any move lines, ordered chronologically.
            queries.append(f"""
                (WITH aml_by_months AS (
                    SELECT DISTINCT ON (to_char("account_move_line".date, 'MM YYYY')) to_char("account_move_line".date, 'MM YYYY') AS month, to_char("account_move_line".date, 'fmMon YYYY') AS display_month, %s as column_group_key, "account_move_line".date
                    FROM {tables}
                    WHERE {where_clause}
                )
                SELECT column_group_key, month, display_month
                FROM aml_by_months
                ORDER BY date)
            """)

        # 1.2.Fetch data from DB
        self._cr.execute(" UNION ALL ".join(queries), params)
        rslt = {}
        for aml_result in self._cr.dictfetchall():
            rslt.setdefault(aml_result['month'], {col_group_key: {} for col_group_key in options['column_groups']})
            rslt[aml_result['month']][aml_result['column_group_key']] = aml_result

        return rslt

    def _get_tax_grids_summary(self, options, data):
        """
        Fetches the details of all grids that have been used in the provided journal.
        The result is grouped by the country in which the tag exists in case of multivat environment.
        Returns a dictionary with the following structure:
        {
            Country : {
                tag_name: {+, -, impact},
                tag_name: {+, -, impact},
                tag_name: {+, -, impact},
                ...
            },
            Country : [
                tag_name: {+, -, impact},
                tag_name: {+, -, impact},
                tag_name: {+, -, impact},
                ...
            ],
            ...
        }
        """
        report = self.env.ref('account_reports.journal_report')
        # Use the same option as we use to get the tax details, but this time to generate the query used to fetch the
        # grid information
        tax_report_options = self._get_generic_tax_report_options(options, data)
        tables, where_clause, where_params = report._query_get(tax_report_options, 'strict_range')
        lang = self.env.user.lang or get_lang(self.env).code
        country_name = f"COALESCE(country.name->>'{lang}', country.name->>'en_US')"
        tag_name = f"COALESCE(tag.name->>'{lang}', tag.name->>'en_US')" if \
            self.pool['account.account.tag'].name.translate else 'tag.name'
        query = f"""
            WITH tag_info (country_name, tag_id, tag_name, tag_sign, balance) as (
                SELECT
                    {country_name} AS country_name,
                    tag.id,
                    {tag_name} AS name,
                    CASE WHEN tag.tax_negate IS TRUE THEN '-' ELSE '+' END,
                    SUM(COALESCE("account_move_line".balance, 0)
                        * CASE WHEN "account_move_line".tax_tag_invert THEN -1 ELSE 1 END
                        ) AS balance
                FROM account_account_tag tag
                JOIN account_account_tag_account_move_line_rel rel ON tag.id = rel.account_account_tag_id
                JOIN res_country country on country.id = tag.country_id
                , {tables}
                WHERE {where_clause}
                  AND applicability = 'taxes'
                  AND "account_move_line".id = rel.account_move_line_id
                GROUP BY country_name, tag.id
            )
            SELECT
                country_name,
                tag_id,
                REGEXP_REPLACE(tag_name, '^[+-]', '') AS name, -- Remove the sign from the grid name
                balance,
                tag_sign AS sign
            FROM tag_info
            ORDER BY country_name, name
        """
        self._cr.execute(query, where_params)
        query_res = self.env.cr.fetchall()

        res = defaultdict(lambda: defaultdict(dict))
        opposite = {'+': '-', '-': '+'}
        for country_name, tag_id, name, balance, sign in query_res:
            res[country_name][name].setdefault('tag_id', []).append(tag_id)
            res[country_name][name][sign] = report._format_value(options, balance, blank_if_zero=False, figure_type='monetary')
            # We need them formatted, to ensure they are displayed correctly in the report. (E.g. 0.0, not 0)
            if not opposite[sign] in res[country_name][name]:
                res[country_name][name][opposite[sign]] = report._format_value(options, 0, blank_if_zero=False, figure_type='monetary')
            res[country_name][name][sign + '_no_format'] = balance
            res[country_name][name]['impact'] = report._format_value(options, res[country_name][name].get('+_no_format', 0) - res[country_name][name].get('-_no_format', 0), blank_if_zero=False, figure_type='monetary')

        return res

    def _get_generic_tax_summary_for_sections(self, options, data):
        """
        Overridden to make use of the generic tax report computation
        Works by forcing specific options into the tax report to only get the lines we need.
        The result is grouped by the country in which the tag exists in case of multivat environment.
        Returns a dictionary with the following structure:
        {
            Country : [
                {name, base_amount, tax_amount, tax_non_deductible{_no_format}, tax_deductible{_no_format}, tax_due{_no_format}},
                {name, base_amount, tax_amount, tax_non_deductible{_no_format}, tax_deductible{_no_format}, tax_due{_no_format}},
                {name, base_amount, tax_amount, tax_non_deductible{_no_format}, tax_deductible{_no_format}, tax_due{_no_format}},
                ...
            ],
            Country : [
                {name, base_amount, tax_amount, tax_non_deductible{_no_format}, tax_deductible{_no_format}, tax_due{_no_format}},
                {name, base_amount, tax_amount, tax_non_deductible{_no_format}, tax_deductible{_no_format}, tax_due{_no_format}},
                {name, base_amount, tax_amount, tax_non_deductible{_no_format}, tax_deductible{_no_format}, tax_due{_no_format}},
                ...
            ],
            ...
        }
        """
        report = self.env['account.report'].browse(options['report_id'])
        tax_report_options = self._get_generic_tax_report_options(options, data)
        tax_report_options['account_journal_report_tax_deductibility_columns'] = True
        tax_report = self.env.ref('account.generic_tax_report')
        tax_report_lines = tax_report._get_lines(tax_report_options)

        tax_values = {}
        for tax_report_line in tax_report_lines:
            model, line_id = report._parse_line_id(tax_report_line.get('id'))[-1][1:]
            if model == 'account.tax':
                tax_values[line_id] = {
                    'base_amount': tax_report_line['columns'][0]['no_format'],
                    'tax_amount': tax_report_line['columns'][1]['no_format'],
                    'tax_non_deductible': tax_report_line['columns'][2]['no_format'],
                    'tax_deductible': tax_report_line['columns'][3]['no_format'],
                    'tax_due': tax_report_line['columns'][4]['no_format'],
                }

        # Make the final data dict that will be used by the template, using the taxes information.
        taxes = self.env['account.tax'].browse(tax_values.keys())
        res = defaultdict(list)
        for tax in taxes:
            res[tax.country_id.name].append({
                'base_amount': report._format_value(options, tax_values[tax.id]['base_amount'], blank_if_zero=False, figure_type='monetary'),
                'tax_amount': report._format_value(options, tax_values[tax.id]['tax_amount'], blank_if_zero=False, figure_type='monetary'),
                'tax_non_deductible': report._format_value(options, tax_values[tax.id]['tax_non_deductible'], blank_if_zero=False, figure_type='monetary'),
                'tax_non_deductible_no_format': tax_values[tax.id]['tax_non_deductible'],
                'tax_deductible': report._format_value(options, tax_values[tax.id]['tax_deductible'], blank_if_zero=False, figure_type='monetary'),
                'tax_deductible_no_format': tax_values[tax.id]['tax_deductible'],
                'tax_due': report._format_value(options, tax_values[tax.id]['tax_due'], blank_if_zero=False, figure_type='monetary'),
                'tax_due_no_format': tax_values[tax.id]['tax_due'],
                'name': tax.name,
                'line_id': report._get_generic_line_id('account.tax', tax.id)
            })

        # Return the result, ordered by country name
        return dict(sorted(res.items()))

    ####################################################
    # Actions
    ####################################################

    def journal_report_tax_tag_template_open_aml(self, options, params=None):
        """ returns an action to open a tree view of the account.move.line having the selected tax tag """
        tag_id = params.get('tag_id')
        # When grouped by month, we don't use the report dates directly, but the ones of the month. So they need to replace the ones in the options.
        new_options = options.copy()
        new_options['date'].update({
            'date_from': params and params.get('date_from') or options.get('date', {}).get('date_from'),
            'date_to': params and params.get('date_to') or options.get('date', {}).get('date_to'),
        })
        domain = self.env['account.report'].browse(options['report_id'])._get_options_domain(new_options, 'strict_range') + [('tax_tag_ids', 'in', tag_id)] + self.env['account.move.line']._get_tax_exigible_domain()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Items for Tax Audit'),
            'res_model': 'account.move.line',
            'views': [[self.env.ref('account.view_move_line_tax_audit_tree').id, 'list']],
            'domain': domain,
            'context': self.env.context,
        }

    def journal_report_action_dropdown_audit_default_tax_report(self, options, params):
        # See above
        new_options = options.copy()
        new_options['date'].update({
            'date_from': params and params.get('date_from') or options.get('date', {}).get('date_from'),
            'date_to': params and params.get('date_to') or options.get('date', {}).get('date_to'),
        })
        return self.env['account.generic.tax.report.handler'].caret_option_audit_tax(new_options, params)

    def journal_report_action_open_tax_journal_items(self, options, params):
        """
        Open the journal items related to the tax on this line.
        Take into account the given/options date and group by taxes then account.
        :param options: the report options.
        :param params: a dict containing the line params. (Dates, name, journal_id, tax_type)
        :return: act_window on journal items grouped by tax or tags and accounts.
        """
        ctx = {
            'search_default_posted': 0 if options.get('all_entries') else 1,
            'search_default_date_between': 1,
            'date_from': params and params.get('date_from') or options.get('date', {}).get('date_from'),
            'date_to': params and params.get('date_to') or options.get('date', {}).get('date_to'),
            'search_default_journal_id': params.get('journal_id'),
            'expand': 1,
        }
        if params and params.get('tax_type') == 'tag':
            ctx.update({
                'search_default_group_by_tax_tags': 1,
                'search_default_group_by_account': 2,
            })
        elif params and params.get('tax_type') == 'tax':
            ctx.update({
                'search_default_group_by_taxes': 1,
                'search_default_group_by_account': 2,
            })

        if params and 'journal_id' in params:
            ctx.update({
                'search_default_journal_id': [params['journal_id']],
            })

        if options and options.get('journals') and 'search_default_journal_id' not in ctx:
            selected_journals = [journal['id'] for journal in options['journals'] if journal.get('selected')]
            if len(selected_journals) == 1:
                ctx['search_default_journal_id'] = selected_journals

        return {
            'name': params.get('name'),
            'view_mode': 'tree,pivot,graph,kanban',
            'res_model': 'account.move.line',
            'views': [(self.env.ref('account.view_move_line_tree').id, 'list')],
            'type': 'ir.actions.act_window',
            'domain': [('display_type', 'not in', ('line_section', 'line_note'))],
            'context': ctx,
        }

    def open_journal_items(self, options, params):
        report = self.env['account.report'].browse(options['report_id'])
        action = report.open_journal_items(options=options, params=params)
        action.get('context', {}).update({'search_default_group_by_account': 0, 'search_default_group_by_move': 1})
        return action

    def journal_report_action_open_business_doc(self, options, params):
        model, record_id = self.env['account.report']._get_model_info_from_id(params['line_id'])
        record = self.env[model].browse(record_id)
        if record._name in ['account.move', 'account.move.line']:
            return record.action_open_business_doc()
        raise UserError(_("The selected report line does not target a Journal Entry or a Journal Item."))
