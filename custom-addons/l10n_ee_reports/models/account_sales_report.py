# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from lxml import etree, objectify

from odoo import _, fields, models
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools import float_round


class EstonianECSalesReportCustomHandler(models.AbstractModel):
    _name = 'l10n_ee.ec.sales.report.handler'
    _inherit = 'account.ec.sales.report.handler'
    _description = 'Estonian EC Sales Report Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        lines = []

        for partner, results in super()._query_partners(report, options):
            partner_values = defaultdict(dict)
            for column_group_key in options['column_groups']:
                partner_sum = results.get(column_group_key, {})
                partner_values[column_group_key]['country_code'] = partner_sum.get('country_code', 'UNKNOWN')
                partner_values[column_group_key]['vat_number'] = partner_sum.get('vat_number', 'UNKNOWN')
                partner_values[column_group_key]['goods'] = partner_sum.get('goods', 0.0)
                partner_values[column_group_key]['triangular'] = partner_sum.get('triangular', 0.0)
                partner_values[column_group_key]['services'] = partner_sum.get('services', 0.0)
            lines.append((0, super()._get_report_line_partner(report, options, partner, partner_values)))

        return lines

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._init_core_custom_options(report, options, previous_options)

        ec_operation_category = options.get('sales_report_taxes', {'goods': tuple(), 'triangular': tuple(), 'services': tuple()})

        ec_operation_category['goods'] = tuple(self.env.ref('l10n_ee.tax_report_line_ec_goods_tag')._get_matching_tags().ids)
        ec_operation_category['triangular'] = tuple(self.env.ref('l10n_ee.tax_report_line_ec_triangular_tag')._get_matching_tags().ids)
        ec_operation_category['services'] = tuple(self.env.ref('l10n_ee.tax_report_line_ec_services_tag')._get_matching_tags().ids)
        options.update({'sales_report_taxes': ec_operation_category})

        options.setdefault('buttons', []).append({
            'name': _('XML'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'export_to_xml_sales_report',
            'file_export_type': _('XML'),
        })

    def export_to_xml_sales_report(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        date_to = fields.Date.from_string(options['date'].get('date_to'))
        if options['date']['period_type'] != 'month':
            raise UserError(_('Choose a month to export the IC Supply Report'))
        company = self.env.company
        if not company.company_registry:
            action = self.env.ref('base.action_res_company_form')
            raise RedirectWarning(_('No company registry number associated with your company. Please define one.'), action.id, _("Company Settings"))

        lines = report._get_lines(options)
        colexpr_to_idx = {col['expression_label']: idx for idx, col in enumerate(options.get('columns', []))}
        rows = []
        undefined_vat_partners = []
        for line in lines:
            vat_number = line['columns'][colexpr_to_idx['vat_number']].get('name', '')
            if not vat_number:
                undefined_vat_partners.append(line['name'])
            rows.append({
                'country_code': line['columns'][colexpr_to_idx['country_code']].get('name', ''),
                'vat_number': vat_number,
                'goods': int(float_round(line['columns'][colexpr_to_idx['goods']]['no_format'], precision_digits=0)),
                'triangular': int(float_round(line['columns'][colexpr_to_idx['triangular']]['no_format'], precision_digits=0)),
                'services': int(float_round(line['columns'][colexpr_to_idx['services']]['no_format'], precision_digits=0)),
            })

        if undefined_vat_partners:
            raise UserError(_('No VAT number defined for the following partners: %s', ', '.join(undefined_vat_partners)))

        xml_data = {
            'tax_payer_reg_code': company.company_registry,
            'year': date_to.year,
            'month': date_to.month,
            'rows': rows,
        }

        rendered_content = self.env['ir.qweb']._render('l10n_ee_reports.ec_sales_report_xml', xml_data)
        tree = objectify.fromstring(rendered_content)

        return {
            'file_name': report.get_default_report_filename(options, 'xml'),
            'file_content': etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding='utf-8'),
            'file_type': 'xml',
        }
