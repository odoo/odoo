# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    carrier_id = fields.Many2one('delivery.carrier', string="Delivery Method", help="Fill this field if you plan to invoice the shipping based on picking.")
    delivery_price = fields.Float(string='Estimated Delivery Price', readonly=True, copy=False)
    delivery_message = fields.Char(readonly=True, copy=False)
    delivery_rating_success = fields.Boolean(copy=False)
    invoice_shipping_on_delivery = fields.Boolean(string="Invoice Shipping on Delivery", copy=False)
    available_carrier_ids = fields.Many2many("delivery.carrier", compute="_compute_available_carrier", string="Available Carriers")

    def _compute_amount_total_without_delivery(self):
        self.ensure_one()
        delivery_cost = sum([l.price_total for l in self.order_line if l.is_delivery])
        return self.amount_total - delivery_cost

    @api.depends('partner_id')
    def _compute_available_carrier(self):
        carriers = self.env['delivery.carrier'].search([])
        for rec in self:
            rec.available_carrier_ids = carriers.available_carriers(rec.partner_id) if rec.partner_id else carriers

    def get_delivery_price(self):
        for order in self.filtered(lambda o: o.state in ('draft', 'sent') and len(o.order_line) > 0):
            # We do not want to recompute the shipping price of an already validated/done SO
            # or on an SO that has no lines yet
            order.delivery_rating_success = False
            res = order.carrier_id.rate_shipment(order)
            if res['success']:
                order.delivery_rating_success = True
                order.delivery_price = res['price']
                order.delivery_message = res['warning_message']
            else:
                order.delivery_rating_success = False
                order.delivery_price = 0.0
                order.delivery_message = res['error_message']

    @api.onchange('carrier_id')
    def onchange_carrier_id(self):
        if self.state in ('draft', 'sent'):
            self.delivery_price = 0.0
            self.delivery_rating_success = False
            self.delivery_message = False

    @api.onchange('partner_id')
    def onchange_partner_id_carrier_id(self):
        if self.partner_id:
            self.carrier_id = self.partner_id.property_delivery_carrier_id.filtered('active')

    # TODO onchange sol, clean delivery price

    @api.multi
    def _action_confirm(self):
        res = super(SaleOrder, self)._action_confirm()
        for so in self:
            so.invoice_shipping_on_delivery = all([not line.is_delivery for line in so.order_line])
        return res

    @api.multi
    def _remove_delivery_line(self):
        self.env['sale.order.line'].search([('order_id', 'in', self.ids), ('is_delivery', '=', True)]).unlink()

    @api.multi
    def set_delivery_line(self):

        # Remove delivery products from the sales order
        self._remove_delivery_line()

        for order in self:
            if order.state not in ('draft', 'sent'):
                raise UserError(_('You can add delivery price only on unconfirmed quotations.'))
            elif not order.carrier_id:
                raise UserError(_('No carrier set for this order.'))
            elif not order.delivery_rating_success:
                raise UserError(_('Please use "Check price" in order to compute a shipping price for this quotation.'))
            else:
                price_unit = order.carrier_id.rate_shipment(order)['price']
                # TODO check whether it is safe to use delivery_price here
                order._create_delivery_line(order.carrier_id, price_unit)
        return True

    def _create_delivery_line(self, carrier, price_unit):
        SaleOrderLine = self.env['sale.order.line']
        if self.partner_id:
            # set delivery detail in the customer language
            carrier = carrier.with_context(lang=self.partner_id.lang)

        # Apply fiscal position
        taxes = carrier.product_id.taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
        taxes_ids = taxes.ids
        if self.partner_id and self.fiscal_position_id:
            taxes_ids = self.fiscal_position_id.map_tax(taxes, carrier.product_id, self.partner_id).ids

        # Create the sales order line
        values = {
            'order_id': self.id,
            'name': carrier.with_context(lang=self.partner_id.lang).name,
            'product_uom_qty': 1,
            'product_uom': carrier.product_id.uom_id.id,
            'product_id': carrier.product_id.id,
            'price_unit': price_unit,
            'tax_id': [(6, 0, taxes_ids)],
            'is_delivery': True,
        }
        if self.order_line:
            values['sequence'] = self.order_line[-1].sequence + 1
        sol = SaleOrderLine.sudo().create(values)
        return sol

    @api.depends('state', 'order_line.invoice_status', 'order_line.invoice_lines',
                 'order_line.is_delivery', 'order_line.is_downpayment', 'order_line.product_id.invoice_policy')
    def _get_invoiced(self):
        super(SaleOrder, self)._get_invoiced()
        for order in self:
            order_line = order.order_line.filtered(lambda x: not x.is_delivery and not x.is_downpayment)
            if all(line.product_id.invoice_policy == 'delivery' and line.invoice_status == 'no' for line in order_line):
                order.update({'invoice_status': 'no'})


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_delivery = fields.Boolean(string="Is a Delivery", default=False)
    product_qty = fields.Float(compute='_compute_product_qty', string='Quantity', digits=dp.get_precision('Product Unit of Measure'))

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_product_qty(self):
        for line in self:
            if not line.product_id or not line.product_uom or not line.product_uom_qty:
                return 0.0
            line.product_qty = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)

    def _is_delivery(self):
        self.ensure_one()
        return self.is_delivery
