# Part of Odoo. See LICENSE file for full copyright and licensing details.
import csv
import io
from collections import defaultdict

from odoo import _, models
from odoo.exceptions import RedirectWarning


class DenmarkECSalesReportCustomHandler(models.AbstractModel):
    _name = 'l10n_dk.ec.sales.report.handler'
    _inherit = 'account.ec.sales.report.handler'
    _description = 'Denmark EC Sales Report Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        """
        Generate the dynamic lines for the report in a horizontal style
        (one line partner, one column per operation type).
        """

        lines = []

        totals_by_column_group = {
            column_group_key: {
                "goods": 0.0,
                "services": 0.0,
                "triangular": 0.0,
                "balance": 0.0,
            }
            for column_group_key in options['column_groups']
        }

        for partner, results in super()._query_partners(report, options):
            partner_values = defaultdict(dict)

            for column_group_key in options['column_groups']:
                partner_sum = results.get(column_group_key, {})
                partner_values[column_group_key]['vat_number'] = partner_sum.get('full_vat_number', '')
                partner_values[column_group_key]['country_code'] = partner_sum.get('country_code', 'UNKNOWN')
                partner_values[column_group_key]['goods'] = partner_sum.get('goods', 0.0)
                partner_values[column_group_key]['services'] = partner_sum.get('services', 0.0)
                partner_values[column_group_key]['triangular'] = partner_sum.get('triangular', 0.0)
                line_balance = partner_sum.get('goods', 0.0) + partner_sum.get('services', 0.0) + partner_sum.get('triangular', 0.0)
                partner_values[column_group_key]['balance'] = line_balance

                totals_by_column_group[column_group_key]['goods'] += partner_sum.get('goods', 0.0)
                totals_by_column_group[column_group_key]['services'] += partner_sum.get('services', 0.0)
                totals_by_column_group[column_group_key]['triangular'] += partner_sum.get('triangular', 0.0)
                totals_by_column_group[column_group_key]['balance'] += line_balance

            lines.append((0, super()._get_report_line_partner(report, options, partner, partner_values)))

        lines.append((0, super()._get_report_line_total(report, options, totals_by_column_group)))
        return lines

    def _custom_options_initializer(self, report, options, previous_options):
        """
        Add custom options for the invoice lines domain specific to Denmark

        Typically, the taxes account.report.expression ids relative to the country for the triangular, sale of goods
        or services.
        """
        super()._custom_options_initializer(report, options, previous_options)
        options.setdefault('buttons', []).append({
            'name': _('CSV'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'export_sales_report_to_csv',
            'file_export_type': _('CSV'),
        })

        report_goods_eu_tag = self.env.ref('l10n_dk.account_tax_report_line_section_b_product_eu_tag')
        report_services_eu_tag = self.env.ref('l10n_dk.account_tax_report_line_section_b_services_tag')
        report_triangular_eu_tag = self.env.ref('l10n_dk.account_tax_report_line_section_b_triangular_tag')

        ec_operation_category = options.get('sales_report_taxes', {})
        ec_operation_category['goods'] = report_goods_eu_tag._get_matching_tags().ids
        ec_operation_category['services'] = report_services_eu_tag._get_matching_tags().ids
        ec_operation_category['triangular'] = report_triangular_eu_tag._get_matching_tags().ids

        # Unset this as 'use_taxes_instead_of_tags' should never be used outside of the generic ec sales report
        ec_operation_category['use_taxes_instead_of_tags'] = False

        options.update({
            'sales_report_taxes': ec_operation_category,
            'rounding_unit': 'units',  # So that the report is rounded by default
        })

    def export_sales_report_to_csv(self, options):
        colname_to_idx = {col['expression_label']: idx for idx, col in enumerate(options.get('columns', []))}
        report = self.env['account.report'].browse(options['report_id'])

        company = self.env.company
        cvr_number = company.company_registry
        if not cvr_number:
            raise RedirectWarning(
                    _('No CVR number associated with your company.'),
                    self.env.ref('base.action_res_company_form').id,
                    _("Change the VAT number")
                )

        # First heading line:
        # Always start with 0, then our CVR number, then the word LIST, rest is empty
        csv_lines = [
            [0, cvr_number, 'LIST', '', '', '', '', '', ''],
        ]

        # We don't need formatting since we just need raw data
        options['no_format'] = True
        lines = report._get_lines(options)

        date_formatted = options['date'].get('date_to')
        index = 0
        for line in lines[:-1]:
            customer_vat = line['columns'][colname_to_idx['vat_number']].get('name', '')

            if not customer_vat:
                redirect_action = {
                    'view_mode': 'form',
                    'res_model': 'res.partner',
                    'type': 'ir.actions.act_window',
                    'res_id': int(report._get_model_info_from_id(line['id'])[1]),
                    'views': [(False, 'form')]
                }
                raise RedirectWarning(
                    _("Customer's VAT cannot be empty"),
                    redirect_action,
                    _("Change the VAT number")
                )

            country_code = line['columns'][colname_to_idx['country_code']].get('name', '')

            # Denmark government impose that country code for greece is EL
            if country_code == 'GR':
                country_code = 'EL'

            # line entry, should always start with 'id 2' format:
            # 2, id, end date of the report, our company cvr number, the partner country code, partner VAT, amounts for goods, triangular, services
            csv_lines.append(
                [
                    2,
                    index,
                    date_formatted,
                    cvr_number,
                    country_code,
                    customer_vat[2:],
                    round(line['columns'][colname_to_idx['goods']].get('no_format', 0)),
                    round(line['columns'][colname_to_idx['triangular']].get('no_format', 0)),
                    round(line['columns'][colname_to_idx['services']].get('no_format', 0)),
                ]
            )
            index += 1

        # Last line is the total line, first column is always 'id 10', then we get the number of lines with 'id 2' and after that the total balance
        # all the other columns should stay empty
        csv_lines.append(
            [
                10,
                index,
                round(lines[-1]['columns'][colname_to_idx['balance']]['no_format']) if lines else 0,
                '',
                '',
                '',
                '',
                '',
                ''
            ]
        )

        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=',')
        writer.writerows(csv_lines)

        return {
            'file_name': report.get_default_report_filename(options, 'csv'),
            'file_content': buf.getvalue().encode(),
            'file_type': 'csv',
        }
