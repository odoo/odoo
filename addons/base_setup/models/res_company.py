from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    external_email_server_default = fields.Boolean(
        "External Email Servers")
