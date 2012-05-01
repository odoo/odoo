# -*- coding: utf-8 -*-
from osv import fields, osv
import random
import string

class ir_attachment(osv.osv):
    _inherit = 'ir.attachment'

    def pad_generate_url(self, cr, uid, model):
        pad_url_template = self.pool.get('res.users').browse(cr,uid,[uid])[0].company_id.pad_url_template
        s = string.ascii_uppercase + string.digits
        salt = ''.join([s[random.randint(0, len(s) - 1)] for i in range(8)])
        template_vars = {
            'db' : cr.dbname,
            'model' : model,
            'salt' : salt,
        }
        return pad_url_template % template_vars

    def pad_get(self, cr, uid, model, id):
        if not id: return False
        attachment = self.search(cr, uid, [('res_model', '=', model), ('res_id', '=', id), ('type', '=', 'url'), ('name', '=', 'Pad')])
        if attachment:
            return self.read(cr, uid, attachment)[0]['url']
        else:
            url = self.pad_generate_url(cr, uid, model)
            self.create(cr, uid, {
                'res_model' : model,
                'res_id' : id,
                'type' : 'url',
                'name' : 'Pad',
                'url' : url,
            })
            return url

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
