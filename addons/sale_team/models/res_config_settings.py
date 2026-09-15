from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    is_membership_multi = fields.Boolean(
        string="Multi Teams",
        config_parameter="sale_team.membership_multi",
    )
