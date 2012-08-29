# -*- coding: utf-8 -*-
from osv import fields, osv
import random
import string
import urllib2
from tools.translate import _

class pad_common(osv.osv_memory):
    _name = 'pad.common'
    _pad_fields = []

    def pad_content(self, cr, uid, url ,context=None):
        content = urllib2.urlopen('%s/export/html'%url).read()
        return content

    def pad_generate_url(self, cr, uid, context=None):
        pad_url_template =  self.pool.get('res.users').browse(cr,uid, uid, context).company_id.pad_url_template
        s = string.ascii_uppercase + string.digits
        salt = ''.join([s[random.randint(0, len(s) - 1)] for i in range(8)])
        template_vars = {
            'db' : cr.dbname,
            'model' : self._name,
            'salt' : salt,
        }
        url = pad_url_template % template_vars
        return url

    # TODO
    # add attribute on columns pad_content_field = 
    # override default write to load the content at write and store it in the field
    # reverse engineer protocol to be setHtml without using the api key
    # override default get to generate urls
    # override read to generate url and store the content if empty

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        update = [(field,self.pad_generate_url(cr, uid, context)) for field in self._pad_fields]
        default.update(update)
        return super(pad_common, self).copy(cr, uid, id, default, context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
