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
from openerp.osv import fields, osv
from openerp.tools.translate import _


class sale_order_line(osv.Model):
    _inherit = 'sale.order.line'

    _columns = {
        'is_delivery': fields.boolean("Is a Delivery"),
    }

    _defaults = {
        'is_delivery': False
    }


class sale_order(osv.Model):
    _inherit = 'sale.order'
    _columns = {
        'carrier_id': fields.many2one(
            "delivery.carrier", string="Delivery Method",
            help="Complete this field if you plan to invoice the shipping based on picking."),
    }

    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        result = super(sale_order, self).onchange_partner_id(cr, uid, ids, part, context=context)
        if part:
            dtype = self.pool.get('res.partner').browse(cr, uid, part, context=context).property_delivery_carrier.id
            # TDE NOTE: not sure the aded 'if dtype' is valid
            if dtype:
                result['value']['carrier_id'] = dtype
        return result


    def _delivery_unset(self, cr, uid, ids, context=None):
        sale_obj = self.pool['sale.order.line']
        line_ids = sale_obj.search(cr, uid, [('order_id', 'in', ids), ('is_delivery', '=', True)],context=context)
        sale_obj.unlink(cr, uid, line_ids, context=context)

    def delivery_set(self, cr, uid, ids, context=None):
        line_obj = self.pool.get('sale.order.line')
        grid_obj = self.pool.get('delivery.grid')
        carrier_obj = self.pool.get('delivery.carrier')
        acc_fp_obj = self.pool.get('account.fiscal.position')
        self._delivery_unset(cr, uid, ids, context=context)
        currency_obj = self.pool.get('res.currency')
        line_ids = []
        for order in self.browse(cr, uid, ids, context=context):
            grid_id = carrier_obj.grid_get(cr, uid, [order.carrier_id.id], order.partner_shipping_id.id)
            if not grid_id:
                raise osv.except_osv(_('No Grid Available!'), _('No grid matching for this carrier!'))

            if order.state not in ('draft', 'sent'):
                raise osv.except_osv(_('Order not in Draft State!'), _('The order state have to be draft to add delivery lines.'))

            grid = grid_obj.browse(cr, uid, grid_id, context=context)

            taxes = grid.carrier_id.product_id.taxes_id
            fpos = order.fiscal_position or False
            taxes_ids = acc_fp_obj.map_tax(cr, uid, fpos, taxes)
            price_unit = grid_obj.get_price(cr, uid, grid.id, order, time.strftime('%Y-%m-%d'), context)
            if order.company_id.currency_id.id != order.pricelist_id.currency_id.id:
                price_unit = currency_obj.compute(cr, uid, order.company_id.currency_id.id, order.pricelist_id.currency_id.id,
                    price_unit, context=dict(context or {}, date=order.date_order))
            #create the sale order line
            line_id = line_obj.create(cr, uid, {
                'order_id': order.id,
                'name': grid.carrier_id.name,
                'product_uom_qty': 1,
                'product_uom': grid.carrier_id.product_id.uom_id.id,
                'product_id': grid.carrier_id.product_id.id,
                'price_unit': price_unit,
                'tax_id': [(6, 0, taxes_ids)],
                'is_delivery': True
            }, context=context)
            line_ids.append(line_id)
        return line_ids
