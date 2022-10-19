# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class MoroccanTaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_ma.tax.report.handler'
    _inherit = 'account.generic.tax.report.handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        lines_121_129 = (
            'l10n_ma_vat_121.tax',
            'l10n_ma_vat_122.tax',
            'l10n_ma_vat_123.tax',
            'l10n_ma_vat_124.tax',
            'l10n_ma_vat_129.tax',
        )
        column_group_values = {}

        for column_group, expression_totals in all_column_groups_expression_totals.items():
            expression_values = { f'{expression.report_line_id.code}.{expression.label}': totals.get('value') for expression, totals in expression_totals.items() }
            lines_121_129_sum = sum(map(lambda x: expression_values.get(x, 0), lines_121_129))

            line_130 = expression_values.get('l10n_ma_vat_b.tax_sum', 0)
            line_180 = expression_values.get('l10n_ma_vat_180.tax', 0)
            line_182 = expression_values.get('l10n_ma_vat_182.tax', 0)
            line_190 = expression_values.get('l10n_ma_vat_190.tax', 0)
            line_204 = 0

            if line_130 - line_190 > 0:
                line_130 += lines_121_129_sum
            else:
                line_204 += lines_121_129_sum

            line_200 = line_130 - line_190 if line_130 > line_190 else 0
            line_201 = line_190 - line_130 if line_190 > line_130 else 0
            line_202 = (line_182 + line_180 - line_130) * 0.15 if line_182 + line_180 > line_130 else 0
            line_203 = line_201 - line_202 if line_201 > line_202 else 0

            column_group_values[column_group] = {
                130: line_130,
                200: line_200,
                201: line_201,
                202: line_202,
                203: line_203,
                204: line_204,
            }

        column_values = {
            130: [],
            200: [],
            201: [],
            202: [],
            203: [],
            204: [],
        }

        for line in column_values.keys():
            for column in options['columns']:
                if column['expression_label'] != 'tax':
                    column_values[line].append({})
                    continue

                col_val = column_group_values.get(column['column_group_key'], {}).get(line)

                if not col_val:
                    column_values[line].append({})
                else:
                    column_values[line].append({
                        'name': self.env['account.report'].format_value(col_val, figure_type=column['figure_type']),
                        'no_format': col_val,
                        'class': 'number',
                    })

        dynamic_lines = [
            (68, {
                'id': report._get_generic_line_id(None, None, markup='tax_report_line_130'),
                'name': _('130 - Total VAT Payable'),
                'columns': column_values[130],
                'level': 0,
            }),
            (110, {
                'id': report._get_generic_line_id(None, None, markup='tax_report_line_200'),
                'name': _('200 - Payable VAT (130 - 190)'),
                'columns': column_values[200],
                'level': 3,
            }),
            (111, {
                'id': report._get_generic_line_id(None, None, markup='tax_report_line_201'),
                'name': _('201 - Credit (190 - 130)'),
                'columns': column_values[201],
                'level': 3,
            }),
            (112, {
                'id': report._get_generic_line_id(None, None, markup='tax_report_line_202'),
                'name': _('202 - 15% reduction of the credit for the period ((182 + 180) - 130) x 15%'),
                'columns': column_values[202],
                'level': 3,
            }),
            (113, {
                'id': report._get_generic_line_id(None, None, markup='tax_report_line_203'),
                'name': _('203 - Credit to be carried forward (201 - 202)'),
                'columns': column_values[203],
                'level': 3,
            }),
            (114, {
                'id': report._get_generic_line_id(None, None, markup='tax_report_line_204'),
                'name': _('204 - Credit with payment including VAT due under articles 115, 116 and 117 of the CGI'),
                'columns': column_values[204],
                'level': 3,
            }),
        ]

        return dynamic_lines
