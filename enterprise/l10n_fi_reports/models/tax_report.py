from odoo import _, fields, models
from odoo.exceptions import UserError


class FinlandTaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_fi_reports.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Finland Tax Report'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        options['buttons'].append({
            'name': _("Generate VSRALVKV"),
            'sequence': 150,
            'action': 'export_file',
            'action_param': 'l10n_fi_export_tax_report',
            'file_export_type': _('TXT'),
        })

    def l10n_fi_export_tax_report(self, options):
        error_messages = []
        if options['date']['period_type'] not in {'month', 'quarter', 'fiscalyear'}:
            error_messages.append(_("The declaration should be month by month, quarter per quarter or year by year. Please select only a right period."))
        if not self.env.company.company_registry:
            error_messages.append(_("The current company needs a Business ID to export VSRALVKV."))
        if not self.env.company.phone:
            error_messages.append(_("The current company needs a phone number to export VSRALVKV."))
        if error_messages:
            raise UserError(_("The file generation raises errors:\n %s", "\n".join(error_messages)))

        generated_time = fields.Datetime.now()
        timestamp_date = generated_time.strftime('%d%m%Y')
        timestamp_time = generated_time.strftime('%H%M%S')
        file_content = self.env['ir.actions.report']._render_qweb_text(
            report_ref='l10n_fi_reports.action_generate_tax_report_export',
            docids=[options['report_id']],
            data={
                'timestamp': f'{timestamp_date}{timestamp_time}',
                'options': options,
            },
        )
        return {
            'file_name': f'V_{timestamp_date}_{timestamp_time}_VSRALVKV.txt',
            'file_content': file_content[0],
            'file_type': 'txt',
        }
