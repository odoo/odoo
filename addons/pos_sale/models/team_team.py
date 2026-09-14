from odoo import fields, models


class TeamTeam(models.Model):
    _inherit = "team.team"

    pos_config_ids = fields.One2many(
        comodel_name="pos.config",
        inverse_name="team_id",
        string="Point of Sales",
    )
