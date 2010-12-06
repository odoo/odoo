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
import decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time

class stock_change_product_qty(osv.osv_memory):
    _name = "stock.change.product.qty"
    _description = "Change Product Quantity"
    _columns = {
        'new_quantity': fields.float('Quantity', required=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True, ondelete="cascade"),
        'location_id': fields.many2one('stock.location', 'Location', required=True, ondelete="cascade"),
    }

    _defaults = {
        'warehouse_id': 1 or False,
    }


    def onchange_warehouse_id(self, cr, uid, ids, warehouse_id, context={}):
        """ Finds location id for changed warehouse.
        @param warehouse_id: Changed id of warehouse.
        @return: Dictionary of values.
        """
        if warehouse_id:
            w = self.pool.get('stock.warehouse').browse(cr, uid, warehouse_id, context)
            v = {'location_id': w.lot_stock_id.id}
            return {'value': v}
        return {}

    def default_get(self, cr, uid, fields, context):
        """ To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values
         @param context: A standard dictionary
         @return: A dictionary which of fields with values.
        """
        product_pool = self.pool.get('product.product')
        product_obj = product_pool.browse(cr, uid, context.get('active_id', False))
        res = super(stock_change_product_qty, self).default_get(cr, uid, fields, context=context)

        if 'new_quantity' in fields:
            res.update({'new_quantity': product_obj.qty_available})
        return res

    def change_product_qty(self, cr, uid, ids, context):
        """ Changes the Standard Price of Product.
            And creates an account move accordingly.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        @return:
        """
        move_ids = []
        rec_id = context and context.get('active_id', False)
        assert rec_id, _('Active ID is not set in Context')

        inventry_obj_pool = self.pool.get('stock.inventory')
        inventry_line_obj_pool = self.pool.get('stock.inventory.line')
        prod_obj_pool = self.pool.get('product.product')
        move_obj_pool = self.pool.get('stock.move')

        res_original = prod_obj_pool.browse(cr, uid, rec_id)
        res_update = self.browse(cr, uid, ids)

        datas = {
            'name': 'INV:' + str(res_original.name),
            'company_id' : self.pool.get('res.users').browse(cr, uid, uid).company_id.id or False ,
            'date': time.strftime('%Y-%m-%d %H:%M:%S'),
        }

        invntry_id = inventry_obj_pool.create(cr , uid, datas, context = context)

        line_data ={
            'inventory_id' : invntry_id,
            'product_qty' : res_update[0].new_quantity,
            'location_id' : res_update[0].location_id.id,
            'product_id' : rec_id,
            'product_uom' : res_original.uom_id.id,
            'company_id' : self.pool.get('res.users').browse(cr, uid, uid).company_id.id or False ,
            'state' : 'draft'
        }
        line_id = inventry_line_obj_pool.create(cr , uid, line_data, context = context)

        inventry_obj_pool.action_confirm(cr, uid, [invntry_id], context = context)
        inventry_obj_pool.action_done(cr, uid, [invntry_id], context = context)
        return {}
stock_change_product_qty()
