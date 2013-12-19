from openerp.osv import fields, osv

class calendar_config_settings(osv.osv_memory):
    #_name = 'calendar.config.settings'
    _inherit = 'base.config.settings'
    
    _columns = {
        'google_cal_sync': fields.boolean("Show tutorial to know how to get my 'Client ID' and my 'Client Secret'"),
        'cal_client_id': fields.char("Client_id"),
        'cal_client_secret': fields.char("Client_key"),
        'server_uri': fields.char('URI for tuto')
    }
    
    
    def set_calset(self,cr,uid,ids,context=None) :
        params = self.pool.get('ir.config_parameter')
        me = self.browse(cr,uid,ids[0],context=context)
        #new_val = dict(cal_client_id=me.cal_client_id,cal_client_secret=me.cal_client_secret)
        
        new_val_id = {
                    'key' : 'google_calendar_client_id',
                    'value' : me.cal_client_id
                   }
        new_val_secret = {
                    'key' : 'google_calendar_client_secret',
                    'value' : me.cal_client_secret
                   }
        
        exist_id = params.search(cr,uid,[('key','=','google_calendar_client_id')],context=context)
        exist_secret = params.search(cr,uid,[('key','=','google_calendar_client_secret')],context=context)
                
        if exist_id:
            params.write(cr,uid,exist_id[0],new_val_id,context=context)            
        else:
            params.create(cr,uid,new_val_id,context=context)
            
        if exist_secret:
            params.write(cr,uid,exist_secret[0],new_val_secret,context=context)            
        else:
            params.create(cr,uid,new_val_secret,context=context)
        

    def get_default_all(self,cr,uid,ids,context=None):
        params = self.pool.get('ir.config_parameter')
        
        cal_client_id = params.get_param(cr, uid, 'google_calendar_client_id',default='',context=context)
        cal_client_secret = params.get_param(cr, uid, 'google_calendar_client_secret',default='',context=context)
        server_uri= "%s/google_account/authentication" % params.get_param(cr, uid, 'web.base.url',default="http://yourcompany.my.openerp.com",context=context)          
        return dict(cal_client_id=cal_client_id,cal_client_secret=cal_client_secret,server_uri=server_uri)
        
        
        
    

