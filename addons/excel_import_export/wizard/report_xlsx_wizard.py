# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)
import ast

from odoo import fields, models


class ReportXLSXWizard(models.TransientModel):
    _name = "report.xlsx.wizard"
    _description = "Generic Report Wizard, used with template reporting option"

    res_model = fields.Char()
    domain = fields.Char(string="Search Criterias")

    def action_report(self):
        action_id = self._context.get("report_action_id")
        action = self.env["ir.actions.report"].browse(action_id)
        res = action.read()[0]
        return res

    def safe_domain(self, str_domain):
        return ast.literal_eval(str_domain or "[]")
