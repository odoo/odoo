# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import time
from osv import fields,osv
import netsvc

class sale_delivery_line(osv.osv):
    _name = 'sale.delivery.line'
    def _check_product_qty(self, cr, uid, ids):
        for delivery in self.browse(cr, uid, ids):
            cr.execute('select sum(product_uom_qty) from sale_order_line where order_id = %d and product_id = %d',(delivery.order_id,delivery.product_id))            
            sale_product_qty = cr.fetchall()[0][0]
            cr.execute('select sum(product_qty) from sale_delivery_line where order_id = %d and product_id = %d',(delivery.order_id,delivery.product_id))
            product_qty = cr.fetchall()[0][0]
            if  sale_product_qty < product_qty:
                return False
        return True
    
    def _check_products(self, cr, uid, ids):
        for delivery in self.browse(cr, uid, ids):
            cr.execute('select id from sale_order_line where order_id = %d and product_id = %d',(delivery.order_id,delivery.product_id))
            if not len(cr.fetchall()):
                return False
        return True

    _columns = {
        'product_id': fields.many2one('product.product', string='Product', required=True ),
        'product_qty': fields.float('Product Quantity', digits=(16,2), required=True),
        'product_uom' : fields.many2one('product.uom', 'Product UoM', required=True),
        'packaging_id' : fields.many2one('product.packaging', 'Packaging'),
        'date_planned': fields.datetime('Date Planned', select=True, required=True),
        'priority': fields.integer('Priority'),
        'note' : fields.text('Note'),
        'order_id': fields.many2one('sale.order', 'Order Ref', required=True, ondelete='cascade', select=True),
    }
    _constraints = [
        (_check_products,
            'You have selected a product which is not in related Sale Order',
            ['product_id']),
        (_check_product_qty,
            'The quanitties plannified in Deliveries must be equals to or less then the quantities in the Sale Order lines',
            ['product_qty'])]
    
sale_delivery_line()


class sale_order(osv.osv):
    _inherit = 'sale.order'
    _columns = {
        'delivery_line': fields.one2many('sale.delivery.line', 'order_id', 'Delivery Lines', readonly=True, states={'draft':[('readonly',False)]}),
    }
    
    def action_ship_create(self, cr, uid, ids, *args):
#        picking_id=False
        picking = {}
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        for order in self.browse(cr, uid, ids, context={}):
            output_id = order.shop_id.warehouse_id.lot_output_id.id
#            picking_id = False
#            if not order.delivery_line:
#                return super(sale_order, self).action_ship_create(cr, uid, ids)
            for line in order.delivery_line:
                cr.execute('select id from sale_order_line where order_id = %d and product_id = %d',(ids[0],line.product_id.id))
                sale_line_id = cr.fetchall()[0][0]
                sale_line = self.pool.get('sale.order.line').browse(cr, uid, sale_line_id)
                proc_id=False
                date_planned = line.date_planned
#                date_planned = (date_planned - DateTime.RelativeDateTime(days=company.security_lead)).strftime('%Y-%m-%d %H:%M:%S')
#                if line.state == 'done':
#                    continue
                if line.product_id and line.product_id.product_tmpl_id.type in ('product', 'consu'):
                    location_id = order.shop_id.warehouse_id.lot_stock_id.id
#                    if not picking_id:
                    if not date_planned in picking:
                        loc_dest_id = order.partner_id.property_stock_customer.id
                        picking_id = self.pool.get('stock.picking').create(cr, uid, {
                            'origin': order.name,
                            'type': 'out',
                            'state': 'confirmed',
                            'move_type': order.picking_policy,
                            'sale_id': order.id,
                            'address_id': order.partner_shipping_id.id,
                            'note': order.note,
                            'invoice_state': (order.order_policy=='picking' and '2binvoiced') or 'none',
                        })
                        picking[date_planned] = picking_id
                    
                    else:
                        picking_id = picking[date_planned]
                        
                    move_id = self.pool.get('stock.move').create(cr, uid, {
                        'name': line.product_id.name[:64],
                        'picking_id': picking_id,
                        'product_id': line.product_id.id,
                        'date_planned': date_planned,
                        'product_qty': line.product_qty,
                        'product_uom': line.product_uom.id,
                        'product_uos_qty': line.product_qty,
                        'product_uos': line.product_uom.id,
                        'product_packaging' : line.packaging_id.id,
                        'address_id' : order.partner_shipping_id.id,
                        'location_id': location_id,
                        'location_dest_id': output_id,
                        'tracking_id': False,
                        'state': 'waiting',
                        'note': line.note,
                    })
                    proc_id = self.pool.get('mrp.procurement').create(cr, uid, {
                        'name': order.name,
                        'origin': order.name,
                        'date_planned': date_planned,
                        'product_id': line.product_id.id,
                        'product_qty': line.product_qty,
                        'product_uom': line.product_uom.id,
                        'product_uos_qty': line.product_qty,
                        'product_uos': line.product_uom.id,
                        'location_id': order.shop_id.warehouse_id.lot_stock_id.id,
                        'procure_method': sale_line.type,
                        'move_id': move_id,
                        'property_ids': [(6, 0, [x.id for x in sale_line.property_ids])],
                    })
                    wf_service = netsvc.LocalService("workflow")
                    wf_service.trg_validate(uid, 'mrp.procurement', proc_id, 'button_confirm', cr)
#                    self.pool.get('sale.order.line').write(cr, uid, [line.id], {'procurement_id': proc_id})
                elif line.product_id and line.product_id.product_tmpl_id.type=='service':
                    proc_id = self.pool.get('mrp.procurement').create(cr, uid, {
                        'name': line.name,
                        'origin': order.name,
                        'date_planned': date_planned,
                        'product_id': line.product_id.id,
                        'product_qty': line.product_uom_qty,
                        'product_uom': line.product_uom.id,
                        'location_id': order.shop_id.warehouse_id.lot_stock_id.id,
                        'procure_method': line.type,
                        'property_ids': [(6, 0, [x.id for x in line.property_ids])],
                    })
                    wf_service = netsvc.LocalService("workflow")
                    wf_service.trg_validate(uid, 'mrp.procurement', proc_id, 'button_confirm', cr)
#                    self.pool.get('sale.order.line').write(cr, uid, [line.id], {'procurement_id': proc_id})
                else:
                    #
                    # No procurement because no product in the sale.order.line.
                    #
                    pass
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_validate(uid, 'stock.picking', picking['date_planned'], 'button_confirm', cr)

            val = {}
#            if 'date_planned' in picking and picking['date_planned']:
#                print 
                
            if order.state=='shipping_except':
                val['state'] = 'progress'
                if (order.order_policy == 'manual') and order.invoice_ids:
                    val['state'] = 'manual'
            self.write(cr, uid, [order.id], val)

        return True
sale_order()

class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'
    
    def _get_planned_deliveries(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for val in self.browse(cr, uid, ids):
            cr.execute('select sum(product_qty) from sale_delivery_line where order_id = %d and product_id = %d',(val.order_id,val.product_id))
            product_qty = cr.fetchall()[0][0]
            res[val.id] = product_qty
        return res
    
    _columns = {
         'deliveries': fields.function(_get_planned_deliveries, method=True, string='Planned Deliveries'),
    }
    
sale_order_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
