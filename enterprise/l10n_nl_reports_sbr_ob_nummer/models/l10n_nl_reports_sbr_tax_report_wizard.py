from odoo import models

class L10nNlTaxReportSBRWizard(models.TransientModel):
    _inherit = 'l10n_nl_reports_sbr.tax.report.wizard'

    def _get_sbr_identifier(self):
        return self.env.company.l10n_nl_reports_sbr_ob_nummer or super()._get_sbr_identifier()
