# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import models
from odoo.http import request


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def set_delivery_line(self, carrier, amount):
        """ Override of `website_sale` to recompute warehouse and fiscal position when a new
        delivery method is not in-store anymore. """
        in_store_orders = self.filtered(
            lambda so: (
                so.carrier_id.delivery_type == 'in_store' and carrier.delivery_type != 'in_store'
            )
        )
        in_store_orders._compute_warehouse_id()
        in_store_orders._compute_fiscal_position_id()
        return super().set_delivery_line(carrier, amount)

    def _set_pickup_location(self, pickup_location_data):
        """ Override `website_sale` to set the pickup location for in-store delivery methods.
        Set account fiscal position depending on selected pickup location to correctly calculate
        taxes.
        """
        res = super()._set_pickup_location(pickup_location_data)
        if self.carrier_id.delivery_type != 'in_store':
            return res

        self.pickup_location_data = json.loads(pickup_location_data)
        if self.pickup_location_data:
            self.warehouse_id = self.pickup_location_data['id']
            AccountFiscalPosition = self.env['account.fiscal.position'].sudo()
            self.fiscal_position_id = AccountFiscalPosition._get_fiscal_position(
                self.partner_id, delivery=self.warehouse_id.partner_id
            )
        else:
            self._compute_warehouse_id()

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

    def _get_shop_warehouse_id(self):
        """Override of `website_sale_stock` to consider the chosen warehouse."""
        self.ensure_one()
        if self.carrier_id.delivery_type == 'in_store':
            return self.warehouse_id.id
        return super()._get_shop_warehouse_id()

    def _build_stock_warning(self):
        """Override of `website_sale_stock` if the selected delivery method is of type `in_store`"""
        if self.carrier_id.delivery_type == 'in_store':
            return self.env._("Some products are not available in the selected store.")
        return super()._build_stock_warning()

    # === TOOLING ===#

    def _verify_updated_quantity(self, order_line, product_id, new_qty, **kwargs):
        """ Override of `website_sale_stock` to skip the verification when click and collect
        is activated. The quantity is verified later. """
        product = self.env['product.product'].browse(product_id)
        if (
            product.is_storable
            and not product.allow_out_of_stock_order
            and self.website_id.in_store_dm_id
        ):
            return new_qty, ''
        return super()._verify_updated_quantity(order_line, product_id, new_qty, **kwargs)
