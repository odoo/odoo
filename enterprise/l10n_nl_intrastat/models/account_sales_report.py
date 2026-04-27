# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, models, _


class DutchECSalesReportCustomHandler(models.AbstractModel):
    _name = 'l10n_nl.ec.sales.report.handler'
    _inherit = 'account.ec.sales.report.handler'
    _description = 'Dutch EC Sales Report Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        lines = []

        totals_by_column_group = {
            key: {
                column['expression_label']: 0.0 if column['figure_type'] == 'monetary' else ''
                for column in options['columns']
            } for key in options['column_groups']
        }

        for partner, results in self._query_partners(report, options):
            partner_values = defaultdict(dict)

            for column_group_key in options['column_groups']:
                partner_sum = results.get(column_group_key, {})
                country_code = partner_sum.get('country_code', 'UNKNOWN')

                # For Greece, the ISO 3166 code (GR) and European Union code (EL) is not the same.
                # Since this is a european report, we need the European Union code.
                if country_code == 'GR':
                    country_code = 'EL'

                line_total = partner_sum.get('goods', 0.0) + partner_sum.get('services', 0.0) + partner_sum.get('triangular', 0.0)

                partner_values[column_group_key].update({
                    'country_code': country_code,
                    'partner_name': '',
                    'vat': self._format_vat(partner_sum.get('full_vat_number'), country_code),
                    'amount_product': partner_sum.get('goods', 0.0),
                    'amount_service': partner_sum.get('services', 0.0),
                    'amount_triangular': partner_sum.get('triangular', 0.0),
                    'total': line_total,
                })

                totals_by_column_group[column_group_key]['amount_product'] += partner_sum.get('goods', 0.0)
                totals_by_column_group[column_group_key]['amount_service'] += partner_sum.get('services', 0.0)
                totals_by_column_group[column_group_key]['amount_triangular'] += partner_sum.get('triangular', 0.0)
                totals_by_column_group[column_group_key]['total'] += line_total

            lines.append((0, self._get_report_line_partner(report, options, partner, partner_values)))

        lines.append((0, self._get_report_line_total(report, options, totals_by_column_group)))
        return lines

    def _caret_options_initializer(self):
        """
        Add custom caret option for the report to link to the partner and allow cleaner overrides.
        """
        return {
            'nl_icp_partner': [
                {'name': _("View Partner"), 'action': 'caret_option_open_record_form'},
            ],
        }

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)
        goods_tag = self.env.ref('l10n_nl.tax_report_rub_3bg_tag', raise_if_not_found=False)
        services_tag = self.env.ref('l10n_nl.tax_report_rub_3bs_tag', raise_if_not_found=False)
        triangular_tag = self.env.ref('l10n_nl.tax_report_rub_3bt_tag', raise_if_not_found=False)
        if goods_tag and services_tag and triangular_tag:
            options.get('sales_report_taxes', {}).update({
                'goods': goods_tag._get_matching_tags().ids,
                'services': services_tag._get_matching_tags().ids,
                'triangular': triangular_tag._get_matching_tags().ids,
                'use_taxes_instead_of_tags': False,
            })
        else:
            goods_tax = self.env['account.chart.template'].ref('btw_X0_producten', raise_if_not_found=False)
            services_tax = self.env['account.chart.template'].ref('btw_X0_diensten', raise_if_not_found=False)
            triangular_tax = self.env['account.chart.template'].ref('btw_X0_ABC_levering', raise_if_not_found=False)
            options.get('sales_report_taxes', {}).update({
                'goods': [goods_tax.id] if goods_tax else [],
                'services': [services_tax.id] if services_tax else [],
                'triangular': [triangular_tax.id] if triangular_tax else [],
                'use_taxes_instead_of_tags': True,
            })

    @api.model
    def _format_vat(self, vat, country_code):
        """ VAT numbers must be reported without country code, and grouped by 4
        characters, with a space between each pair of groups.
        """
        if vat:
            if vat[:2].lower() == country_code.lower():
                vat = vat[2:]
            return vat
        return None
