from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    minlength = fields.Integer(
        "Minimum Password Length", config_parameter="auth_password_policy.minlength",
        help="Minimum number of characters passwords must contain, set to 0 to disable.",
        # password lower bounds must be naturals
        clean=lambda minlength: max(minlength, 0))
