# Copyright 2017 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class MisReportKpiExpression(models.Model):
    _inherit = "mis.report.kpi.expression"

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        args = args or []
        if "default_budget_id" in self.env.context:
            report_id = (
                self.env["mis.budget"]
                .browse(self.env.context["default_budget_id"])
                .report_id.id
            )
            if report_id:
                args += [("kpi_id.report_id", "=", report_id)]
                if "." in name:
                    args += [("subkpi_id.report_id", "=", report_id)]
        return super().name_search(name, args, operator, limit)
