from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    gelato_api_key = fields.Char(string="Gelato API Key", groups="base.group_system")
    gelato_webhook_secret = fields.Char(groups="base.group_system")
