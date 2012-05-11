# -*- coding: utf-8 -*-
from osv import fields, osv
import random
import string


class pad_common(osv.osv_memory):
    _name = 'pad.common'
    
    def pad_generate_url(self, cr, uid, model, context=None):
        pad_url_template = self.pool.get('res.users').browse(cr,uid,[uid])[0].company_id.pad_url_template
        s = string.ascii_uppercase + string.digits
        salt = ''.join([s[random.randint(0, len(s) - 1)] for i in range(8)])
        template_vars = {
            'db' : cr.dbname,
            'model' : model,
            'salt' : salt,
        }
        return pad_url_template % template_vars

    def _pad_api_key(self, cr, uid, context=None):
        return self.pool.get('res.users').browse(cr,uid,[uid])[0].company_id.etherpad_api_key

    def _pad_user_name(self, cr, uid, context=None):
        return self.pool.get('res.users').browse(cr,uid,[uid])[0].name
    
    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'pad_url':self.pool.get('ir.attachment').pad_generate_url(cr, uid, self._name),            
        })
        return super(pad_common, self).copy(cr, uid, id, default, context)
    
    def create(self, cr, uid, vals, context=None):        
        record_id =  super(pad_common, self).create(cr, uid, vals, context=context)
        res = self.browse(cr,uid, record_id)        
        url = res.pad_url
        if url:
            self.pool.get('ir.attachment').create(cr, uid, {
                'res_model' : self._name,
                'res_id' : record_id,
                'type' : 'url',
                'name' : 'Pad',
                'url' : url,
            })
        return record_id
        
    _columns = {
        'pad_url': fields.char('Full Screen', size=512),
        'pad_api_key': fields.function(_pad_api_key, type='text', string="Pad API Key"),
        'pad_user_name': fields.function(_pad_user_name, type='text', string="Current Pad User"),
    }
    _defaults = {
        'pad_url': lambda self, cr, uid, context: self.pool.get('ir.attachment').pad_generate_url(cr, uid, self._name)
    }
    
    def action_open_pad(self, cr, uid, ids, context=None):
        """Get pad action
        """
        url = self.browse(cr, uid, ids[0]).pad_url
        return {
            'type': 'ir.actions.act_url',
            'url': url
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
