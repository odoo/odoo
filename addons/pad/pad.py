# -*- coding: utf-8 -*-
from osv import fields, osv
import random
import string
from etherpad import EtherpadLiteClient


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

    def _pad_api_key(self, cr, uid, ids=None, name=None, arg=None , context=None):
        if not ids:
            return self.pool.get('res.users').browse(cr,uid,[uid],context)[0].company_id.etherpad_api_key
        res = {}
        for id in ids:
            res[id] = self.pool.get('res.users').browse(cr,uid,[uid],context)[0].company_id.etherpad_api_key            
        return res

    def _pad_user_name(self, cr, uid, ids=None, name = None, arg = None, context=None):
        if not ids:
            return self.pool.get('res.users').browse(cr,uid,[uid],context=context)[0].name
        res = {}
        for id in ids:
            res[id] = self.pool.get('res.users').browse(cr,uid,[uid],context=context)[0].name
        return res        
    
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
        api_key =  self._pad_api_key(cr, uid)
        if api_key:
            api_url = url[0:url.find("p/")] + "api/"            
            pad_id = url[url.find("p/")+2:]
            pad_author = self._pad_user_name(cr,uid)
            ep_client = EtherpadLiteClient(api_key, api_url)
            ep_client.createPad(pad_id,"")
            ep_client.createAuthor(pad_author)
        return record_id
        
    _columns = {
        'pad_url': fields.char('Full Screen', size=512),        
    }
    _defaults = {
        'pad_url': lambda self, cr, uid, context: self.pool.get('ir.attachment').pad_generate_url(cr, uid, self._name),
    }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
