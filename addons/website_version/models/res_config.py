from openerp import fields, models, api


class analytics_config_settings(models.TransientModel):

    _inherit = 'base.config.settings'
    
    ga_sync = fields.Boolean("Show tutorial to know how to get my 'Client ID' and my 'Client Secret'")
    ga_client_id = fields.Char('Client ID')
    ga_client_secret = fields.Char('Client Secret')
    google_management_authorization = fields.Char('Google authorization')
    
    @api.model
    def set_analytics(self, ids):
        params = self.env['ir.config_parameter']
        myself = self.browse(ids[0])
        params.set_param('google_management_client_id', myself.ga_client_id or '', groups=['base.group_system'])
        params.set_param('google_management_client_secret', myself.ga_client_secret or '', groups=['base.group_system'])
        
    @api.model
    def get_analytics(self, ids):
        params = self.env.get('ir.config_parameter')
        ga_client_id = params.get_param('google_management_client_id', default='')
        ga_client_secret = params.get_param('google_management_client_secret', default='')
        return dict(ga_client_id=ga_client_id, ga_client_secret=ga_client_secret)
