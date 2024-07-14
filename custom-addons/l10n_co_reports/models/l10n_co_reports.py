# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import models


class ColumbianReportCustomHandler(models.AbstractModel):
    _name = 'l10n_co.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Columbian Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        for button in options['buttons']:
            if button['name'] == 'PDF':
                button['action'] = 'print_pdf'

    def _get_column_values(self, report, options, grouped_values):
        """ Retrieve the correct value for each column and format it accordingly.
        This method is used by several reports, and some columns only apply to
        one or more report(s), i.e 'percentage' and 'bimestre'.

        :param options (dict):      The report options.
        :param values (dict):       All the values for the current line.
        :return (list of dicts):    A list of dicts, with each dict representing a column.
        """
        column_values = []

        for column in options['columns']:
            col_expr = column['expression_label']
            current_value = grouped_values.get(column['column_group_key'], {})

            if not current_value:
                column_values.append(report._build_column_dict(None, None))
            else:
                col_val = current_value.get(col_expr)

                if col_expr == 'percentage':
                    col_val = 15 if current_value['balance'] else 0
                else:
                    if col_val is None:
                        column_values.append(report._build_column_dict(None, None))
                        continue
                    else:
                        if col_expr == 'bimestre':
                            col_val = self._get_bimonth_name(current_value['bimestre'])

                column_values.append(report._build_column_dict(col_val, column, options=options))

        return column_values

    def _get_partner_values(self, report, options, query_results, expand_function):
        grouped_results = {}
        for results in query_results:
            grouped_results.setdefault(results['partner_id'], {})[results['column_group_key']] = results

        lines = []
        for partner_id, partner_values in grouped_results.items():
            line_id = report._get_generic_line_id('res.partner', partner_id)
            lines.append((0, {
                'id': line_id,
                'name': list(partner_values.values())[0]['partner_name'],
                'level': 2,
                'unfoldable': True,
                'unfolded': line_id in options.get('unfolded_lines'),
                'expand_function': expand_function,
                'columns': self._get_column_values(report, options, partner_values)
            }))
        return lines

    def _get_grouped_values(self, report, options, query_results, group_by=None):
        grouped_results = {}
        for results in query_results:
            grouped_results.setdefault(results[group_by], {})[results['column_group_key']] = results

        lines = []
        for group, group_values in grouped_results.items():
            parent_line_id = report._get_generic_line_id('res.partner', list(group_values.values())[0]['partner_id'])
            markup = '%s_%s' % (group_by, group)
            lines.append({
                'id': report._get_generic_line_id(None, None, markup=markup, parent_line_id=parent_line_id),
                'name': '',
                'unfoldable': False,
                'columns': self._get_column_values(report, options, group_values),
                'level': 3,
                'parent_id': parent_line_id,
            })
        return {'lines': lines}

    def _get_bimonth_name(self, bimonth_index):
        bimonth_names = {
            1: 'Enero - Febrero',
            2: 'Marzo - Abril',
            3: 'Mayo - Junio',
            4: 'Julio - Agosto',
            5: 'Septiembre - Octubre',
            6: 'Noviembre - Diciembre',
        }
        return bimonth_names[bimonth_index]

    def _get_domain(self, report, options, line_dict_id=None):
        common_domain = [('partner_id', '!=', False)]
        if line_dict_id:
            partner_model, partner_id = report._get_model_info_from_id(line_dict_id)
            if partner_model == 'res.partner' and partner_id:
                common_domain += [('partner_id', '=', partner_id)]
        return common_domain

    def print_pdf(self, options, action_param):
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'l10n_co_reports.retention_report.wizard',
            'views': [(self.env.ref('l10n_co_reports.retention_report_wizard_form').id, 'form')],
            'view_id': self.env.ref('l10n_co_reports.retention_report_wizard_form').id,
            'target': 'new',
            'context': {'options': options},
            'data': {'options': json.dumps(options), 'output_format': 'pdf'},
        }
