from openerp.osv import fields, osv

class calendar_config_settings(osv.TransientModel):
    _inherit = 'base.config.settings'
    
    _columns = {
        'google_cal_sync': fields.boolean("Show tutorial to know how to get my 'Client ID' and my 'Client Secret'"),
        'cal_client_id': fields.char("Client_id"),
        'cal_client_secret': fields.char("Client_key"),
        'server_uri': fields.char('URI for tuto')
    }
    
    def set_calset(self,cr,uid,ids,context=None) :
        params = self.pool['ir.config_parameter']
        myself = self.browse(cr,uid,ids[0],context=context)
        params.set_param(cr, uid, 'google_calendar_client_id', myself.cal_client_id.strip() or '', groups=['base.group_system'], context=None)
        params.set_param(cr, uid, 'google_calendar_client_secret', myself.cal_client_secret.strip() or '', groups=['base.group_system'], context=None)
        

    def get_default_all(self,cr,uid,ids,context=None):
        params = self.pool.get('ir.config_parameter')
        
        cal_client_id = params.get_param(cr, uid, 'google_calendar_client_id',default='',context=context)
        cal_client_secret = params.get_param(cr, uid, 'google_calendar_client_secret',default='',context=context)
        server_uri= "%s/google_account/authentication" % params.get_param(cr, uid, 'web.base.url',default="http://yourcompany.odoo.com",context=context)
        return dict(cal_client_id=cal_client_id,cal_client_secret=cal_client_secret,server_uri=server_uri)
        
        
        
    

