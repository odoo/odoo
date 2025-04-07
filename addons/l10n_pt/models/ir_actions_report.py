from odoo import models

from odoo.addons.l10n_pt.const import PT_CERTIFICATION_NUMBER


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        if self.env.company.account_fiscal_country_id.code == 'PT':
            if report_ref in ('account.report_hash_integrity', 'account.report_invoice_with_payments'):
                self.env['account.move']._l10n_pt_compute_missing_hashes()
                if report_ref == 'account.report_invoice_with_payments':
                    for move in self.env['account.move'].browse(res_ids):
                        move.update_l10n_pt_print_version()
        return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)

    def _get_rendering_context(self, report, docids, data):
        data = super()._get_rendering_context(report, docids, data)
        data['l10n_pt_certification_number'] = PT_CERTIFICATION_NUMBER
        return data
