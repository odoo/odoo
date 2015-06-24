# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from openerp import api, fields, models, _
from openerp.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_delivery = fields.Boolean(string="Is a Delivery")


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    carrier_id = fields.Many2one('delivery.carrier', string="Delivery Method",
        help="Complete this field if you plan to invoice the shipping based on picking.")

    @api.multi
    def onchange_partner_id(self, partner_id):
        result = super(SaleOrder, self).onchange_partner_id(partner_id)
        if partner_id:
            dtype = self.env['res.partner'].browse(partner_id).property_delivery_carrier.id
            if dtype:
                result['value']['carrier_id'] = dtype
        return result

    @api.multi
    def _delivery_unset(self):
        self.env['sale.order.line'].search([('order_id', 'in', self.ids), ('is_delivery', '=', True)]).unlink()

    @api.multi
    def delivery_set(self):
        OrderLine = self.env['sale.order.line']
        DeliveryGrid = self.env['delivery.grid']
        self._delivery_unset()
        ResCurrency = self.env['res.currency']
        for order in self:
            if order.state not in ('draft', 'sent'):
                raise UserError(_('The order state have to be draft to add delivery lines.'))

            Carrier = order.carrier_id
            grid_id = Carrier.grid_get(order.partner_shipping_id.id)
            if not grid_id:
                raise UserError(_('No grid matching for this carrier!'))

            grid = DeliveryGrid.browse(grid_id)
            taxes = grid.carrier_id.product_id.taxes_id
            price_unit = grid.get_price(order, time.strftime('%Y-%m-%d'))
            if order.company_id.currency_id.id != order.pricelist_id.currency_id.id:
                price_unit = ResCurrency.with_context(date=order.date_order).compute(order.company_id.currency_id.id, order.pricelist_id.currency_id.id,
                    price_unit)
            MappedTaxes = order.fiscal_position_id.map_tax(taxes)
            #create the sale order line
            OrderLine.create({
                'order_id': order.id,
                'name': grid.carrier_id.name,
                'product_uom_qty': 1,
                'product_uom': grid.carrier_id.product_id.uom_id.id,
                'product_id': grid.carrier_id.product_id.id,
                'price_unit': price_unit,
                'tax_id': [(6, 0, MappedTaxes.ids)],
                'is_delivery': True
            })
