# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ChooseDeliveryCarrier(models.TransientModel):
    _name = 'choose.delivery.carrier'
    _description = 'Delivery Carrier Selection Wizard'

    order_id = fields.Many2one('sale.order', required=True, ondelete="cascade")
    partner_id = fields.Many2one('res.partner', related='order_id.partner_id', required=True)
    carrier_id = fields.Many2one(
        'delivery.carrier',
        string="Shipping Method",
        help="Choose the method to deliver your goods",
        required=True,
    )
    delivery_type = fields.Selection(related='carrier_id.delivery_type')
    delivery_price = fields.Float()
    display_price = fields.Float(string='Cost', readonly=True)
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id')
    available_carrier_ids = fields.Many2many("delivery.carrier", compute='_compute_available_carrier', string="Available Carriers")
    invoicing_message = fields.Text(compute='_compute_invoicing_message')
    delivery_message = fields.Text(readonly=True)

    @api.onchange('carrier_id')
    def _onchange_carrier_id(self):
        self.delivery_message = False
        if self.delivery_type in ('fixed', 'base_on_rule'):
            vals = self.carrier_id.rate_shipment(self.order_id)
            if vals.get('success'):
                if vals.get('warning_message'):
                    self.delivery_message = vals['warning_message']
                self.delivery_price = vals['price']
                self.display_price = vals['carrier_price']
            else:
                return {'error': vals['error_message']}
        else:
            self.display_price = 0
            self.delivery_price = 0

    @api.depends('carrier_id')
    def _compute_invoicing_message(self):
        self.ensure_one()
        if self.carrier_id.invoice_policy == 'real':
            self.invoicing_message = _('The shipping price will be set once the delivery is done.')
        else:
            self.invoicing_message = ""

    @api.depends('partner_id')
    def _compute_available_carrier(self):
        carriers = self.env['delivery.carrier'].search([])
        for rec in self:
            rec.available_carrier_ids = carriers.available_carriers(rec.partner_id) if rec.partner_id else carriers

    def update_price(self):
        vals = self.carrier_id.rate_shipment(self.order_id)
        if vals.get('success'):
            if vals['warning_message']:
                self.delivery_message = vals['warning_message']
            self.delivery_price = vals['price']
            self.display_price = vals['carrier_price']
        else:
            raise UserError(vals['error_message'])
        return {
            'name': _('Add a shipping method'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'choose.delivery.carrier',
            'res_id': self.id,
            'target': 'new',
        }

    def button_confirm(self):
        if self.carrier_id.deliver_over and self.order_id._compute_amount_total_without_delivery() < self.carrier_id.minimum_amount:
            raise UserError(_('The amount of the SO is below the minimum allowed with this delivery method. The minimum amount should be %s. Please choose another delivery method.') % self.carrier_id.minimum_amount)
        self.order_id.carrier_id = self.carrier_id
        self.order_id.delivery_message = self.delivery_message
        self.order_id.set_delivery_line(self.carrier_id, self.delivery_price)
