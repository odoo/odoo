# Copyright 2017-2020 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MisBudgetByAccount(models.Model):
    _name = "mis.budget.by.account"
    _description = "MIS Budget by Account"
    _inherit = ["mis.budget.abstract", "mail.thread"]

    item_ids = fields.One2many(
        comodel_name="mis.budget.by.account.item", inverse_name="budget_id", copy=True
    )
    company_id = fields.Many2one(required=False)
    allow_items_overlap = fields.Boolean(
        help="If checked, overlap between budget items is allowed"
    )
