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

from osv import fields, osv
from service import web_services
from tools.misc import UpdateableStr, UpdateableDict
from tools.translate import _
import netsvc
import pooler
import time
import wizard

class stock_location_product(osv.osv_memory):
    _name = "stock.location.product"
    _description = "Products by Location"
    _columns = {
                'from_date': fields.datetime('From'), 
                'to_date': fields.datetime('To'), 
                }

    def action_open_window(self, cr, uid, ids, context):
        mod_obj = self.pool.get('ir.model.data')
        for location_obj in self.read(cr, uid, ids, ['from_date', 'to_date']):
            result = mod_obj._get_id(cr, uid, 'product', 'product_search_form_view')
            id = mod_obj.read(cr, uid, result, ['res_id'])
            return {
                    'name': 'product', 
                    'view_type': 'form', 
                    'view_mode': 'tree,form', 
                    'res_model': 'product.product', 
                    'type': 'ir.actions.act_window', 
                    'context': {'location': context['active_id'], 
                           'from_date': location_obj['from_date'], 
                           'to_date': location_obj['to_date']}, 
                    'domain': [('type', '<>', 'service')], 
                    'search_view_id': id['res_id']
                    }

stock_location_product()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
