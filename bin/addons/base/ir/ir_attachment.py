# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
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
            if m['res_model'] in cache:
                if not cache[m['res_model']]:
                    ids.remove(m['id'])
                continue
            cache[m['res_model']] = ima.check(cr, uid, m['res_model'], 'read',
                                              raise_exception=False)

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

    def __init__(self, *args, **kwargs):
        r = super(ir_attachment, self).__init__(*args, **kwargs)
        self.pool.get('ir.model.access').register_cache_clearing_method(self._name, 'clear_cache')
        return r

    def __del__(self):
        self.pool.get('ir.model.access').unregister_cache_clearing_method(self._name, 'clear_cache')
        return super(ir_attachment, self).__del__()

    _name = 'ir.attachment'
    _columns = {
        'name': fields.char('Attachment Name',size=64, required=True),
        'datas': fields.binary('Data'),
        'datas_fname': fields.char('Data Filename',size=64),
        'description': fields.text('Description'),
        # Not required due to the document module !
        'res_model': fields.char('Resource Object',size=64, readonly=True),
        'res_id': fields.integer('Resource ID', readonly=True),
        'link': fields.char('Link', size=256)
    }
ir_attachment()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

