from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"
    _CREDENTIAL_FIELDS = {
        "gelato_api_key": "gelato_api_key",
        "gelato_webhook_secret": "gelato_webhook_secret",
    }

    gelato_api_key = fields.Char(
        string="Gelato API Key",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        groups="base.group_system",
    )
    gelato_webhook_secret = fields.Char(
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        groups="base.group_system",
    )
