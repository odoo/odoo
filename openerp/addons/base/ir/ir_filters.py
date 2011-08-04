# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from osv import osv, fields
from tools.translate import _

class ir_filters(osv.osv):
    '''
    Filters
    '''
    _name = 'ir.filters'
    _description = 'Filters'

    def copy(self, cr, uid, id, default=None, context=None):
        name = self.read(cr, uid, [id], ['name'])[0]['name']
        default.update({'name':_('%s (copy)') % name})
        return super(ir_filters, self).copy(cr, uid, id, default, context)
   
    def get_filters(self, cr, uid, model):
        act_ids = self.search(cr,uid,[('model_id','=',model),('user_id','=',uid)])
        my_acts = self.read(cr, uid, act_ids, ['name', 'domain','context'])
        return my_acts

    def create_or_replace(self, cr, uid, vals, context=None):
        filter_id = None
        lower_name = vals['name'].lower()
        matching_filters = [x for x in self.get_filters(cr, uid, vals['model_id'])
                                if x['name'].lower() == lower_name]
        if matching_filters:
            self.write(cr, uid, matching_filters[0]['id'], vals, context)
            return False
        return self.create(cr, uid, vals, context)

    def _auto_init(self, cr, context={}):
        super(ir_filters, self)._auto_init(cr, context)
        # Use unique index to implement unique constraint on the lowercase name (not possible using a constraint)
        cr.execute("SELECT indexname FROM pg_indexes WHERE indexname = 'ir_filters_name_model_uid_unique_index'")
        if not cr.fetchone():
            cr.execute('CREATE UNIQUE INDEX "ir_filters_name_model_uid_unique_index" ON ir_filters (lower(name), model_id, user_id)')

    _columns = {
        'name': fields.char('Filter Name', size=64, translate=True, required=True),
        'user_id':fields.many2one('res.users', 'User', help="The user this filter is available to. Keep empty to make it available to all users."),
        'domain': fields.text('Domain Value', required=True),
        'context': fields.text('Context Value', required=True),
        'model_id': fields.many2one('ir.model', 'Object',required=True),
    }
    _defaults = {
        'domain': '[]',
        'context':'{}',
    }

ir_filters()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
