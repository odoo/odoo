# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from openerp.osv import osv
from openerp.exceptions import UserError
from openerp.tools.translate import _


class sale_order(osv.Model):
    _inherit = 'sale.order'

    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        result = super(sale_order, self).onchange_partner_id(cr, uid, ids, part, context=context)
        if part:
            dtype = self.pool.get('res.partner').browse(cr, uid, part, context=context).property_delivery_carrier.id
            # TDE NOTE: not sure the aded 'if dtype' is valid
            if dtype:
                result['value']['carrier_id'] = dtype
        return result

    def delivery_set(self, cr, uid, ids, context=None):
        line_obj = self.pool.get('sale.order.line')
        grid_obj = self.pool.get('delivery.grid')
        carrier_obj = self.pool.get('delivery.carrier')
        acc_fp_obj = self.pool.get('account.fiscal.position')
        self._delivery_unset(cr, uid, ids, context=context)
        currency_obj = self.pool.get('res.currency')
        for order in self.browse(cr, uid, ids, context=context):
            grid = carrier_obj.grid_get(cr, uid, [order.carrier_id.id], order.partner_shipping_id)
            if not grid:
                raise UserError(_('No grid matching for this carrier!'))

            if order.state not in ('draft', 'sent'):
                raise UserError(_('The order state have to be draft to add delivery lines.'))

            taxes = grid.carrier_id.product_id.taxes_id
            fpos = order.fiscal_position or False
            taxes_ids = acc_fp_obj.map_tax(cr, uid, fpos, taxes)
            price_unit = grid_obj.get_price(cr, uid, grid.id, order, time.strftime('%Y-%m-%d'), context)
            if order.company_id.currency_id.id != order.pricelist_id.currency_id.id:
                price_unit = currency_obj.compute(cr, uid, order.company_id.currency_id.id, order.pricelist_id.currency_id.id,
                    price_unit, context=dict(context or {}, date=order.date_order))
            # create the sale order line
            line_obj.create(cr, uid, {
                'order_id': order.id,
                'name': grid.carrier_id.name,
                'product_uom_qty': 1,
                'product_uom': grid.carrier_id.product_id.uom_id.id,
                'product_id': grid.carrier_id.product_id.id,
                'price_unit': price_unit,
                'tax_id': [(6, 0, taxes_ids)],
                'is_delivery': True
            }, context=context)
