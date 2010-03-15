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
import time

class delivery_sale_order(osv.osv_memory):
    """
    Sale order Delivery.
    """
    def _delivery_default(self, cr, uid, context):
        """
        Get Default value for carrier_id field.
        """
        order_obj = self.pool.get('sale.order')
        order = order_obj.browse(cr, uid, context['active_ids'])[0]
        if not order.state in ('draft'):
            raise osv.except_osv(_('Order not in draft state !'), _('The order state have to be draft to add delivery lines.'))
        carrier_id = order.partner_id.property_delivery_carrier.id
        return carrier_id

    def delivery_set(self, cr, uid, ids, context):
        """
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of delivery set order’s IDs
        @return: dictionary {}.
        """
        for data in self.read(cr, uid, ids):
            order_obj = self.pool.get('sale.order')
            line_obj = self.pool.get('sale.order.line')
            order_objs = order_obj.browse(cr, uid, context['active_ids'], context)

            for order in order_objs:
                grid_id = self.pool.get('delivery.carrier').grid_get(cr, uid, [data['carrier_id']], order.partner_shipping_id.id)
                if not grid_id:
                    raise osv.except_osv(_('No grid avaible !'), _('No grid matching for this carrier !'))
                grid_obj = self.pool.get('delivery.grid')
                grid = grid_obj.browse(cr, uid, [grid_id])[0]

                taxes = grid.carrier_id.product_id.taxes_id
                fpos = order.fiscal_position or False
                taxes_ids = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, taxes)
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
            return {}

    _name = "delivery.sale.order"
    _description = "Delivery sale order"
    _columns = {
                'carrier_id':fields.many2one('delivery.carrier', 'Delivery Method', required=True, ondelete='cascade'),
                }
    _defaults = {
           'carrier_id':_delivery_default
        }
    
delivery_sale_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

