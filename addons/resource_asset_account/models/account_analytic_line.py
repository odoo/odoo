from odoo import fields, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    asset_id = fields.Many2one(
        comodel_name="resource.asset",
        related="move_line_id.asset_id",
        string="Asset",
        help="Asset associated with this analytic entry, inherited from the accounting move line",
    )
