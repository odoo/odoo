# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _, fields
from odoo.tools import float_compare
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT


class TrialBalanceCustomHandler(models.AbstractModel):
    _name = 'account.trial.balance.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Trial Balance Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        def _update_column(line, column_key, new_value, blank_if_zero=False):
            line['columns'][column_key]['name'] = self.env['account.report']._format_value(options, new_value, figure_type='monetary', blank_if_zero=blank_if_zero)
            line['columns'][column_key]['no_format'] = new_value

        def _update_balance_columns(line, debit_column_key, credit_column_key, total_diff_values_key):
            debit_value = line['columns'][debit_column_key]['no_format'] if debit_column_key is not None else False
            credit_value = line['columns'][credit_column_key]['no_format'] if credit_column_key is not None else False

            if debit_value and credit_value:
                new_debit_value = 0.0
                new_credit_value = 0.0

                if float_compare(debit_value, credit_value, precision_digits=self.env.company.currency_id.decimal_places) == 1:
                    new_debit_value = debit_value - credit_value
                    total_diff_values[total_diff_values_key] += credit_value
                else:
                    new_credit_value = (debit_value - credit_value) * -1
                    total_diff_values[total_diff_values_key] += debit_value

                _update_column(line, debit_column_key, new_debit_value)
                _update_column(line, credit_column_key, new_credit_value)

        lines = [line[1] for line in self.env['account.general.ledger.report.handler']._dynamic_lines_generator(report, options, all_column_groups_expression_totals, warnings=warnings)]

        total_diff_values = {
            'initial_balance': 0.0,
            'end_balance': 0.0,
        }

        # We need to find the index of debit and credit columns for initial and end balance in case of extra custom columns
        init_balance_debit_index = next((index for index, column in enumerate(options['columns']) if column.get('expression_label') == 'debit'), None)
        init_balance_credit_index = next((index for index, column in enumerate(options['columns']) if column.get('expression_label') == 'credit'), None)

        end_balance_debit_index = -(next((index for index, column in enumerate(reversed(options['columns'])) if column.get('expression_label') == 'debit'), -1) + 1)\
                                  or None
        end_balance_credit_index = -(next((index for index, column in enumerate(reversed(options['columns'])) if column.get('expression_label') == 'credit'), -1) + 1)\
                                   or None

        for line in lines[:-1]:
            # Initial balance
            res_model = report._get_model_info_from_id(line['id'])[0]
            if res_model == 'account.account':
                # Initial balance
                _update_balance_columns(line, init_balance_debit_index, init_balance_credit_index, 'initial_balance')

                # End balance
                _update_balance_columns(line, end_balance_debit_index, end_balance_credit_index, 'end_balance')

            line.pop('expand_function', None)
            line.pop('groupby', None)
            line.update({
                'unfoldable': False,
                'unfolded': False,
            })

            res_model = report._get_model_info_from_id(line['id'])[0]
            if res_model == 'account.account':
                line['caret_options'] = 'trial_balance'

        # Total line
        if lines:
            total_line = lines[-1]

            for index, balance_key in zip(
                    (init_balance_debit_index, init_balance_credit_index, end_balance_debit_index, end_balance_credit_index),
                    ('initial_balance', 'initial_balance', 'end_balance', 'end_balance')
            ):
                if index is not None:
                    _update_column(total_line, index, total_line['columns'][index]['no_format'] - total_diff_values[balance_key], blank_if_zero=False)

        return [(0, line) for line in lines]

    def _caret_options_initializer(self):
        return {
            'trial_balance': [
                {'name': _("General Ledger"), 'action': 'caret_option_open_general_ledger'},
                {'name': _("Journal Items"), 'action': 'open_journal_items'},
            ],
        }

    def _custom_options_initializer(self, report, options, previous_options=None):
        """ Modifies the provided options to add a column group for initial balance and end balance, as well as the appropriate columns.
        """
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        default_group_vals = {'horizontal_groupby_element': {}, 'forced_options': {}}

        # Columns between initial and end balance must not include initial balance; we use a special option key for that in general ledger
        for column_group in options['column_groups'].values():
            column_group['forced_options']['general_ledger_strict_range'] = True

        if options['comparison']['periods']:
            # Reverse the order the group of columns with the same column_group_key while keeping the original order inside the group
            new_columns_order = []
            current_column = []
            current_column_group_key = options['columns'][-1]['column_group_key']

            for column in reversed(options['columns']):
                if current_column_group_key != column['column_group_key']:
                    current_column_group_key = column['column_group_key']
                    new_columns_order += current_column
                    current_column = []

                current_column.insert(0, column)
            new_columns_order += current_column

            options['columns'] = new_columns_order
            options['column_headers'][0][:] = reversed(options['column_headers'][0])

        # Initial balance
        initial_balance_options = self.env['account.general.ledger.report.handler']._get_options_initial_balance(options)
        initial_forced_options = {
            'date': initial_balance_options['date'],
            'include_current_year_in_unaff_earnings': initial_balance_options['include_current_year_in_unaff_earnings']
        }
        initial_header_element = [{'name': _("Initial Balance"), 'forced_options': initial_forced_options}]
        col_headers_initial = [
            initial_header_element,
            *options['column_headers'][1:],
        ]
        initial_column_group_vals = report._generate_columns_group_vals_recursively(col_headers_initial, default_group_vals)
        initial_columns, initial_column_groups = report._build_columns_from_column_group_vals(initial_forced_options, initial_column_group_vals)

        # End balance
        end_date_to = options['date']['date_to']
        end_date_from = options['comparison']['periods'][-1]['date_from'] if options['comparison']['periods'] else options['date']['date_from']
        end_forced_options = {
            'date': {
                'mode': 'range',
                'date_to': fields.Date.from_string(end_date_to).strftime(DEFAULT_SERVER_DATE_FORMAT),
                'date_from': fields.Date.from_string(end_date_from).strftime(DEFAULT_SERVER_DATE_FORMAT)
            }
        }
        end_header_element = [{'name': _("End Balance"), 'forced_options': end_forced_options}]
        col_headers_end = [
            end_header_element,
            *options['column_headers'][1:],
        ]
        end_column_group_vals = report._generate_columns_group_vals_recursively(col_headers_end, default_group_vals)
        end_columns, end_column_groups = report._build_columns_from_column_group_vals(end_forced_options, end_column_group_vals)

        # Update options
        options['column_headers'][0] = initial_header_element + options['column_headers'][0] + end_header_element
        options['column_groups'].update(initial_column_groups)
        options['column_groups'].update(end_column_groups)
        options['columns'] = initial_columns + options['columns'] + end_columns
        options['ignore_totals_below_sections'] = True # So that GL does not compute them

        report._init_options_order_column(options, previous_options)

    def _custom_line_postprocessor(self, report, options, lines, warnings=None):
        # If the hierarchy is enabled, ensure to add the o_account_coa_column_contrast class to the hierarchy lines
        if options.get('hierarchy'):
            for line in lines:
                model, dummy = report._get_model_info_from_id(line['id'])
                if model == 'account.group':
                    line_classes = line.get('class', '')
                    line['class'] = line_classes + ' o_account_coa_column_contrast_hierarchy'

        return lines
