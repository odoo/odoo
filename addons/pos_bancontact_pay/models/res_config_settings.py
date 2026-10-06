from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bancontact_merchant_id = fields.Char(related="company_id.bancontact_merchant_id", readonly=False)
