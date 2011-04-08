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

class stock_location_product(osv.osv_memory):
    _name = "stock.location.product"
    _description = "Products by Location"
    _columns = {
        'from_date': fields.datetime('From'), 
        'to_date': fields.datetime('To'), 
    }

    def action_open_window(self, cr, uid, ids, context=None):
        """ To open location wise product information specific to given duration
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: An ID or list of IDs if we want more than one 
         @param context: A standard dictionary 
         @return: Invoice type
        """
        mod_obj = self.pool.get('ir.model.data')
        for location_obj in self.read(cr, uid, ids, ['from_date', 'to_date'], context=context):
            return {
                'name': False, 
                'view_type': 'form', 
                'view_mode': 'tree,form', 
                'res_model': 'product.product', 
                'type': 'ir.actions.act_window', 
                'context': {'location': context['active_id'], 
                       'from_date': location_obj['from_date'], 
                       'to_date': location_obj['to_date']}, 
                'domain': [('type', '<>', 'service')], 
            }

stock_location_product()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
