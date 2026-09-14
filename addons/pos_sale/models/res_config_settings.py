from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_team_id = fields.Many2one(
        related="pos_config_id.team_id",
        string="Sales Team (PoS)",
        readonly=False,
    )
    pos_down_payment_product_id = fields.Many2one(
        related="pos_config_id.down_payment_product_id",
        readonly=False,
    )
