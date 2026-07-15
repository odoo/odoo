from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _get_rendering_context(self, report, docids, data):
        data = super()._get_rendering_context(report, docids, data)
        if report.report_name == 'stock.report_reception_report_label' and not docids:
            docids = data['docids']
            docs = self.env[report.model].browse(docids)
            data.update({
                'doc_ids': docids,
                'docs': docs,
            })
        return data

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        result = super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
        if self._get_report(report_ref).report_name == "stock.report_picking" and res_ids:
            self.env["stock.picking"].browse(res_ids).filtered(lambda p: p.state == "assigned").write({"printed": True})
        return result
