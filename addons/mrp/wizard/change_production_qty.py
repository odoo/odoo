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

class change_production_qty(osv.osv_memory):
    _name = 'change.production.qty'
    _description = 'Change Quantity of Products'
    
    _columns = {
        'product_qty': fields.float('Product Qty', required=True),
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
        res = super(change_production_qty, self).default_get(cr, uid, fields, context=context)        
        prod_obj = self.pool.get('mrp.production')
        prod = prod_obj.browse(cr, uid, context.get('active_id'), context=context)
        if 'product_qty' in fields:
            res.update({'product_qty': prod.product_qty})  
        return res
        
    def change_prod_qty(self, cr, uid, ids, context=None):
        """ 
        Changes the Quantity of Product.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected 
        @param context: A standard dictionary 
        @return:  
        """
        record_id = context and context.get('active_id',False)
        assert record_id, _('Active Id is not found')
        prod_obj = self.pool.get('mrp.production')
        bom_obj = self.pool.get('mrp.bom')
        for wiz_qty in self.browse(cr, uid, ids, context=context):
            prod = prod_obj.browse(cr, uid, record_id, context=context)
            prod_obj.write(cr, uid,prod.id, {'product_qty': wiz_qty.product_qty})
            prod_obj.action_compute(cr, uid, [prod.id])
            move_lines = prod.move_lines
            move_lines.extend(prod.picking_id.move_lines)

            move_lines_obj = self.pool.get('stock.move')
            for move in move_lines:
                bom_point = prod.bom_id
                bom_id = prod.bom_id.id
                if not bom_point:
                    bom_id = bom_obj._bom_find(cr, uid, prod.product_id.id, prod.product_uom.id)
                    if not bom_id:
                        raise osv.except_osv(_('Error'), _("Couldn't find bill of material for product"))
                    prod_obj.write(cr, uid, [prod.id], {'bom_id': bom_id})
                    bom_point = bom_obj.browse(cr, uid, [bom_id])[0]
        
                if not bom_id:
                    raise osv.except_osv(_('Error'), _("Couldn't find bill of material for product"))
        
                factor = prod.product_qty * prod.product_uom.factor / bom_point.product_uom.factor
                res = bom_obj._bom_explode(cr, uid, bom_point, factor / bom_point.product_qty, [])
                for r in res[0]:
                    if r['product_id'] == move.product_id.id:
                        move_lines_obj.write(cr, uid, [move.id], {'product_qty' :  r['product_qty']})
            for m in prod.move_created_ids:
                move_lines_obj.write(cr, uid, [m.id], {'product_qty': wiz_qty.product_qty})
    
        return {}
    
change_production_qty()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
