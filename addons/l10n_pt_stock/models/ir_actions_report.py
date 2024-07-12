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
                # A transfer validated without a transport document prints as a plain delivery slip.
                if issued := pickings.filtered('l10n_pt_document_number'):
                    self._l10n_pt_report_compliance('stock.picking', issued.ids, compute_hash=True)
        return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)

    def _get_rendering_context(self, report, docids, data):
        # EXTENDS base
        # A Portuguese transfer prints its goods by their name on Portuguese documents, so a reprint
        # matches the original after the product was renamed outside Portugal.
        data = super()._get_rendering_context(report, docids, data)
        if report.report_name == 'stock.report_deliveryslip' and 'docs' in data and any(
            picking.country_code == 'PT' for picking in data['docs']
        ):
            data['docs'] = data['docs'].with_context(l10n_pt_frozen_product_name=True)
        return data

    def _l10n_pt_templates_with_print_version(self):
        return super()._l10n_pt_templates_with_print_version() + ['stock.report_deliveryslip']
