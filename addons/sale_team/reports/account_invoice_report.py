from odoo import fields, models
from odoo.tools import SQL


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    team_id = fields.Many2one(
        comodel_name="team.team",
        string="Sales Team",
    )

    def _select(self) -> SQL:
        return SQL("%s, move.team_id as team_id", super()._select())
