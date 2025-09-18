from odoo import fields, models
from odoo.tools import SQL


class AccountInvoiceReport(models.Model):
    """Extends the 'account.invoice.report' model to include sales team information.

    This module adds a Many2one field to link invoice reports to sales teams, enabling better
    tracking and analysis of sales performance by team."""

    _inherit = "account.invoice.report"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    team_id = fields.Many2one(comodel_name="crm.team", string="Sales Team")

    # ------------------------------------------------------------
    # QUERY METHODS
    # ------------------------------------------------------------

    def _select(self) -> SQL:
        return SQL("%s, move.team_id as team_id", super()._select())
