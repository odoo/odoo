from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        if report_ref == "account.report_hash_integrity" and self.env['res.company'].browse(data.get('context', {}).get('active_id')).account_fiscal_country_id.code == 'PT':
            self.env['account.move']._l10n_pt_compute_missing_hashes()
        return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)
