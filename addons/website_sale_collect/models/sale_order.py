# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, models
from odoo.exceptions import ValidationError
from odoo.http import request


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _set_pickup_location(self, pickup_location_data):
        """ Override `website_sale` to set the pickup location for in-store delivery methods. """
        res = super()._set_pickup_location(pickup_location_data)
        if self.carrier_id.delivery_type != 'in_store':
            return res

        self.pickup_location_data = json.loads(pickup_location_data)

    def _get_pickup_locations(self, zip_code=None, country=None, **kwargs):
        """ Override of `website_sale` to ensure that a country is provided when there is a zip
        code.

        If the country cannot be found (e.g., the GeoIP request fails), the zip code is cleared to
        prevent the parent method's assertion to fail.
        """
        if zip_code and not country:
            country_code = None
            if self.pickup_location_data:
                country_code = self.pickup_location_data['country_code']
            elif request.geoip.country_code:
                country_code = request.geoip.country_code
            country = self.env['res.country'].search([('code', '=', country_code)], limit=1)
            if not country:
                zip_code = None  # Reset the zip code to skip the `assert` in the `super` call.
        return super()._get_pickup_locations(zip_code=zip_code, country=country, **kwargs)

    def _check_cart_is_ready_to_be_paid(self):
        """ Override of `website_sale` to check if all products are in stock in the selected
        warehouse. """
        if (
            self._has_deliverable_products()
            and self.carrier_id.delivery_type == 'in_store'
            and not self._is_in_stock(self.pickup_location_data['warehouse_id'])
        ):
            raise ValidationError(_("Some products are not available in the selected store."))
        return super()._check_cart_is_ready_to_be_paid()

    # === TOOLING ===#

    def _is_in_stock(self, wh_id):
        """ Check whether all storable products of the cart are in stock in the given warehouse.

        :param int wh_id: The warehouse in which to check the stock, as a `stock.warehouse` id.
        :return: Whether all storable products are in stock.
        :rtype: bool
        """
        return not self._get_unavailable_products(wh_id)

    def _get_unavailable_products(self, wh_id):
        """ Return the products that are not in stock for the given warehouse.

        :param int wh_id: The warehouse in which to check the stock, as a `stock.warehouse` id.
        :return: The products that are not in stock.
        :rtype: product.product
        """
        out_of_stock_products = self.order_line.filtered(
            lambda l: l.is_storable
            and l.product_uom_qty > l.product_id.with_context(warehouse_id=wh_id).free_qty
        ).product_id
        return out_of_stock_products
