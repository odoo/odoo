from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    enable_recaptcha = fields.Boolean(
        string="Enable reCAPTCHA",
        default=True,
        config_parameter="enable_recaptcha",
        groups="base.group_system",
    )
    recaptcha_public_key = fields.Char(
        string="Site Key",
        config_parameter="recaptcha_public_key",
        groups="base.group_system",
    )
    recaptcha_private_key = fields.Char(
        string="Secret Key",
        secret_parameter="recaptcha_private_key",
        groups="base.group_system",
    )
    recaptcha_min_score = fields.Float(
        string="Minimum score",
        default="0.7",
        config_parameter="recaptcha_min_score",
        groups="base.group_system",
        help="By default, should be one of 0.1, 0.3, 0.7, 0.9.\n1.0 is very likely a good interaction, 0.0 is very likely a bot",
    )
