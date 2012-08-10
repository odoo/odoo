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

import netsvc

from osv import fields, osv

class make_procurement(osv.osv_memory):
    _name = 'make.procurement'
    _description = 'Make Procurements'
    
    _columns = {
        'qty': fields.float('Quantity', digits=(16,2), required=True),
        'product_id': fields.many2one('product.product', 'Product', required=True, readonly=1),
        'uom_id': fields.many2one('product.uom', 'Unit of Measure', required=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True),
        'date_planned': fields.date('Planned Date', required=True),
    }

    _defaults = {
        'date_planned': fields.date.context_today,
        'qty': lambda *args: 1.0,
    }

    def make_procurement(self, cr, uid, ids, context=None):
        """ Creates procurement order for selected product.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        @return: A dictionary which loads Procurement form view.
        """
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context).login
        wh_obj = self.pool.get('stock.warehouse')
        procurement_obj = self.pool.get('procurement.order')
        wf_service = netsvc.LocalService("workflow")
        data_obj = self.pool.get('ir.model.data')

        for proc in self.browse(cr, uid, ids, context=context):
            wh = wh_obj.browse(cr, uid, proc.warehouse_id.id, context=context)
            procure_id = procurement_obj.create(cr, uid, {
                'name':'INT: '+str(user),
                'date_planned': proc.date_planned,
                'product_id': proc.product_id.id,
                'product_qty': proc.qty,
                'product_uom': proc.uom_id.id,
                'location_id': wh.lot_stock_id.id,
                'procure_method':'make_to_order',
            })

            wf_service.trg_validate(uid, 'procurement.order', procure_id, 'button_confirm', cr)


        id2 = data_obj._get_id(cr, uid, 'procurement', 'procurement_tree_view')
        id3 = data_obj._get_id(cr, uid, 'procurement', 'procurement_form_view')

        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        if id3:
            id3 = data_obj.browse(cr, uid, id3, context=context).res_id

        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'procurement.order',
            'res_id' : procure_id,
            'views': [(id3,'form'),(id2,'tree')],
            'type': 'ir.actions.act_window',
         }

    def default_get(self, cr, uid, fields, context=None):
        """ To get default values for the object.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for which we want default values
        @param context: A standard dictionary
        @return: A dictionary which of fields with values.
        """
        if context is None:
            context = {}
        record_id = context and context.get('active_id', False) or False

        res = super(make_procurement, self).default_get(cr, uid, fields, context=context)
        warehouse_id = self.pool.get('stock.warehouse').search(cr, uid, [], context=context)
        product_uom_id = self.pool.get('product.product').browse(cr, uid, record_id, context=context).uom_id.id
        warehouse_id = warehouse_id and warehouse_id[0] or False
        res.update({'uom_id':product_uom_id, 'warehouse_id': warehouse_id})
        return res

make_procurement()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

