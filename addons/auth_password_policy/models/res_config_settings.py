from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    minlength = fields.Integer(
        string="Minimum Password Length",
        help="Minimum number of characters passwords must contain, set to 0 to disable.",
        default=0,
        config_parameter="auth_password_policy.minlength",
    )

    @api.onchange("minlength")
    def _on_change_mins(self):
        """Password lower bounds must be naturals"""
        self.minlength = max(0, self.minlength or 0)
