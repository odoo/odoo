# -*- coding: utf-8 -*-
from osv import fields, osv
import random
import re
import string
import urllib2
from tools.translate import _

class pad_common(osv.osv_memory):
    _name = 'pad.common'

    def pad_generate_url(self, cr, uid, context=None):
        pad_server = self.pool.get('res.users').browse(cr, uid, uid, context).company_id.pad_server
        # make sure pad server in the form of http://hostname
        if not pad_server:
            return ''
        if not pad_server.startswith('http'):
            pad_server = 'http://' + pad_server
        pad_server = pad_server.rstrip('/')
        # generate a salt
        s = string.ascii_uppercase + string.digits
        salt = ''.join([s[random.randint(0, len(s) - 1)] for i in range(10)])
        # contruct the url
        url = '%s/p/%s-%s-%s' % (pad_server, cr.dbname.replace('_','-'), self._name, salt)

        key = "4DxmsNIbnQUVQMW9S9tx2oLOSjFdrx1l"
        
        return {
            "url": url,
            "pad_server": pad_server,
            "dbname": cr.dbname.replace('_','-'),
            "name": self._name,
            "salt": salt,
        }

    def pad_get_content(self, cr, uid, url, context=None):
        content = ''
        if url:
            page = urllib2.urlopen('%s/export/html'%url).read()
            mo = re.search('<body>(.*)</body>',page)
            if mo:
                content = mo.group(1)
        return content

    # TODO
    # reverse engineer protocol to be setHtml without using the api key

    def write(self, cr, uid, ids, vals, context=None):
        self._set_pad_value(cr, uid, vals, context)
        return super(pad_common, self).write(cr, uid, ids, vals, context=context)

    def create(self, cr, uid, vals, context=None):
        self._set_pad_value(cr, uid, vals, context)
        return super(pad_common, self).create(cr, uid, vals, context=context)

    # Set the pad content in vals
    def _set_pad_value(self, cr, uid, vals, context=None):
        for k,v in vals.items():
            field = self._all_columns[k].column
            if hasattr(field,'pad_content_field'):
                vals[field.pad_content_field] = self.pad_get_content(cr, uid, v, context=context)        

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        for k,v in self._all_columns:
            field = v.column
            if hasattr(field,'pad_content_field'):
                pad = self.pad_generate_url(cr, uid, context)
                default[k] = pad['url']
        return super(pad_common, self).copy(cr, uid, id, default, context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
