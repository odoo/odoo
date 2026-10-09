# Copyright 2017-2020 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class MisBudgetAbstract(models.AbstractModel):
    _name = "mis.budget.abstract"
    _description = "MIS Budget (Abstract Base Class)"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True, tracking=True)
    description = fields.Char(tracking=True)
    date_range_id = fields.Many2one(comodel_name="date.range", string="Date range")
    date_from = fields.Date(required=True, string="From", tracking=True)
    date_to = fields.Date(required=True, string="To", tracking=True)
    state = fields.Selection(
        [("draft", "Draft"), ("confirmed", "Confirmed"), ("cancelled", "Cancelled")],
        required=True,
        default="draft",
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    def copy(self, default=None):
        self.ensure_one()
        if default is None:
            default = {}
        if "name" not in default:
            default["name"] = _("%s (copy)") % self.name
        return super().copy(default=default)

    @api.onchange("date_range_id")
    def _onchange_date_range(self):
        for rec in self:
            if rec.date_range_id:
                rec.date_from = rec.date_range_id.date_start
                rec.date_to = rec.date_range_id.date_end

    @api.onchange("date_from", "date_to")
    def _onchange_dates(self):
        for rec in self:
            if rec.date_range_id:
                if (
                    rec.date_from != rec.date_range_id.date_start
                    or rec.date_to != rec.date_range_id.date_end
                ):
                    rec.date_range_id = False

    def action_draft(self):
        self.write({"state": "draft"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_confirm(self):
        self.write({"state": "confirmed"})
