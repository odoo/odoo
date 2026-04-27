from odoo import models, fields


class L10nNlTaxReportSBRWizard(models.TransientModel):
    _inherit = 'l10n_nl_reports_sbr.tax.report.wizard'

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    password = fields.Char(default=lambda self: self.env.company.l10n_nl_reports_sbr_password, store=True)  # Deprecated

    def _additional_processing(self, options, kenmerk, closing_move):
        # OVERRIDE
        self.env['l10n_nl_reports_sbr.status.service'].create({
            'kenmerk': kenmerk,
            'company_id': self.env.company.id,
            'report_name': self.env['account.report'].browse(options['report_id']).name,
            'closing_entry_id': closing_move.id,
            'is_test': self.is_test,
        })
        status_service_cron = self.env.ref('l10n_nl_reports_sbr_status_info.cron_l10n_nl_reports_status_process')
        status_service_cron._trigger()
