from odoo import api, fields, models


class ReportL10nFiReportsECSalesListExport(models.AbstractModel):
    _name = 'report.l10n_fi_reports.ec_sales_list_report_export'
    _description = 'L10n FI Report - EC Sales List export'

    @api.model
    def _get_report_values(self, docids, data=None):
        options = data['options']
        date_to = fields.Date.to_date(options['date']['date_to'])
        report = self.env['account.report'].browse(docids)
        template_data = {
            # Actually in server time so by default UTC, nothing indicates which timezone we should follow here
            'timestamp': data['timestamp'],
            'business_id': self.env.company.company_registry,
            'target_month': date_to.month,
            'target_year': date_to.year,
            'lines': [],
        }

        for line in report._get_lines(options):
            if report._get_markup(line['id']) == 'total':
                continue

            country_code_column, vat_number_column, goods_column, services_column, triangular_column = line['columns']
            template_data['lines'].append({
                'country_code': country_code_column['name'],
                'vat_number': vat_number_column['name'],
                'goods': goods_column['no_format'],
                'services': services_column['no_format'],
                'triangular': triangular_column['no_format'],
            })
        template_data['nb_lines'] = len(template_data['lines'])

        return {
            'doc_ids': docids,
            'doc_model': self.env['account.report'],
            'data': template_data,
            'docs': docids,
        }
