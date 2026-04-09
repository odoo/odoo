# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    website_id = fields.Many2one(
        "website",
        related="sale_id.website_id",
        string="Website",
        help="Website where this order has been placed, for eCommerce orders.",
        store=True,
        readonly=True,
    )
    is_pickup_required = fields.Boolean(related="carrier_id.support_pickup_locations")

    def write(self, vals):
        if "carrier_id" in vals:
            # Reset the partner if it is a pickup location and the delivery method changes.
            for picking in self:
                if (
                    picking.partner_id.pickup_delivery_method_id
                    and picking.partner_id.pickup_delivery_method_id.id != vals["carrier_id"]
                ):
                    picking.partner_id = picking.partner_id.parent_id
        return super().write(vals)

    def _check_pickup_location(self):
        """Check that pickings with a pickup delivery method have a matching pickup address.

        :raises UserError: if the picking is a pickup delivery and no pickup address is selected or
        the selected address belongs to another delivery method.
        """
        if any(
            picking.is_pickup_required
            and picking.partner_id.pickup_delivery_method_id.id != picking.carrier_id.id
            for picking in self
        ):
            raise UserError(_("You must select a pickup address with this delivery method."))

    def action_confirm(self):
        self._check_pickup_location()
        return super().action_confirm()

    def button_validate(self):
        self._check_pickup_location()
        return super().button_validate()

    def set_pickup_location(self, pickup_location_data):
        """Set the pickup location on the current record."""
        self.ensure_one()
        if self.is_pickup_required:
            pickup_location_data_json = json.loads(pickup_location_data)
            parent_location = (
                self.partner_id.parent_id
                if self.partner_id.pickup_delivery_method_id
                else self.partner_id
            )
            address = self.env["res.partner"]._address_from_json(
                pickup_location_data_json,
                parent_location,
                pickup_delivery_method_id=self.carrier_id.id,
            )
            self.partner_id = address or self.partner_id
