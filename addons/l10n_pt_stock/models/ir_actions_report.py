from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        if (
            self._get_report(report_ref).report_name == 'stock.report_deliveryslip'
            and self.env.company.account_fiscal_country_id.code == 'PT'
        ):
            self._l10n_pt_report_compliance('stock.picking', res_ids, compute_hash=True, update_print_version=True)
        return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)

    def _l10n_pt_templates_with_print_version(self):
        return super()._l10n_pt_templates_with_print_version() + ['stock.report_deliveryslip']
