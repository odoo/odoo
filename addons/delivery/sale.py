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

from openerp.addons import decimal_precision
from openerp.addons.sale.sale import sale_order as OriginalSaleOrder
from openerp.osv import fields, osv
from openerp.tools.translate import _


class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'

    _columns = {
        'is_delivery': fields.boolean("Is a Delivery"),
    }

    _defaults = {
        'is_delivery': False
    }


class sale_order(osv.Model):
    _inherit = 'sale.order'

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = super(sale_order, self)._amount_all(cr, uid, ids, field_name, arg, context=context)
        Currency = self.pool.get('res.currency')
        for order in self.browse(cr, uid, ids, context=context):
            line_amount = sum([line.price_subtotal for line in order.order_line if line.is_delivery])
            currency = order.pricelist_id.currency_id
            res[order.id]['amount_delivery'] = Currency.round(cr, uid, currency, line_amount)
        return res

    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()

    _columns = {
        'carrier_id': fields.many2one(
            "delivery.carrier", string="Delivery Method",
            help="Complete this field if you plan to invoice the shipping based on picking."),
        'amount_delivery': fields.function(
            _amount_all, type='float', digits_compute=decimal_precision.get_precision('Account'), string='Delivery Amount',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The amount without tax.", track_visibility='always'
        ),
    }

    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        result = super(sale_order, self).onchange_partner_id(cr, uid, ids, part, context=context)
        if part:
            dtype = self.pool.get('res.partner').browse(cr, uid, part, context=context).property_delivery_carrier.id
            result['value']['carrier_id'] = dtype
        return result

    def _prepare_order_picking(self, cr, uid, order, context=None):
        result = super(sale_order, self)._prepare_order_picking(cr, uid, order, context=context)
        result.update(carrier_id=order.carrier_id.id)
        return result

    def _delivery_unset(self, cr, uid, order, context=None):
        for line in order.order_line:
            if line.is_delivery:
                self.pool.get('sale.order.line').unlink(cr, uid, [line.id], context=context)
        return True

    def delivery_set(self, cr, uid, ids, context=None):
        line_obj = self.pool.get('sale.order.line')
        grid_obj = self.pool.get('delivery.grid')
        carrier_obj = self.pool.get('delivery.carrier')
        acc_fp_obj = self.pool.get('account.fiscal.position')
        for order in self.browse(cr, uid, ids, context=context):
            self._delivery_unset(cr, uid, order, context=context)
        for order in self.browse(cr, uid, ids, context=context):
            grid_id = carrier_obj.grid_get(cr, uid, [order.carrier_id.id], order.partner_shipping_id.id)
            if not grid_id:
                raise osv.except_osv(_('No Grid Available!'), _('No grid matching for this carrier!'))

            if not order.state in ('draft'):
                raise osv.except_osv(_('Order not in Draft State!'), _('The order state have to be draft to add delivery lines.'))

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
                'tax_id': [(6, 0, taxes_ids)],
                'type': 'make_to_stock',
                'is_delivery': True
            })
        # remove the value of the carrier_id field on the sale order
        # TDE NOTE: why removing it ?? seems weird
        # return self.write(cr, uid, ids, {'carrier_id': False}, context=context)
