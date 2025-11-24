import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = "choose.delivery.carrier"

    is_pickup_required = fields.Boolean(related="carrier_id.support_pickup_locations")
    partner_shipping_id = fields.Many2one("res.partner", string="Pickup Point")

    @api.onchange("carrier_id")
    def _onchange_carrier_id(self):
        # Reset the shipping partner if it is a pickup location and the delivery method changes.
        super()._onchange_carrier_id()
        partner_shipping_dm_id = self.partner_shipping_id.pickup_delivery_method_id
        if partner_shipping_dm_id and partner_shipping_dm_id != self.carrier_id:
            self.partner_shipping_id = self.partner_id

    def button_confirm(self):
        if (
            self.is_pickup_required
            and self.partner_shipping_id.pickup_delivery_method_id.id != self.carrier_id.id
        ):
            raise UserError(_("Please select a pickup point before adding a delivery method"))
        super().button_confirm()
        # Update order's shipping partner with the selected one.
        if self.is_pickup_required:
            self.order_id.partner_shipping_id = self.partner_shipping_id

    def set_pickup_location(self, pickup_location_data):
        """Set the pickup location on the current wizard.

        :param str pickup_location_data: The pickup location data in JSON format.
        """
        self.ensure_one()
        if self.is_pickup_required:
            pickup_location_data_json = json.loads(pickup_location_data)
            address = self.env["res.partner"]._address_from_json(
                pickup_location_data_json,
                self.partner_id,
                pickup_delivery_method_id=self.carrier_id.id,
            )
            self.partner_shipping_id = address or self.partner_id
