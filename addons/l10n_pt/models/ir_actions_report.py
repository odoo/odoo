from odoo import models

from odoo.addons.l10n_pt.const import PT_CERTIFICATION_NUMBER


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        if report_ref == "account.report_hash_integrity" and self.env['res.company'].browse(data.get('context', {}).get('active_id')).account_fiscal_country_id.code == 'PT':
            self.env['account.move']._l10n_pt_compute_missing_hashes()
        return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)

    def _get_rendering_context(self, report, docids, data):
        data = super()._get_rendering_context(report, docids, data)
        data['l10n_pt_certification_number'] = PT_CERTIFICATION_NUMBER
        data['l10n_pt_training_mode'] = any(
            doc.company_id.account_fiscal_country_id.code == 'PT' and doc.company_id.l10n_pt_training_mode
            for doc in data['docs']
            if 'company_id' in doc
        )
        return data
