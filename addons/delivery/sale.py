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
from osv import fields,osv
from tools.translate import _

# Overloaded sale_order to manage carriers :
class sale_order(osv.osv):
    _inherit = 'sale.order'
    _columns = {
        'carrier_id':fields.many2one("delivery.carrier", "Delivery Method", help="Complete this field if you plan to invoice the shipping based on picking."),
        'id': fields.integer('ID', readonly=True,invisible=True),
    }

    def onchange_partner_id(self, cr, uid, ids, part):
        result = super(sale_order, self).onchange_partner_id(cr, uid, ids, part)
        if part:
            dtype = self.pool.get('res.partner').browse(cr, uid, part).property_delivery_carrier.id
            result['value']['carrier_id'] = dtype
        return result

    def _prepare_order_picking(self, cr, uid, order, context=None):
        result = super(sale_order, self)._prepare_order_picking(cr, uid, order, context=context)
        result.update(carrier_id=order.carrier_id.id)
        return result

    def delivery_set(self, cr, uid, ids, context=None):
        order_obj = self.pool.get('sale.order')
        line_obj = self.pool.get('sale.order.line')
        grid_obj = self.pool.get('delivery.grid')
        carrier_obj = self.pool.get('delivery.carrier')
        acc_fp_obj = self.pool.get('account.fiscal.position')
        for order in self.browse(cr, uid, ids, context=context):
            grid_id = carrier_obj.grid_get(cr, uid, [order.carrier_id.id], order.partner_shipping_id.id)
            if not grid_id:
                raise osv.except_osv(_('No grid available !'), _('No grid matching for this carrier !'))

            if not order.state in ('draft'):
                raise osv.except_osv(_('Order not in draft state !'), _('The order state have to be draft to add delivery lines.'))

            grid = grid_obj.browse(cr, uid, grid_id, context=context)

            taxes = grid.carrier_id.product_id.taxes_id
            fpos = order.fiscal_position or False
            taxes_ids = acc_fp_obj.map_tax(cr, uid, fpos, taxes)
            #create the sale order line
            line_obj.create(cr, uid, {
                'order_id': order.id,
                'name': grid.carrier_id.name,
                'product_uom_qty': 1,
                'product_uom': grid.carrier_id.product_id.uom_id.id,
                'product_id': grid.carrier_id.product_id.id,
                'price_unit': grid_obj.get_price(cr, uid, grid.id, order, time.strftime('%Y-%m-%d'), context),
                'tax_id': [(6,0,taxes_ids)],
                'type': 'make_to_stock'
            })
        #remove the value of the carrier_id field on the sale order
        return self.write(cr, uid, ids, {'carrier_id': False}, context=context)
        #return {'type': 'ir.actions.act_window_close'} action reload?

sale_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

