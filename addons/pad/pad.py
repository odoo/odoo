# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import random
import re
import string
import urllib2
import logging
from openerp import SUPERUSER_ID
from openerp.tools.translate import _
from openerp.tools import html2plaintext
from py_etherpad import EtherpadLiteClient
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)

class pad_common(osv.osv_memory):
    _name = 'pad.common'

    def pad_is_configured(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return bool(user.company_id.pad_server)

    def pad_generate_url(self, cr, uid, context=None):
        company = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context).company_id

        pad = {
            "server" : company.pad_server,
            "key" : company.pad_key,
        }

        # make sure pad server in the form of http://hostname
        if not pad["server"]:
            return pad
        if not pad["server"].startswith('http'):
            pad["server"] = 'http://' + pad["server"]
        pad["server"] = pad["server"].rstrip('/')
        # generate a salt
        s = string.ascii_uppercase + string.digits
        salt = ''.join([s[random.SystemRandom().randint(0, len(s) - 1)] for i in range(10)])
        #path
        # etherpad hardcodes pad id length limit to 50
        path = '-%s-%s' % (self._name, salt)
        path = '%s%s' % (cr.dbname.replace('_','-')[0:50 - len(path)], path)
        # contruct the url
        url = '%s/p/%s' % (pad["server"], path)

        #if create with content
        if "field_name" in context and "model" in context and "object_id" in context:
            myPad = EtherpadLiteClient( pad["key"], pad["server"]+'/api')
            try:
                myPad.createPad(path)
            except urllib2.URLError:
                raise UserError(_("Pad creation failed, either there is a problem with your pad server URL or with your connection."))

            #get attr on the field model
            model = self.pool[context["model"]]
            field = model._fields[context['field_name']]
            real_field = field.pad_content_field

            #get content of the real field
            for record in model.browse(cr, uid, [context["object_id"]]):
                if record[real_field]:
                    myPad.setText(path, (html2plaintext(record[real_field]).encode('utf-8')))
                    #Etherpad for html not functional
                    #myPad.setHTML(path, record[real_field])

        return {
            "server": pad["server"],
            "path": path,
            "url": url,
        }

    def pad_get_content(self, cr, uid, url, context=None):
        content = ''
        if url:
            try:
                page = urllib2.urlopen('%s/export/html'%url).read()
                mo = re.search('<body>(.*)</body>',page)
                if mo:
                    content = mo.group(1)
            except:
                _logger.warning("No url found '%s'.", url)
        return content

    # TODO
    # reverse engineer protocol to be setHtml without using the api key

    def write(self, cr, uid, ids, vals, context=None):
        self._set_pad_value(cr, uid, vals, context)
        return super(pad_common, self).write(cr, uid, ids, vals, context=context)

    def create(self, cr, uid, vals, context=None):
        self._set_pad_value(cr, uid, vals, context)
        res = super(pad_common, self).create(cr, uid, vals, context=context)

        # In case the pad is created programmatically, the content is not filled in yet since it is
        # normally initialized by the JS layer
        pad_urls = {}
        for k, field in self._fields.iteritems():
            if hasattr(field, 'pad_content_field') and k not in vals:
                ctx = dict(context or {})
                ctx.update({
                    'model': self._name,
                    'field_name': k,
                    'object_id': res,
                })
                pad = self.pad_generate_url(cr, uid, ctx)
                pad_urls[k] = pad.get('url')
        if pad_urls:
            self.write(cr, uid, res, pad_urls, context=context)
        return res

    # Set the pad content in vals
    def _set_pad_value(self, cr, uid, vals, context=None):
        for k,v in vals.items():
            field = self._fields[k]
            if hasattr(field,'pad_content_field'):
                vals[field.pad_content_field] = self.pad_get_content(cr, uid, v, context=context)        

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        for k, field in self._fields.iteritems():
            if hasattr(field,'pad_content_field'):
                pad = self.pad_generate_url(cr, uid, context)
                default[k] = pad.get('url')
        return super(pad_common, self).copy(cr, uid, id, default, context)
