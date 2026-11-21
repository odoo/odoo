from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bancontact_merchant_id = fields.Char(related="company_id.bancontact_merchant_id", readonly=False)
    bancontact_jwks_url = fields.Char("JWKS URL", compute="_compute_bancontact_jwks_url")

    @api.depends("company_id")
    def _compute_bancontact_jwks_url(self):
        for settings in self:
            settings.bancontact_jwks_url = f"{settings.company_id.get_base_url()}/bancontact_pay/jwks"

    def action_bancontact_regenerate_signing_key(self):
        self.company_id._bancontact_generate_signing_key()
