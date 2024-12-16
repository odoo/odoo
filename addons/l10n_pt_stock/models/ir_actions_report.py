from odoo import models, _
from odoo.exceptions import ValidationError


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        if self._get_report(report_ref).report_name == 'stock.report_deliveryslip':
            pickings = self.env['stock.picking'].browse(res_ids)
            for picking in pickings.filtered(lambda p: p.company_id.account_fiscal_country_id.code == 'PT'):
                picking.update_l10n_pt_print_version()
        return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
