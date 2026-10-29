from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    google_api_key = fields.Char(string="API Key",  readonly=False,
                                           related='company_id.google_api_key')
    
