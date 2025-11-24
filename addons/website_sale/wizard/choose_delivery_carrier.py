import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = 'choose.delivery.carrier'

    is_pickup_delivery = fields.Boolean(related='carrier_id.is_pickup')
    partner_shipping_id = fields.Many2one('res.partner', string="Pickup Point")

    @api.onchange('carrier_id', 'total_weight')
    def _onchange_carrier_id(self):
        super()._onchange_carrier_id()
        if self.partner_shipping_id.pickup_delivery_carrier_id and self.partner_shipping_id.pickup_delivery_carrier_id.id != self.carrier_id.id:
            self.partner_shipping_id = self.partner_id

    def _get_so_vals(self):
        vals = super()._get_so_vals()
        if self.is_pickup_delivery:
            vals.update({'partner_shipping_id': self.partner_shipping_id})
        return vals

    def button_confirm(self):
        if self.is_pickup_delivery and self.partner_shipping_id.pickup_delivery_carrier_id.id != self.carrier_id.id:
            raise UserError(_("Please select a pickup point before adding a delivery method"))
        super().button_confirm()

    def set_pickup_location(self, pickup_location_data):
        """Set the pickup location on the current wizard.

        :param str pickup_location_data: The pickup location data in JSON format.
        """
        self.ensure_one()
        if self.carrier_id.is_pickup:
            pickup_location_data_json = json.loads(pickup_location_data)
            address = self.env['res.partner']._address_from_json(
                pickup_location_data_json,
                self.partner_id,
                pickup_delivery_carrier_id=self.carrier_id.id
            )
            self.partner_shipping_id = address or self.partner_id
        # When opening a dialog from another dialog, the first one gets closed
        # We need to return an action to open the first dialog again
        action = self.order_id.action_open_delivery_wizard()
        del action['context']
        action['res_id'] = self.id
        return action
