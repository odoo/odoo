from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        if (
            self._get_report(report_ref).report_name == 'sale.report_saleorder'
            and self.env.company.account_fiscal_country_id.code == 'PT'
        ):
            self._l10n_pt_report_compliance('sale.order', res_ids, compute_hash=True, update_print_version=True)
        return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
