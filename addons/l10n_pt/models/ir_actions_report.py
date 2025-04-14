from odoo import models

from odoo.addons.l10n_pt.const import PT_CERTIFICATION_NUMBER


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _l10n_pt_report_compliance(self, model, res_ids, compute_hash=False, update_print_version=True):
        """
        Ensure compliance with PT requirements by:
        - Triggering the computation of missing hashes for documents before printing.
        - Updating the print version (original or reprint) to be displayed in documents.
        """
        Model = self.env[model]
        if compute_hash:
            Model._l10n_pt_compute_missing_hashes()
        if update_print_version:
            for record in Model.browse(res_ids):
                record.update_l10n_pt_print_version()

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        if self.env.company.account_fiscal_country_id.code == 'PT':
            report_ref_2_update_records_params = {
                'account.report_hash_integrity': ('account.move', True, False),
                'account.report_invoice_with_payments': ('account.move', True, True),
                'account.report_payment_receipt': ('account.payment', False, True),
            }
            if params := report_ref_2_update_records_params.get(self._get_report(report_ref).report_name):
                model, compute_hash, update_print_version = params
                self._l10n_pt_report_compliance(model, res_ids, compute_hash, update_print_version)
        return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)

    def _get_rendering_context(self, report, docids, data):
        data = super()._get_rendering_context(report, docids, data)
        data['l10n_pt_certification_number'] = PT_CERTIFICATION_NUMBER
        return data
