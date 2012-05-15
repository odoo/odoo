# -*- coding: utf-8 -*-
from osv import fields, osv
import random
import string
from etherpad import EtherpadLiteClient
import urllib2
from tools.translate import _


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
        url = pad_url_template % template_vars
        api_key =  self._pad_api_key(cr, uid)
        if api_key:
            api_url = url[0:url.find("p/")] + "api"
            pad_id = url[url.find("p/")+2:]
            pad_author = self._pad_user_name(cr,uid)
            ep_client = EtherpadLiteClient(api_key, api_url)
            try:
                ep_client.createPad(pad_id," ")
            except ValueError as strerror:
                raise osv.except_osv(_('Configuration Error !'),_("Etherpad Have Wrong API Key."))
            except urllib2.HTTPError as e:
                raise osv.except_osv(_('Configuration Error !'),_("Etherpad Have Wrong API URL."))
            except urllib2.URLError as e:
                raise osv.except_osv(_('Configuration Error !'),_("Etherpad Have Wrong Pad URL Template."))
        return url

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
            'pad_url':self.pad_generate_url(cr, uid, self._name),            
        })
        return super(pad_common, self).copy(cr, uid, id, default, context)
                    
    _columns = {
        'pad_url': fields.char('Full Screen', size=512),
        'pad_username': fields.function(_pad_user_name, string='Picked', type='char',size=64),
        
    }
    _defaults = {
        'pad_url': lambda self, cr, uid, context: self.pad_generate_url(cr, uid, self._name),
        'pad_username': lambda self, cr, uid, context: self._pad_user_name(cr,uid),
    }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
