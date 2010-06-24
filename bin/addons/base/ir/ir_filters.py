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

    _columns = {
        'name': fields.char('Action Name', size=64, translate=True, required=True), 
        'user_id':fields.many2one('res.users', 'User', help='False means for every user'), 
        'domain': fields.char('Domain Value', size=250, required=True), 
        'context': fields.char('Context Value', size=250, required=True), 
        'model_id': fields.selection(_list_all_models, 'Model', required=True), 
    }
    
    def get_filters(self, cr, uid, model):
        act_ids = self.search(cr,uid,[('model_id','=',model),('user_id','=',uid)])
        my_acts = self.read(cr, uid, act_ids, ['name', 'domain','context'])
        return my_acts

ir_filters()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
