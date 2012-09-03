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
        url = '%s/p/%s-%s-%s' % (pad_server, cr.dbname, self._name, salt)
        return url

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
    # override read and copy to generate url and store the content if empty

    def default_get(self, cr, uid, fields, context=None):
        data = super(pad_common, self).default_get(cr, uid, fields, context)
        for k in fields:
            field = self._all_columns[k].column
            if hasattr(field,'pad_content_field'):
                data[k] = self.pad_generate_url(cr, uid, context=context)
        return data

    def write(self, cr, uid, ids, vals, context=None):
        for k,v in vals.items():
            field = self._all_columns[k].column
            if hasattr(field,'pad_content_field'):
                vals[field.pad_content_field] = self.pad_get_content(cr, uid, v, context=context)
        return super(pad_common, self).write(cr, uid, ids, vals, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        for k,v in self._all_columns:
            field = v.column
            if hasattr(field,'pad_content_field'):
                default[k] = self.pad_generate_url(cr, uid, context)
        return super(pad_common, self).copy(cr, uid, id, default, context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
