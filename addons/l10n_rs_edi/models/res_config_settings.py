from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_rs_edi_api_key = fields.Char(string="API Key", related="company_id.l10n_rs_edi_api_key", readonly=False)
    l10n_rs_edi_demo_env = fields.Boolean(related='company_id.l10n_rs_edi_demo_env', readonly=False)
