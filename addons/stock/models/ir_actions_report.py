from odoo import models

from ..tools import debug_log as dbg


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _pre_render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        if self._get_report(report_ref).report_name == "stock.report_picking":
            picking_ids, _data = self._normalize_render_args(res_ids, data, "pdf")
            if picking_ids:
                self.env["stock.picking"].sudo().browse(picking_ids).write(
                    {"printed": True}
                )
        return super()._pre_render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

    def _prepare_rendering_context(self, report, docids, data):
        data = super()._prepare_rendering_context(report, docids, data)
        if report.report_name == "stock.report_reception_report_label" and not docids:
            docids = data["docids"]
            dbg.logic.debug(
                "reception report label: docids taken from data (%d)", len(docids)
            )
            docs = self.env[report.model].browse(docids)
            data.update(
                {
                    "doc_ids": docids,
                    "docs": docs,
                }
            )
        return data
