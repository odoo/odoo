# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from openerp import models, fields, api, _
from openerp.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_price = fields.Float(string='Estimated Delivery Price', compute='_compute_delivery_price')
    carrier_id = fields.Many2one('delivery.carrier', string="Delivery Method", help="Complete this field if you plan to invoice the shipping based on picking.")

    @api.depends('carrier_id', 'partner_id', 'order_line')
    def _compute_delivery_price(self):
        for order in self:
            order.delivery_price = order.carrier_id.with_context(order_id=order.id).price

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

        SaleOrderLine = self.env['sale.order.line']

        # Remove delivery products from the sale order
        self._delivery_unset()

        for order in self:
            # Shipping providers are used when delivery_type is other than 'grid'

            if order.state not in ('draft', 'sent'):
                raise UserError(_('The order state have to be draft to add delivery lines.'))

            carrier = order.carrier_id
            if order.carrier_id and order.carrier_id.delivery_type != 'grid':
                account_id = carrier.product_id.property_account_income.id
                if not account_id:
                    account_id = carrier.product_id.categ_id.property_account_income_categ.id

                # Apply fiscal position
                taxes = carrier.product_id.taxes_id
                taxes_ids = taxes.ids
                if order.partner_id and order.fiscal_position_id:
                    account_id = order.fiscal_position_id.map_account(account_id)
                    taxes_ids = order.fiscal_position_id.map_tax(taxes).ids

                SaleOrderLine.create({
                    'order_id': order.id,
                    'name': order.carrier_id.name,
                    'product_uom_qty': 1,
                    'product_uom': order.carrier_id.product_id.uom_id.id,
                    'product_id': order.carrier_id.product_id.id,
                    'price_unit': order.carrier_id.get_shipping_price_from_so(order)[0],
                    'tax_id': [(6, 0, taxes_ids)],
                    'is_delivery': True
                })

            else:
                # Classic grid-based carriers
                grid_id = carrier.grid_get(order.partner_shipping_id.id)
                if not grid_id:
                    raise UserError(_('No grid matching for this carrier!'))

                grid = self.env['delivery.grid'].browse(grid_id)
                taxes = grid.carrier_id.product_id.taxes_id
                price_unit = grid.get_price(order, time.strftime('%Y-%m-%d'))
                if order.company_id.currency_id.id != order.pricelist_id.currency_id.id:
                    price_unit = self.env['res.currency'].with_context(date=order.date_order).compute(order.company_id.currency_id.id, order.pricelist_id.currency_id.id,
                    price_unit)
                MappedTaxes = order.fiscal_position_id.map_tax(taxes)
                #create the sale order line
                SaleOrderLine.create({
                    'order_id': order.id,
                    'name': grid.carrier_id.name,
                    'product_uom_qty': 1,
                    'product_uom': grid.carrier_id.product_id.uom_id.id,
                    'product_id': grid.carrier_id.product_id.id,
                    'price_unit': price_unit,
                    'tax_id': [(6, 0, MappedTaxes.ids)],
                    'is_delivery': True
                })


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_delivery = fields.Boolean(string="Is a Delivery")
