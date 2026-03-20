from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_rs_edi_api_key = fields.Char(string="eFaktura API Key")
    l10n_rs_edi_demo_env = fields.Boolean(string='Use Demo Environment', default=True)
