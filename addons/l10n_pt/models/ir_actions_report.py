from odoo import models

from odoo.addons.l10n_pt.const import PT_CERTIFICATION_NUMBER


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        # Overridden to compute the hash and QR code also for moves being printed (not through send&print).
        if (
            report_ref in ("account.report_hash_integrity", 'account.report_invoice_with_payments', 'account.report_invoice')
            and self.env.company.account_fiscal_country_id.code == 'PT'
        ):
            self.env['account.move']._l10n_pt_compute_missing_hashes()
        return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)

    def _get_rendering_context(self, report, docids, data):
        data = super()._get_rendering_context(report, docids, data)
        data['l10n_pt_certification_number'] = PT_CERTIFICATION_NUMBER
        if data.get('docs'):  # session reports in PoS do not have 'docs' key
            data['l10n_pt_training_mode'] = any(
                doc.company_id.account_fiscal_country_id.code == 'PT' and doc.company_id.l10n_pt_training_mode
                for doc in data['docs']
                if 'company_id' in doc
            )
        else:
            data['l10n_pt_training_mode'] = False
        return data
