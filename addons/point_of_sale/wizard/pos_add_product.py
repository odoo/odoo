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


class add_product(osv.osv_memory):
    _name = 'pos.add.product'
    _description = 'Add Product'

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'quantity': fields.float('Quantity', required=True),
    }
    _defaults = {
        'quantity': 1,
    }

    def select_product(self, cr, uid, ids, context=None):
        """
             To get the product and quantity and add in order .
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return : Return the add product form again for adding more product
        """
        if context is None:
            context = {}
        this = self.browse(cr, uid, ids[0], context=context)
        record_id = context and context.get('active_id', False)
        assert record_id, _('Active ID is not found')
        if record_id:
            order_obj = self.pool.get('pos.order')
            order_obj.add_product(cr, uid, record_id, this.product_id.id, this.quantity, context=context)
        return {
            'name': _('Add Product'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.add.product',
            'view_id': False,
            'target': 'new',
            'views': False,
            'type': 'ir.actions.act_window',
        }

    def close_action(self, cr, uid, ids, context=None):
        """
             To get the product and Make the payment .
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return : Return the Make Payment
        """
        if context is None:
            context = {}
        record_id = context and context.get('active_id', False)
        order_obj= self.pool.get('pos.order')
        this = self.browse(cr, uid, ids[0], context)
        order_obj.add_product(cr, uid, record_id, this.product_id.id, this.quantity, context=context)

        order_obj.write(cr, uid, [record_id], {'state': 'done'}, context=context)
        return {
            'name': _('Make Payment'),
            'context': context and context.get('active_id', False),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.make.payment',
            'view_id': False,
            'target': 'new',
            'views': False,
            'type': 'ir.actions.act_window',
        }

add_product()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

