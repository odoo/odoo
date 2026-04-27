import logging

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class FinlandECSalesReportCustomHandler(models.AbstractModel):
    _name = 'l10n_fi_reports.ec.sales.report.handler'
    _inherit = 'account.ec.sales.report.handler'
    _description = 'Finland EC Sales Report Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        lines = []

        totals_by_column_group = {
            column_group_key: {
                'goods': 0.0,
                'services': 0.0,
                'triangular': 0.0,
                'balance': 0.0,
            }
            for column_group_key in options['column_groups']
        }

        for partner, results in super()._query_partners(report, options):
            partner_values = defaultdict(dict)

            for column_group_key in options['column_groups']:
                partner_sum = results.get(column_group_key, {})
                partner_values[column_group_key]['country_code'] = partner_sum.get('country_code') or 'UNKNOWN'
                partner_values[column_group_key]['vat_number'] = partner_sum.get('vat_number') or ''
                partner_values[column_group_key]['goods'] = goods = partner_sum.get('goods') or 0.0
                partner_values[column_group_key]['services'] = services = partner_sum.get('services') or 0.0
                partner_values[column_group_key]['triangular'] = triangular = partner_sum.get('triangular') or 0.0
                line_balance = goods + services + triangular
                partner_values[column_group_key]['balance'] = line_balance

                totals_by_column_group[column_group_key]['goods'] += goods
                totals_by_column_group[column_group_key]['services'] += services
                totals_by_column_group[column_group_key]['triangular'] += triangular
                totals_by_column_group[column_group_key]['balance'] += line_balance

            lines.append((0, super()._get_report_line_partner(report, options, partner, partner_values)))

        lines.append((0, super()._get_report_line_total(report, options, totals_by_column_group)))
        return lines

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        options['buttons'].append({
            'name': _("Generate VSRALVYV"),
            'sequence': 150,
            'action': 'export_file',
            'action_param': 'l10n_fi_export_ec_sales_list_report',
            'file_export_type': _('TXT'),
        })

        try:
            tax_report_goods_eu_tag = self.env.ref('l10n_fi.tax_report_base_sales_goods_eu_tax_tag')
            tax_report_services_eu_tag = self.env.ref('l10n_fi.tax_report_base_sales_service_eu_tag')
            tax_report_triangular_eu_tag = self.env.ref('l10n_fi.tax_report_base_triangular_eu_tax_tag')
        except ValueError as err:
            _logger.warning(err)
            raise UserError(_("Make sure to update Finland localization to have the right expressions to generate your EC Sales report."))

        ec_operation_category = options.get('sales_report_taxes') or {}
        ec_operation_category['goods'] = tax_report_goods_eu_tag._get_matching_tags().ids
        ec_operation_category['services'] = tax_report_services_eu_tag._get_matching_tags().ids
        ec_operation_category['triangular'] = tax_report_triangular_eu_tag._get_matching_tags().ids

        # Unset this as 'use_taxes_instead_of_tags' should never be used outside the generic ec sales report
        ec_operation_category['use_taxes_instead_of_tags'] = False

        options.update({'sales_report_taxes': ec_operation_category})

    @api.model
    def l10n_fi_export_ec_sales_list_report(self, options):
        if options['date']['period_type'] != 'month':
            raise UserError(_("The declaration should be month by month. Please select only a month period."))
        if not self.env.company.company_registry:
            raise UserError(_("Business ID is needed on your current company to export VSRALVYV."))

        generated_time = fields.Datetime.now()
        timestamp_date = generated_time.strftime('%d%m%Y')
        timestamp_time = generated_time.strftime('%H%M%S')
        file_content = self.env['ir.actions.report']._render_qweb_text(
            report_ref='l10n_fi_reports.action_generate_ec_sales_list_report_export',
            docids=[options['report_id']],
            data={
                'timestamp': f'{timestamp_date}{timestamp_time}',
                'options': options,
            },
        )
        return {
            'file_name': f'V_{timestamp_date}_{timestamp_time}_VSRALVYV.txt',
            'file_content': file_content[0],
            'file_type': 'txt',
        }
