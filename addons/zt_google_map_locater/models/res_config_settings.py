from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    api_key = fields.Char(string="API Key")
    
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            api_key=self.env['ir.config_parameter'].sudo().get_param('zt_google_map_locater.api_key')
        )
        return res
    
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('zt_google_map_locater.api_key', self.api_key)        

    @api.model
    def get_values_api(self):
        google_api = self.env['ir.config_parameter'].sudo().get_param('zt_google_map_locater.api_key')
        return google_api
