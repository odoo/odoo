from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        if self._get_report(report_ref).report_name == 'stock.report_deliveryslip':
            # Keyed on each transfer's company, not the active one, which may not be PT. A transfer
            # that is no transport document (a pick, a receipt) prints as in any other country.
            pickings = self.env['stock.picking'].browse(res_ids).filtered(
                lambda p: p.country_code == 'PT' and p.l10n_pt_document_type
            )
            if pickings:
                pickings._l10n_pt_check_printable()
                self._l10n_pt_report_compliance('stock.picking', pickings.ids, compute_hash=True)
        return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)

    def _l10n_pt_templates_with_print_version(self):
        return super()._l10n_pt_templates_with_print_version() + ['stock.report_deliveryslip']
