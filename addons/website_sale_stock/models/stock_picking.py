# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    website_id = fields.Many2one('website', related='sale_id.website_id', string='Website',
                                 help='Website where this order has been placed, for eCommerce orders.',
                                 store=True, readonly=True)
    is_pickup_delivery = fields.Boolean(related='carrier_id.is_pickup')

    def write(self, vals):
        """ Override to reset the partner_id if the carrier is changed from a pickup to a non-pickup one. """
        if 'carrier_id' in vals:
            new_carrier = self.env['delivery.carrier'].browse(vals['carrier_id'])
            if not new_carrier.is_pickup and any(picking.carrier_id.is_pickup for picking in self):
                pickings_with_pickup = self.filtered(lambda so: so.carrier_id.is_pickup)
                for picking in pickings_with_pickup:
                    picking.partner_id = False
        return super().write(vals)

    def action_confirm(self):
        """ Override to prevent confirming a picking with a pickup delivery method with a wrong address.

        :raises UserError: if the picking is a pickup delivery and no pickup address is selected or the selected address belongs to another delivery method.
        """
        if any(picking.is_pickup_delivery and picking.partner_id.pickup_delivery_carrier_id.id != picking.carrier_id.id for picking in self):
            raise UserError(_("You must select a pickup address with this delivery method."))
        return super().action_confirm()

    def button_validate(self):
        """ Override to prevent validating a picking with a pickup delivery method with a wrong address.

        :raises UserError: if the picking is a pickup delivery and no pickup address is selected or the selected address belongs to another delivery method.
        """
        if any(picking.is_pickup_delivery and picking.partner_id.pickup_delivery_carrier_id.id != picking.carrier_id.id for picking in self):
            raise UserError(_("You must select a pickup address with this delivery method."))
        return super().button_validate()

    def set_pickup_location(self, pickup_location_data):
        """ Set the pickup location on the current record. """
        self.ensure_one()
        if self.carrier_id.is_pickup:
            pickup_location_data_json = json.loads(pickup_location_data)
            parent_location = self.partner_id.parent_id if self.partner_id.pickup_delivery_carrier_id else self.partner_id
            address = self.env['res.partner']._address_from_json(pickup_location_data_json, parent_location, pickup_delivery_carrier_id=self.carrier_id.id)
            self.partner_id = address or self.partner_id
