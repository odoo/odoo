from openerp.osv import fields, osv

class analytics_config_settings(osv.TransientModel):
    _inherit = 'base.config.settings'
    
    _columns = {
        'ga_sync': fields.boolean("Show tutorial to know how to get my 'Client ID' and my 'Client Secret'"),
        'ga_client_id': fields.char('Client ID'),
        'ga_client_secret': fields.char('Client Secret'),
        'google_management_authorization': fields.char('Google authorization')
    }
    
    def set_analytics(self,cr,uid,ids,context=None) :
        params = self.pool['ir.config_parameter']
        myself = self.browse(cr,uid,ids[0],context=context)
        params.set_param(cr, uid, 'google_management_client_id', myself.ga_client_id or '', groups=['base.group_system'], context=None)
        params.set_param(cr, uid, 'google_management_client_secret', myself.ga_client_secret or '', groups=['base.group_system'], context=None)
        

    def get_analytics(self,cr,uid,ids,context=None):
        params = self.pool.get('ir.config_parameter')        
        ga_client_id = params.get_param(cr, uid, 'google_management_client_id',default='',context=context)
        ga_client_secret = params.get_param(cr, uid, 'google_management_client_secret',default='',context=context)
        return dict(ga_client_id=ga_client_id,ga_client_secret=ga_client_secret)
