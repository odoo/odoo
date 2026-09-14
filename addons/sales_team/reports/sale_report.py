from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    team_id = fields.Many2one(
        comodel_name="team.team",
        string="Sales Team",
        readonly=True,
    )

    def _get_fields_select(self) -> dict:
        return super()._get_fields_select() | {"team_id": "o.team_id"}

    def _get_fields_group_by(self) -> list:
        return [*super()._get_fields_group_by(), "o.team_id"]
