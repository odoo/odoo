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
from tools.translate import _
import tools

class stock_change_product_qty(osv.osv_memory):
    _name = "stock.change.product.qty"
    _description = "Change Product Quantity"
    _columns = {
        'product_id' : fields.many2one('product.product', 'Product'),
        'new_quantity': fields.float('Quantity', required=True, help='This quantity is expressed in the Default UoM of the product.'),
        'prodlot_id': fields.many2one('stock.production.lot', 'Production Lot', domain="[('product_id','=',product_id)]"),
        'location_id': fields.many2one('stock.location', 'Location', required=True, domain="[('usage', '=', 'internal')]"),
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        result = super(stock_change_product_qty, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
        product_id = context and context.get('active_id', False) or False

        if (context.get('active_model') == 'product.product') and product_id:
            prod_obj = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            fields = result.get('fields', {})
            if fields and (prod_obj.track_production == True) and (fields.get('prodlot_id')):
                result['fields']['prodlot_id']['required'] =  True
            else:
                result['fields']['prodlot_id']['required'] = False
        return result

    def default_get(self, cr, uid, fields, context):
        """ To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values
         @param context: A standard dictionary
         @return: A dictionary which of fields with values.
        """
        product_id = context and context.get('active_id', False) or False
        res = super(stock_change_product_qty, self).default_get(cr, uid, fields, context=context)

        if 'new_quantity' in fields:
            res.update({'new_quantity': 1})
        if 'product_id' in fields:
            res.update({'product_id': product_id})
        return res

    def change_product_qty(self, cr, uid, ids, context=None):
        """ Changes the Product Quantity by making a Physical Inventory.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        @return:
        """
        if context is None:
            context = {}

        rec_id = context and context.get('active_id', False)
        assert rec_id, _('Active ID is not set in Context')

        inventry_obj = self.pool.get('stock.inventory')
        inventry_line_obj = self.pool.get('stock.inventory.line')
        prod_obj_pool = self.pool.get('product.product')

        res_original = prod_obj_pool.browse(cr, uid, rec_id, context=context)
        for data in self.browse(cr, uid, ids, context=context):
            inventory_id = inventry_obj.create(cr , uid, {'name': _('INV: %s') % tools.ustr(res_original.name)}, context=context)
            line_data ={
                'inventory_id' : inventory_id,
                'product_qty' : data.new_quantity,
                'location_id' : data.location_id.id,
                'product_id' : rec_id,
                'product_uom' : res_original.uom_id.id,
                'prod_lot_id' : data.prodlot_id.id
            }
            inventry_line_obj.create(cr , uid, line_data, context=context)

            inventry_obj.action_confirm(cr, uid, [inventory_id], context=context)
            inventry_obj.action_done(cr, uid, [inventory_id], context=context)

        return {
            'domain': "[('id','=', %s)]" % (inventory_id),
            'name' : _('Physical Inventories'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.inventory',
            'context': context,
            'type': 'ir.actions.act_window',
        }

stock_change_product_qty()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
