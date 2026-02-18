# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = 'choose.delivery.carrier'

    is_shipper = fields.Boolean(compute='_compute_is_shipper')
    is_shipper_3pl = fields.Boolean(compute='_compute_is_shipper_3pl')
    rate_data = fields.Json("Available Rates")
    rate_line_ids = fields.One2many('shipper.rate.line', 'wizard_id', string="Rates")

    rate_id = fields.Char()

    @api.depends('carrier_id')
    def _compute_is_shipper(self):
        self.ensure_one()
        self.is_shipper = self.carrier_id.delivery_type == "shipper"

    @api.depends('carrier_id')
    def _compute_is_shipper_3pl(self):
        self.ensure_one()
        if self.carrier_id.delivery_type == "shipper":
            self.is_shipper_3pl = self.carrier_id.shipper_3pl_partner is not False
        else:
            self.is_shipper_3pl = False

    def _get_shipment_rate_shipper(self):
        vals = self.carrier_id.get_shipper_rate(self.order_id)
        self.rate_data = vals
        self.rate_line_ids.unlink()

        for rate in vals:
            self.env['shipper.rate.line'].create({
                'wizard_id': self.id,
                'carrier_name': rate['carrier_name'],
                'service': rate['service'],
                'final_price': rate['final_price'],
                'delivery_time': rate['delivery_time'],
                'rate_id': rate['rate_id'],
                'must_use_insurance': rate['must_use_insurance'],
                'insurance_fee': rate['insurance_fee'],
            })

    def update_price_shipper(self):
        self._get_shipment_rate_shipper()
        return {
            'name': _('Add a shipping method'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'choose.delivery.carrier',
            'res_id': self.id,
            'target': 'new',
        }

    def button_confirm(self):
        if self.is_shipper and not self.is_shipper_3pl:
            selected_rate = self.rate_line_ids.filtered(lambda r: r.is_selected)
            if not selected_rate:
                raise UserError(_("Please select a shipping rate to apply."))
            elif len(selected_rate) > 1:
                raise UserError(_("Only one shipping rate can be selected at a time."))
            rate = selected_rate[0]

            self.order_id.set_delivery_line(self.carrier_id, rate.final_price)
            self.order_id.write({
                'recompute_delivery_price': False,
                'delivery_message': self.delivery_message,
            })
            delivery_line = self.order_id.order_line.filtered(
                lambda line: line.is_delivery and line.product_id == self.carrier_id.product_id
            )[-1]
            if delivery_line:
                delivery_line.name = f"[{rate.rate_id}] [{rate.carrier_name}] - {self.carrier_id.name}"
        else:
            super().button_confirm()
