from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _pre_render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        # Append context data with the display_name_in_footer parameter
        if self._is_invoice_report(report_ref):
            if self.env['ir.config_parameter'].sudo().get_param('account.display_name_in_footer'):
                data = data and dict(data) or {}
                data.setdefault('display_name_in_footer', []).append("FR")

        return super()._pre_render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
