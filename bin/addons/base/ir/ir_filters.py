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

class ir_filters(osv.osv):
    '''
    Filters
    '''
    _name = 'ir.filters'
    _description = 'Filters'

    def _list_all_models(self, cr, uid, context=None):
        cr.execute("SELECT model, name from ir_model")
        return cr.fetchall()

    def get_filters(self, cr, uid, model):
        act_ids = self.search(cr,uid,[('model_id','=',model),('user_id','=',uid)])
        my_acts = self.read(cr, uid, act_ids, ['name', 'domain','context'])
        return my_acts
    
    def create_or_replace(self, cr, uid, vals, context=None):
        filter_id = None
        for filter in self.get_filters(cr, uid, vals['model_id']):
            if filter['name'].lower() == vals['name'].lower():
                filter_id = filter['id']
                break
        if filter_id:
            return self.write(cr, uid, filter_id, vals, context)
        return self.create(cr, uid, vals, context)


    _columns = {
        'name': fields.char('Action Name', size=64, translate=True, required=True),
        'user_id':fields.many2one('res.users', 'User', help='False means for every user'),
        'domain': fields.text('Domain Value', required=True),
        'context': fields.text('Context Value', required=True),
        'model_id': fields.selection(_list_all_models, 'Model', required=True),
    }
    
    _sql_constraints = [
        ('name_model_uid_uniq', 'UNIQUE(name, model_id, user_id)', 'Filter name must be unique!'),
    ]


ir_filters()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
