from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    digest_emails = fields.Boolean(config_parameter="digest.default_digest_emails")
    digest_id = fields.Many2one(
        comodel_name="digest.digest",
        string="Digest Email",
        config_parameter="digest.default_digest_id",
    )
