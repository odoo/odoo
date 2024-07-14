from odoo import models, fields, api
from lxml.etree import Element
class L10nNlTaxReportSBRWizard(models.TransientModel):
    _inherit = 'l10n_nl_reports_sbr.tax.report.wizard'

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    password = fields.Char(related='company_id.l10n_nl_reports_sbr_password', readonly=False, store=True)

    def _additional_processing(self, options, kenmerk, closing_move):
        # OVERRIDE
        self.env['l10n_nl_reports_sbr.status.service'].create({
            'kenmerk': kenmerk,
            'company_id': self.env.company.id,
            'report_name': self.env['account.report'].browse(options['report_id']).name,
            'closing_entry_id': closing_move.id,
            'is_test': self.is_test,
        })._cron_process_submission_status()

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            node = arch.find(".//field[@name='can_report_be_sent']...")
            if node is not None:
                pwd_element = Element('field')
                pwd_element.set('name', 'company_id')
                pwd_element.set('invisible', '1')
                node.append(pwd_element)
        return arch, view
