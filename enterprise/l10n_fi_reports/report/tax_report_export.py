from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero

PERIOD_LENGTH_CODE_PER_PERIOD_TYPE = {
    'month': 'K',
    'quarter': 'Q',
    'fiscalyear': 'V',
}


class ReportL10nFiReportsTaxReportExport(models.AbstractModel):
    _name = 'report.l10n_fi_reports.tax_report_export'
    _description = 'L10n FI Reports - Tax Report export'

    @api.model
    def _get_report_values(self, docids, data=None):
        options = data['options']
        report = self.env['account.report'].browse(docids)
        tax_period_length = PERIOD_LENGTH_CODE_PER_PERIOD_TYPE.get(options['date']['period_type'])
        date_to = fields.Date.to_date(options['date']['date_to'])
        template_data = {
            # Actually in server time so by default UTC, nothing indicates which timezone we should follow here
            'timestamp': data['timestamp'],
            'business_id': self.env.company.company_registry,
            'tax_period_length': tax_period_length,
            'tax_period_year': date_to.year,
            'contact_phone_number': self.env.company.phone,
        }

        if tax_period_length == 'K':
            template_data['tax_period'] = date_to.month
        elif tax_period_length == 'Q':
            template_data['tax_period'] = date_to.month // 4 + 1
        else:
            template_data['tax_period'] = False

        total_in_tax_report = 0
        for line in report._get_lines(options):
            if report._get_markup(line['id']) == 'total':
                continue

            line_code = line.get('code')
            if not line_code:
                raise UserError(_(
                    "Make sure that you update the Finland localization(l10n_fi) module to have latest changes. "
                    "Each tax report line should have a code."
                ))

            template_data[line_code] = line['columns'][0]['no_format']
            total_in_tax_report += line['columns'][0]['no_format']

        template_data['has_no_activity'] = float_is_zero(total_in_tax_report, precision_digits=self.env.company.currency_id.decimal_places)
        return {
            'doc_ids': docids,
            'doc_model': self.env['account.report'],
            'data': template_data,
            'docs': docids,
        }
