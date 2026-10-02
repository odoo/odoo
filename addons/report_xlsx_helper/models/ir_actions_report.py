# Copyright 2009-2018 Noviat.
# License AGPL-3.0 or later (https://www.gnuorg/licenses/agpl.html).

from odoo import _, api, models
from odoo.exceptions import UserError


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    @api.model
    def _render_xlsx(self, report_ref, docids, data):
        if not self and self.env.context.get("report_name"):
            report_model_name = "report.{}".format(self.env.context["report_name"])
            report_model = self.env.get(report_model_name)
            if report_model is None:
                raise UserError(_("%s model was not found") % report_model_name)
            return report_model.create_xlsx_report(docids, data)
        return super()._render_xlsx(report_ref, docids, data)
