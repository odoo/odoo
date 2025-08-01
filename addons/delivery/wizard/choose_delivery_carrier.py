# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ChooseDeliveryCarrier(models.TransientModel):
    _name = 'choose.delivery.carrier'
    _description = 'Delivery Carrier Selection Wizard'

    def _get_default_weight_uom(self):
        return self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    order_id = fields.Many2one('sale.order', required=True, ondelete="cascade")
    partner_id = fields.Many2one('res.partner', related='order_id.partner_id', required=True)
    carrier_id = fields.Many2one(
        'delivery.carrier',
        string="Shipping Carrier",
        required=True,
        domain="[('id', 'in', available_carrier_ids)]",
    )
    is_pickup_carrier = fields.Boolean(related='carrier_id.is_pickup')
    delivery_type = fields.Selection(related='carrier_id.delivery_type')
    delivery_price = fields.Float()
    display_price = fields.Float(string='Cost', readonly=True)
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id')
    company_id = fields.Many2one('res.company', related='order_id.company_id')
    available_carrier_ids = fields.Many2many("delivery.carrier", compute='_compute_available_carrier', string="Available Carriers")
    invoicing_message = fields.Text(compute='_compute_invoicing_message')
    delivery_message = fields.Text(readonly=True)
    total_weight = fields.Float(string='Total Order Weight', related='order_id.shipping_weight', readonly=False)
    weight_uom_name = fields.Char(readonly=True, default=_get_default_weight_uom)
    partner_shipping_id = fields.Many2one('res.partner', string="Pickup Point")

    @api.onchange('carrier_id', 'total_weight')
    def _onchange_carrier_id(self):
        self.delivery_message = False
        if self.delivery_type in ('fixed', 'base_on_rule'):
            vals = self._get_delivery_rate()
            if vals.get('error_message'):
                return {'error': vals['error_message']}
        else:
            self.display_price = 0
            self.delivery_price = 0

    @api.onchange('order_id')
    def _onchange_order_id(self):
        # fixed and base_on_rule delivery price will computed on each carrier change so no need to recompute here
        if self.carrier_id and self.order_id.delivery_set and self.delivery_type not in ('fixed', 'base_on_rule'):
            vals = self._get_delivery_rate()
            if vals.get('error_message'):
                warning = {
                    'title': _("%(carrier)s Error", carrier=self.carrier_id.name),
                    'message': vals['error_message'],
                    'type': 'notification',
                }
                return {'warning': warning}

    @api.depends('carrier_id')
    def _compute_invoicing_message(self):
        self.ensure_one()
        self.invoicing_message = ""

    @api.depends('partner_id')
    def _compute_available_carrier(self):
        for rec in self:
            carriers = self.env['delivery.carrier'].search(self.env['delivery.carrier']._check_company_domain(rec.order_id.company_id))
            rec.available_carrier_ids = carriers.available_carriers(rec.order_id.partner_shipping_id, rec.order_id) if rec.partner_id else carriers

    def _get_delivery_rate(self):
        vals = self.carrier_id.with_context(order_weight=self.total_weight).rate_shipment(self.order_id)
        if vals.get('success'):
            self.delivery_message = vals.get('warning_message', False)
            self.delivery_price = vals['price']
            self.display_price = vals['carrier_price']
            return {'no_rate': vals.get('no_rate', False)}
        return {'error_message': vals['error_message']}

    def update_price(self):
        vals = self._get_delivery_rate()
        if vals.get('error_message'):
            raise UserError(vals.get('error_message'))
        return {
            'name': _('Add a shipping method'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'choose.delivery.carrier',
            'res_id': self.id,
            'target': 'new',
            'context': vals,
        }

    def button_confirm(self):
        self.ensure_one()
        if self.is_pickup_carrier and not self.partner_shipping_id:
            raise UserError(_("Please select a pickup point before adding a shipping method"))
        self.order_id.set_delivery_line(self.carrier_id, self.delivery_price)
        so_vals = {
            'partner_shipping_id': self.partner_shipping_id if self.is_pickup_carrier else self.partner_id,
            'recompute_delivery_price': False,
            'delivery_message': self.delivery_message,
        }
        self.order_id.write(so_vals)

    def set_pickup_location(self, pickup_location_data):
        self.ensure_one()
        if self.carrier_id.is_pickup:
            pickup_location_data = json.loads(pickup_location_data)
            parent_location = self.partner_shipping_id.parent_id if self.partner_shipping_id.is_pickup_location else self.partner_id
            address = self.env['res.partner']._address_from_json(pickup_location_data, parent_location)
            self.partner_shipping_id = address or self.partner_id
        # When opening a dialog from another dialog, the first one gets closed
        # We need to return an action to open the first dialog again
        action = self.order_id.action_open_delivery_wizard()
        del action['context']
        action['res_id'] = self.id
        return action
