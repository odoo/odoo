from odoo import _, models
from odoo.exceptions import UserError


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _pre_render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        # Check for reports only available for invoices.
        if self._get_report(report_ref).report_name == 'l10n_th.report_commercial_invoice':
            invoices = self.env['account.move'].browse(res_ids)
            if any(not x.is_invoice(include_receipts=True) for x in invoices):
                raise UserError(_("Only invoices could be printed."))

        return super()._pre_render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
