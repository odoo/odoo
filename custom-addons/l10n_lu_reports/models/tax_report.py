# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools, _
from odoo.exceptions import UserError


class LuxembourgishTaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_lu.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Luxembourgish Tax Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options.setdefault('buttons', []).append(
            {'name': _('XML'), 'sequence': 30, 'action': 'open_report_export_wizard', 'file_export_type': _('XML')}
        )

    def _get_field_values(self, lines):
        values = {}
        for line in lines:
            # tax report's `code` would contain alpha-numeric string like `LUTAX_XXX` where characters
            # at last three positions will be digits, hence we split `code` with `_` and build dictionary
            # having `code` as dictionary key
            split_line_code = line.get('code', '') and line['code'].split('_')[-1]
            if split_line_code and split_line_code.isdigit():
                balance = "{:.2f}".format(line['columns'][0]['no_format']).replace('.', ',')
                values[split_line_code] = {'value': balance, 'field_type': 'number'}

        return values

    def get_tax_electronic_report_values(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        lu_template_values = self.env['l10n_lu.report.handler'].get_electronic_report_values(options)
        lines = report._get_lines({'unfold_all': True, **options})
        date_from = fields.Date.from_string(options['date'].get('date_from'))
        date_to = fields.Date.from_string(options['date'].get('date_to'))

        # When user selects custom dates, if its start and end date fall in the same month,
        # the report declaration will be considered monthly. If both dates fall in the same quarter,
        # it will be considered quarterly report. If both datas fall in different quarters,
        # it will be considered a yearly report.
        date_from_quarter = tools.date_utils.get_quarter_number(date_from)
        date_to_quarter = tools.date_utils.get_quarter_number(date_to)
        if date_from.month == date_to.month:
            period = date_from.month
            declaration_type = 'TVA_DECM'
        elif date_from_quarter == date_to_quarter:
            period = date_from_quarter
            declaration_type = 'TVA_DECT'
        elif date_from_quarter == 1 and date_to_quarter == 4:
            period = 1
            declaration_type = 'TVA_DECA'
        else:
            raise UserError(_('The selected period is not supported for the selected declaration type.'))

        values = self._get_field_values(lines)

        lu_template_values.update({
            'forms': [{
                'declaration_type': declaration_type,
                'year': date_from.year,
                'period': period,
                'currency': self.env.company.currency_id.name,
                'field_values': values,
            }]
        })
        return lu_template_values

    def open_report_export_wizard(self, options):
        """ Creates a new export wizard for this report."""
        new_context = self.env.context.copy()
        new_context['report_generation_options'] = options
        return self.env['l10n_lu.generate.tax.report'].with_context(new_context).create({}).get_xml()
