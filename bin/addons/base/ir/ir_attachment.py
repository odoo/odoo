# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields,osv
from osv.orm import except_orm
import tools

class ir_attachment(osv.osv):
    def check(self, cr, uid, ids, mode, context=None):
        if not ids:
            return
        ima = self.pool.get('ir.model.access')
        if isinstance(ids, (int, long)):
            ids = [ids]
        cr.execute('select distinct res_model from ir_attachment where id = ANY (%s)', (ids,))
        for obj in cr.fetchall():
            if obj[0]:
                ima.check(cr, uid, obj[0], mode, context=context)

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
            if m['res_model']:
                if m['res_model'] not in cache:
                    cache[m['res_model']] = ima.check(cr, uid, m['res_model'], 'read',
                                                      raise_exception=False, context=context)
                if not cache[m['res_model']]:
                    ids.remove(m['id'])

        if count:
            return len(ids)
        return ids

    def read(self, cr, uid, ids, fields_to_read=None, context=None, load='_classic_read'):
        self.check(cr, uid, ids, 'read', context=context)
        return super(ir_attachment, self).read(cr, uid, ids, fields_to_read, context, load)

    def write(self, cr, uid, ids, vals, context=None):
        self.check(cr, uid, ids, 'write', context=context)
        return super(ir_attachment, self).write(cr, uid, ids, vals, context)

    def copy(self, cr, uid, id, default=None, context=None):
        self.check(cr, uid, [id], 'write', context=context)
        return super(ir_attachment, self).copy(cr, uid, id, default, context)

    def unlink(self, cr, uid, ids, context=None):
        self.check(cr, uid, ids, 'unlink', context=context)
        return super(ir_attachment, self).unlink(cr, uid, ids, context)

    def create(self, cr, uid, values, context=None):
        if 'res_model' in values and values['res_model'] != '':
            self.pool.get('ir.model.access').check(cr, uid, values['res_model'], 'create', context=context)
        return super(ir_attachment, self).create(cr, uid, values, context)

    def action_get(self, cr, uid, context=None):
        dataobj = self.pool.get('ir.model.data')
        data_id = dataobj._get_id(cr, 1, 'base', 'action_attachment')
        res_id = dataobj.browse(cr, uid, data_id, context).res_id
        return self.pool.get('ir.actions.act_window').read(cr, uid, res_id, [], context)    

    def _name_get_resname(self, cr, uid, ids, object,method, context):
        data = {}
        for attachment in self.browse(cr, uid, ids, context=context):
            model_object = attachment.res_model
            res_id = attachment.res_id
            if model_object and res_id:
                model_pool = self.pool.get(model_object)
                res = model_pool.name_get(cr,uid,[res_id],context)
                data[attachment.id] = res[0][1]
            else:
                 data[attachment.id] = False
        return data

    _name = 'ir.attachment'
    _columns = {
        'name': fields.char('Attachment Name',size=64, required=True),
        'datas': fields.binary('Data'),
        'datas_fname': fields.char('Filename',size=64),
        'description': fields.text('Description'),
        # Not required due to the document module !
        'res_name': fields.function(_name_get_resname, type='char', string='Resource Name', method=True),
        'res_model': fields.char('Resource Object',size=64, readonly=True),
        'res_id': fields.integer('Resource ID', readonly=True),
        'link': fields.char('Link', size=256),
        'create_date': fields.datetime('Date Created', readonly=True),
        'create_uid':  fields.many2one('res.users', 'Creator', readonly=True),
    }

ir_attachment()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

