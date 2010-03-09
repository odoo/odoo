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

import time
import ir
from osv.osv import except_osv
from osv import fields, osv
import netsvc
from tools.translate import _

class change_production_qty(osv.osv_memory):
    _name = 'change.production.qty'
    _description = 'Change Quantity of Products'
    
    _columns = {
        'product_qty': fields.float('Product Qty', required=True),
    }

    def default_get(self, cr, uid, ids, context):
        record_id = context and context.get('record_id',False)
        res = {}
        prod_obj = self.pool.get('mrp.production')
        prod = prod_obj.browse(cr, uid, record_id)
        if prod.state in ('cancel', 'done'):
            raise osv.except_osv(_('Warning !'), _('The production is in "%s" state. You can not change the production quantity anymore') % (prod.state).upper() )
        if prod.state in ('draft'):
            return res
        if record_id:
            res['product_qty'] = prod.product_qty
        return res
    
    def change_prod_qty(self, cr, uid, ids, context):
        record_id = context and context.get('record_id',False)
        prod_obj = self.pool.get('mrp.production')
        wiz_qty = self.browse(cr, uid, ids[0])
        prod = prod_obj.browse(cr, uid,record_id)
        prod_obj.write(cr, uid,prod.id, {'product_qty': wiz_qty.product_qty})
        prod_obj.action_compute(cr, uid, [prod.id])
    
        move_lines_obj = self.pool.get('stock.move')
        for move in prod.move_lines:
            bom_point = prod.bom_id
            bom_id = prod.bom_id.id
            if not bom_point:
                bom_id = self.pool.get('mrp.bom')._bom_find(cr, uid, prod.product_id.id, prod.product_uom.id)
                if not bom_id:
                    raise osv.except_osv(_('Error'), _("Couldn't find bill of material for product"))
                prod_obj.write(cr, uid, [prod.id], {'bom_id': bom_id})
                bom_point = self.pool.get('mrp.bom').browse(cr, uid, [bom_id])[0]
    
            if not bom_id:
                raise osv.except_osv(_('Error'), _("Couldn't find bill of material for product"))
    
            factor = prod.product_qty * prod.product_uom.factor / bom_point.product_uom.factor
            res = self.pool.get('mrp.bom')._bom_explode(cr, uid, bom_point, factor / bom_point.product_qty, [])
            for r in res[0]:
                if r['product_id']== move.product_id.id:
                    move_lines_obj.write(cr, uid,move.id, {'product_qty' :  r['product_qty']})
    
        product_lines_obj = self.pool.get('mrp.production.product.line')
    
        for m in prod.move_created_ids:
            move_lines_obj.write(cr, uid,m.id, {'product_qty': wiz_qty.product_qty})
    
        return {}
    
change_production_qty()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
