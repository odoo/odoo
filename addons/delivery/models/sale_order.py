# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields, api, _
from openerp.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_price = fields.Float(string='Estimated Delivery Price', compute='_compute_delivery_price', store=True)
    carrier_id = fields.Many2one("delivery.carrier", string="Delivery Method", help="Fill this field if you plan to invoice the shipping based on picking.")
    invoice_shipping_on_delivery = fields.Boolean(string="Invoice Shipping on Delivery")

    @api.depends('carrier_id', 'partner_id', 'order_line')
    def _compute_delivery_price(self):
        for order in self:
            if order.state != 'draft':
                # We do not want to recompute the shipping price of an already validated/done SO
                continue
            elif order.carrier_id.delivery_type != 'grid' and not order.order_line:
                # Prevent SOAP call to external shipping provider when SO has no lines yet
                continue
            else:
                order.delivery_price = order.carrier_id.with_context(order_id=order.id).price

    @api.onchange('partner_id')
    def onchange_partner_id_dtype(self):
        if self.partner_id:
            self.carrier_id = self.partner_id.property_delivery_carrier_id

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for so in self:
            self.invoice_shipping_on_delivery = all([not line.is_delivery for line in so.order_line])
        return res

    @api.multi
    def _delivery_unset(self):
        self.env['sale.order.line'].search([('order_id', 'in', self.ids), ('is_delivery', '=', True)]).unlink()

    @api.multi
    def delivery_set(self):

        # Remove delivery products from the sale order
        self._delivery_unset()

        for order in self:
            carrier = order.carrier_id
            if carrier:
                if order.state not in ('draft', 'sent'):
                    raise UserError(_('The order state have to be draft to add delivery lines.'))

                if carrier.delivery_type not in ['fixed', 'base_on_rule']:
                    # Shipping providers are used when delivery_type is other than 'fixed' or 'base_on_rule'
                    price_unit = order.carrier_id.get_shipping_price_from_so(order)[0]
                else:
                    # Classic grid-based carriers
                    carrier = order.carrier_id.verify_carrier(order.partner_shipping_id)
                    if not carrier:
                        raise UserError(_('No carrier matching.'))
                    price_unit = carrier.get_price_available(order)
                    if order.company_id.currency_id.id != order.pricelist_id.currency_id.id:
                        price_unit = order.company_id.currency_id.with_context(date=order.date_order).compute(price_unit, order.pricelist_id.currency_id)

                order._create_delivery_line(carrier, price_unit)

            else:
                raise UserError(_('No carrier set for this order.'))

    def _create_delivery_line(self, carrier, price_unit):
        SaleOrderLine = self.env['sale.order.line']

        # Apply fiscal position
        taxes = carrier.product_id.taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
        taxes_ids = taxes.ids
        if self.partner_id and self.fiscal_position_id:
            taxes_ids = self.fiscal_position_id.map_tax(taxes).ids

        # Create the sale order line
        values = {
            'order_id': self.id,
            'name': carrier.name,
            'product_uom_qty': 1,
            'product_uom': carrier.product_id.uom_id.id,
            'product_id': carrier.product_id.id,
            'price_unit': price_unit,
            'tax_id': [(6, 0, taxes_ids)],
            'is_delivery': True,
        }
        if self.order_line:
            values['sequence'] = self.order_line[-1].sequence + 1
        SaleOrderLine.create(values)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_delivery = fields.Boolean(string="Is a Delivery", default=False)
