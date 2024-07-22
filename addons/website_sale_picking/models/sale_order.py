# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _set_pickup_location(self, pickup_location_data):
        """ Set the pickup location on the current order.

        Note: self.ensure_one()

        :param str pickup_location_data: The JSON-formatted pickup location address.
        :return: None
        """
        self.ensure_one()
        if self.carrier_id.delivery_type != 'onsite':
            return super()._set_pickup_location(pickup_location_data)

        pickup_location = json.loads(pickup_location_data)
        self.pickup_location_data = pickup_location

    def _get_pickup_locations(self, zip_code=None, country=None):
        """ Override of delivery `delivery._get_pickup_locations`
        """
        self.ensure_one()
        if self.carrier_id.delivery_type != 'onsite':
            return super()._get_pickup_locations(zip_code, country)
        error = {'error': _("No pick-up points are available for this delivery address.")}
        pickup_locations = self.carrier_id._onsite_get_close_locations(self)
        if not pickup_locations:
            return error
        return {'pickup_locations': pickup_locations}

    def _is_cart_in_stock(self, wh_id):
        for ol in self.order_line:
            if (
                ol.is_storable
                and ol.product_uom_qty > ol.product_id.with_context(warehouse_id=wh_id).free_qty
            ):
                return False
        return True
