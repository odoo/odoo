from odoo import fields, models


class CrmTeam(models.Model):
    _inherit = "crm.team"

    pos_config_ids = fields.One2many(
        comodel_name="pos.config",
        inverse_name="crm_team_id",
        string="Point of Sales",
    )
