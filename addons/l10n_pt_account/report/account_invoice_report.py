from odoo import models, api


class ReportInvoiceWithoutPayment(models.AbstractModel):
    _inherit = 'report.account.report_invoice'

    @api.model
    def _get_report_values(self, docids, data=None):
        self.env['account.move'].l10n_pt_compute_missing_hashes(self.env.company.id)
        return super()._get_report_values(docids, data)
