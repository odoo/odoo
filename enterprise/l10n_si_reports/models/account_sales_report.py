# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import models, _


class SlovenianECSalesReportCustomHandler(models.AbstractModel):
    _name = 'l10n_si.ec.sales.report.handler'
    _inherit = 'account.ec.sales.report.handler'
    _description = 'Slovenian Sales Report Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        """ Generate the dynamic lines for the report in a horizontal style (one line partner, one column per operation type).
        """
        lines = []

        for partner, results in super()._query_partners(report, options):
            partner_values = defaultdict(dict)
            for column_group_key in options['column_groups']:
                partner_sum = results.get(column_group_key, {})
                partner_values[column_group_key].update({
                    'country_code': partner_sum.get('country_code', 'UNKNOWN'),
                    'vat_number': partner_sum.get('vat_number', 'UNKNOWN'),
                    'total_amount_A3': partner_sum.get('goods', 0.0),
                    'total_amount_A4': partner_sum.get('goods_42_63', 0.0),
                    'total_amount_A5': partner_sum.get('triangular', 0.0),
                    'total_amount_A6': partner_sum.get('services', 0.0),
                    'total_amount_A7': partner_sum.get('goods_stocks', 0.0),
                })
            lines.append((0, super()._get_report_line_partner(report, options, partner, partner_values)))
        return lines

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options)

        ec_operation_category = options.get('sales_report_taxes', {'goods': tuple(), 'goods_42_63': tuple(), 'triangular': tuple(), 'services': tuple(), 'goods_stocks': tuple()})

        tag_mapping = {
            'goods': 'l10n_si.account_account_tag_l10n_si_rp_A3',
            'goods_42_63': 'l10n_si.account_account_tag_l10n_si_rp_A4',
            'triangular': 'l10n_si.account_account_tag_l10n_si_rp_A5',
            'services': 'l10n_si.account_account_tag_l10n_si_rp_A6',
            'goods_stocks': 'l10n_si.account_account_tag_l10n_si_rp_A7',
        }

        for key, ref in tag_mapping.items():
            tag_id = self.env.ref(ref).id
            ec_operation_category[key] = (tag_id,)

        # Without it the query will search for tax ids instead of tags
        ec_operation_category['use_taxes_instead_of_tags'] = False

        options['sales_report_taxes'] = ec_operation_category

    def _init_core_custom_options(self, report, options, previous_options=None):
        super()._init_core_custom_options(report, options, previous_options)

        options['ec_tax_filter_selection'].extend([
            {'id': 'goods_42_63', 'name': _('Goods - 42-63'), 'selected': True},
            {'id': 'goods_stocks', 'name': _('Goods - Stocks'), 'selected': True},
        ])
