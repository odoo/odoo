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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class stock_location_product(osv.osv_memory):
    _name = "stock.location.product"
    _description = "Products by Location"
    _columns = {
        'from_date': fields.datetime('From'), 
        'to_date': fields.datetime('To'),
        'type': fields.selection([('inventory','Analyse Current Inventory'),
            ('period','Analyse a Period')], 'Analyse Type', required=True), 
    }

    def action_open_window(self, cr, uid, ids, context=None):
        """ To open location wise product information specific to given duration
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: An ID or list of IDs (but only the first ID will be processed)
         @param context: A standard dictionary 
         @return: Invoice type
        """
        if context is None:
            context = {}
        location_products = self.read(cr, uid, ids, ['from_date', 'to_date'], context=context)
        if location_products:
            return {
                'name': _('Current Inventory'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'product.product',
                'type': 'ir.actions.act_window',
                'context': {'location': context['active_id'],
                       'from_date': location_products[0]['from_date'],
                       'to_date': location_products[0]['to_date']},
                'domain': [('type', '<>', 'service')],
            }

stock_location_product()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
