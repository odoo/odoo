# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    carrier_id = fields.Many2one('delivery.carrier', string="Delivery Method", help="Fill this field if you plan to invoice the shipping based on picking.")
    delivery_message = fields.Char(readonly=True, copy=False)
    delivery_rating_success = fields.Boolean(copy=False)
    delivery_set = fields.Boolean(compute='_compute_delivery_state')
    recompute_delivery_price = fields.Boolean('Delivery cost should be recomputed')
    is_all_service = fields.Boolean("Service Product", compute="_compute_is_service_products")

    @api.depends('order_line')
    def _compute_is_service_products(self):
        for so in self:
            so.is_all_service = all(line.product_id.type == 'service' for line in so.order_line)

    def _compute_amount_total_without_delivery(self):
        self.ensure_one()
        delivery_cost = sum([l.price_total for l in self.order_line if l.is_delivery])
        return self.amount_total - delivery_cost

    @api.depends('order_line')
    def _compute_delivery_state(self):
        delivery_line = self.order_line.filtered('is_delivery')
        if delivery_line:
            self.delivery_set = True

    @api.onchange('order_line', 'partner_id')
    def onchange_order_line(self):
        delivery_line = self.order_line.filtered('is_delivery')
        if delivery_line:
            self.recompute_delivery_price = True

    def _remove_delivery_line(self):
        self.env['sale.order.line'].search([('order_id', 'in', self.ids), ('is_delivery', '=', True)]).unlink()

    def set_delivery_line(self, carrier, amount):

        # Remove delivery products from the sales order
        self._remove_delivery_line()

        for order in self:
            order._create_delivery_line(carrier, amount, price_unit_in_description=self.carrier_id.invoice_policy == 'real')
        return True

    def action_open_delivery_wizard(self):
        view_id = self.env.ref('delivery.choose_delivery_carrier_view_form').id
        return {
            'name': _('Add a shipping method'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'choose.delivery.carrier',
            'view_id': view_id,
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_carrier_id': self.partner_id.property_delivery_carrier_id.id,
            }
        }

    def recompute_delivery_cost(self):
        self.ensure_one()
        delivery_line = self.order_line.filtered('is_delivery')[:1]
        res = self.carrier_id.rate_shipment(self)
        if res.get('success'):
            self.delivery_message = res.get('warning_message', False)
        else:
            raise UserError(res['error_message'])
        delivery_line.name = self.carrier_id.with_context(lang=self.partner_id.lang).name
        if self.carrier_id.invoice_policy == 'real':
            delivery_line.name += _(' (Estimated Cost: %s )') % self._format_currency_amount(res['price'])
        else:
            delivery_line.price_unit = res['price']
        if self.carrier_id.free_over and self._compute_amount_total_without_delivery() >= res['price']:
            delivery_line.name += '\nFree Shipping'
        self.recompute_delivery_price = False

    def _create_delivery_line(self, carrier, price_unit, price_unit_in_description=False):
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
        carrier_with_partner_lang = carrier.with_context(lang=self.partner_id.lang)
        if carrier_with_partner_lang.product_id.description_sale:
            so_description = '%s: %s' % (carrier_with_partner_lang.name,
                                        carrier_with_partner_lang.product_id.description_sale)
        else:
            so_description = carrier_with_partner_lang.name
        values = {
            'order_id': self.id,
            'name': so_description,
            'product_uom_qty': 1,
            'product_uom': carrier.product_id.uom_id.id,
            'product_id': carrier.product_id.id,
            'tax_id': [(6, 0, taxes_ids)],
            'is_delivery': True,
        }
        if price_unit_in_description:
            values['price_unit'] = 0
            values['name'] += _(' (Estimated Cost: %s )') % self._format_currency_amount(price_unit)
        else:
            values['price_unit'] = price_unit
        if carrier.free_over and self._compute_amount_total_without_delivery() >= price_unit:
            values['name'] += '\n' + 'Free Shipping'
        if self.order_line:
            values['sequence'] = self.order_line[-1].sequence + 1
        sol = SaleOrderLine.sudo().create(values)
        return sol

    def _format_currency_amount(self, amount):
        pre = post = u''
        if self.currency_id.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'.format(symbol=self.currency_id.symbol or '')
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'.format(symbol=self.currency_id.symbol or '')
        return u' {pre}{0}{post}'.format(amount, pre=pre, post=post)

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
    product_qty = fields.Float(compute='_compute_product_qty', string='Product Qty', digits='Product Unit of Measure')
    recompute_delivery_price = fields.Boolean(related='order_id.recompute_delivery_price')

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_product_qty(self):
        for line in self:
            if not line.product_id or not line.product_uom or not line.product_uom_qty:
                return 0.0
            line.product_qty = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)

    def unlink(self):
        for line in self:
            if line.is_delivery:
                line.order_id.carrier_id = False
        super(SaleOrderLine, self).unlink()

    def _is_delivery(self):
        self.ensure_one()
        return self.is_delivery
