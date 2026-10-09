# Copyright 2017 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MisBudget(models.Model):
    _name = "mis.budget"
    _description = "MIS Budget by KPI"
    _inherit = ["mis.budget.abstract", "mail.thread"]

    report_id = fields.Many2one(
        comodel_name="mis.report", string="MIS Report Template", required=True
    )
    item_ids = fields.One2many(
        comodel_name="mis.budget.item", inverse_name="budget_id", copy=True
    )
