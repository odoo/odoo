from odoo import api, fields, models


class PosSession(models.Model):
    _inherit = "pos.session"

    team_id = fields.Many2one(
        comodel_name="team.team",
        related="config_id.team_id",
        string="Sales Team",
        readonly=True,
    )

    @api.model
    def _get_model_names_to_load(self, config):
        data = super()._get_model_names_to_load(config)
        data += ["sale.order", "sale.order.line"]
        return data
