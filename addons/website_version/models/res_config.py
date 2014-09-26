from openerp.osv import fields, osv

class analytics_config_settings(osv.TransientModel):
    _inherit = 'base.config.settings'
    
    _columns = {
        'google_analytics_confirm': fields.boolean("Authorize requests"),
    }
    
    def set_analytics(self,cr,uid,ids,context=None) :
        params = self.pool['ir.config_parameter']
        myself = self.browse(cr,uid,ids[0],context=context)
        params.set_param(cr, uid, 'google_analytics_confirm', myself.google_analytics_confirm or '', groups=['base.group_system'], context=None)
        

    def get_analytics(self,cr,uid,ids,context=None):
        params = self.pool.get('ir.config_parameter')        
        google_analytics_confirm = params.get_param(cr, uid, 'google_analytics_confirm',default=False,context=context)
        return dict(google_analytics_confirm = google_analytics_confirm)