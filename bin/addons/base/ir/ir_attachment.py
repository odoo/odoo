# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields,osv
from osv.orm import except_orm
import tools

class ir_attachment(osv.osv):

    def check(self, cr, uid, ids, mode):
        if not ids: 
            return
        ima = self.pool.get('ir.model.access')
        if isinstance(ids, (int, long)):
            ids = [ids]
        objs = self.browse(cr, uid, ids) or []
        for o in objs:
            if o and o.res_model:
                ima.check(cr, uid, o.res_model, mode)
    
    check = tools.cache()(check)
        
    def search(self, cr, uid, args, offset=0, limit=None, order=None,
            context=None, count=False):
        ids = super(ir_attachment, self).search(cr, uid, args, offset=offset, 
                                                limit=limit, order=order, 
                                                context=context, count=False)
        if not ids:
            if count:
                return 0
            return []
        models = super(ir_attachment,self).read(cr, uid, ids, ['id', 'res_model'])
        cache = {}
        ima = self.pool.get('ir.model.access')
        for m in models:
            if m['res_model'] not in cache:
                cache[m['res_model']] = ima.check(cr, uid, m['res_model'], 'read',
                                                  raise_exception=False)
            if not cache[m['res_model']]:
                ids.remove(m['id'])

        if count:
            return len(ids)
        return ids

    def read(self, cr, uid, ids, *args, **kwargs):
        self.check(cr, uid, ids, 'read')
        return super(ir_attachment, self).read(cr, uid, ids, *args, **kwargs)

    def write(self, cr, uid, ids, *args, **kwargs):
        self.check(cr, uid, ids, 'write')
        return super(ir_attachment, self).write(cr, uid, ids, *args, **kwargs)
    
    def copy(self, cr, uid, id, *args, **kwargs):
        self.check(cr, uid, [id], 'write')
        return super(ir_attachment, self).copy(cr, uid, id, *args, **kwargs)

    def unlink(self, cr, uid, ids, *args, **kwargs):
        self.check(cr, uid, ids, 'unlink')
        return super(ir_attachment, self).unlink(cr, uid, ids, *args, **kwargs)

    def create(self, cr, uid, values, *args, **kwargs):
        if 'res_model' in values and values['res_model'] != '':
            self.pool.get('ir.model.access').check(cr, uid, values['res_model'], 'create')
        return super(ir_attachment, self).create(cr, uid, values, *args, **kwargs)

    def clear_cache(self):
        self.check()    
    
    def action_get(self, cr, uid, context=None):
        dataobj = self.pool.get('ir.model.data')
        data_id = dataobj._get_id(cr, 1, 'base', 'action_attachment')
        res_id = dataobj.browse(cr, uid, data_id, context).res_id
        return self.pool.get('ir.actions.act_window').read(cr, uid, res_id, [], context)

    def __init__(self, *args, **kwargs):
        r = super(ir_attachment, self).__init__(*args, **kwargs)
        self.pool.get('ir.model.access').register_cache_clearing_method(self._name, 'clear_cache')
        return r

    def __del__(self):
        self.pool.get('ir.model.access').unregister_cache_clearing_method(self._name, 'clear_cache')
        return super(ir_attachment, self).__del__()

    def _get_preview(self, cr, uid, ids, name, arg, context=None):
        result = {}
        if context is None:
            context = {}
        context['bin_size'] = False
        for i in self.browse(cr, uid, ids, context=context):
            result[i.id] = False
            for format in ('png','PNG','jpg','JPG'):
                if (i.datas_fname or '').endswith(format):
                    result[i.id]= i.datas
        return result

    _name = 'ir.attachment'
    _columns = {
        'name': fields.char('Attachment Name',size=64, required=True),
        'datas': fields.binary('Data'),
        'preview': fields.function(_get_preview, type='binary', string='Image Preview', method=True),
        'datas_fname': fields.char('Filename',size=64),
        'description': fields.text('Description'),
        # Not required due to the document module !
        'res_model': fields.char('Resource Object',size=64, readonly=True),
        'res_id': fields.integer('Resource ID', readonly=True),
        'link': fields.char('Link', size=256),

        'create_date': fields.datetime('Date Created', readonly=True),
        'create_uid':  fields.many2one('res.users', 'Creator', readonly=True),
    }
ir_attachment()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

