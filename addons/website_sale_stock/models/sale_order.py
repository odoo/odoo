# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_pickup_required = fields.Boolean(related="carrier_id.support_pickup_locations")

    def _compute_warehouse_id(self):
        website_orders = self.filtered("website_id")
        super(SaleOrder, self - website_orders)._compute_warehouse_id()
        for order in website_orders:
            if order.website_id.warehouse_id:
                order.warehouse_id = order.website_id.warehouse_id
            else:
                super(SaleOrder, order)._compute_warehouse_id()
            if not order.warehouse_id:
                order.warehouse_id = self.env.user._get_default_warehouse_id()

    def write(self, vals):
        """Override to adapt pickup location-related data on delivery method change."""
        if "carrier_id" in vals:
            for order in self:
                # Reset the shipping partner if it is a pickup location.
                partner_shipping_dm_id = order.partner_shipping_id.pickup_delivery_method_id
                if partner_shipping_dm_id and partner_shipping_dm_id.id != vals["carrier_id"]:
                    order.partner_shipping_id = order.partner_id
        return super().write(vals)

    def action_open_delivery_wizard(self):
        """Override of `delivery` to include default values for pickup delivery methods."""
        res = super().action_open_delivery_wizard()
        res["context"]["default_partner_shipping_id"] = self.partner_shipping_id.id
        return res

    def set_pickup_location(self, pickup_location_data):
        """Set the pickup location on the current sale order.

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

    def _get_shop_warehouse_id(self):
        """Return the warehouse to use for shop availability checks.

        If no warehouse is specified on the website, all warehouses are considered,
        regardless of the warehouse automatically assigned to the order.

        Note: self.ensure_one()

        :returns: `stock.warehouse` id
        :rtype: int or False
        """
        self.ensure_one()
        return self.website_id.warehouse_id.id
