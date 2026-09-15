from odoo import models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _prepare_rendering_context(self, report, docids, data):
        data = super()._prepare_rendering_context(report, docids, data)
        data["din_header_spacing"] = report.get_paperformat().header_spacing
        return data
