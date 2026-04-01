# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import models
from odoo.exceptions import ValidationError
from odoo.http import request


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _compute_warehouse_id(self):
        """ Override of `website_sale_stock` to avoid recomputations for in_store orders
        when the warehouse was set by the pickup_location_data"""
        in_store_orders_with_pickup_data = self.filtered(
            lambda so: (
                so.carrier_id.delivery_type == 'in_store' and so.pickup_location_data
            )
        )
        super(SaleOrder, self - in_store_orders_with_pickup_data)._compute_warehouse_id()
        for order in in_store_orders_with_pickup_data:
            order.warehouse_id = order.pickup_location_data['id']

    def _compute_fiscal_position_id(self):
        """Override of `sale` to set the fiscal position matching the selected pickup location
        for pickup in-store orders."""
        in_store_orders = self.filtered(
            lambda so: so.carrier_id.delivery_type == 'in_store' and so.pickup_location_data
        )
        AccountFiscalPosition = self.env['account.fiscal.position'].sudo()
        for order in in_store_orders:
            order.fiscal_position_id = AccountFiscalPosition._get_fiscal_position(
                order.partner_id, delivery=order.warehouse_id.partner_id
            )
        super(SaleOrder, self - in_store_orders)._compute_fiscal_position_id()

    def _get_free_qty(self, product):
        """Override of `website_sale_stock` to consider the maximum available quantity across
        all in-store warehouses when no delivery method is set on the order yet."""
        if (
            self.website_id.warehouse_id
            and self.website_id.in_store_dm_id
            and not self.carrier_id
        ):
            return self.website_id.sudo()._get_max_in_store_product_available_qty(product)
        return super()._get_free_qty(product)

    def _set_delivery_method(self, delivery_method, rate=None):
        """ Override of `website_sale` to recompute warehouse and fiscal position when a new
        delivery method is not in-store anymore. """

        self.ensure_one()
        was_in_store_order = (
            self.carrier_id.delivery_type == 'in_store'
            and delivery_method.delivery_type != 'in_store'
        )
        super()._set_delivery_method(delivery_method, rate=rate)
        if was_in_store_order:
            self._compute_warehouse_id()
            self._compute_fiscal_position_id()

    def _set_pickup_location(self, pickup_location_data):
        """ Override `website_sale` to set the pickup location for in-store delivery methods.
        Set account fiscal position depending on selected pickup location to correctly calculate
        taxes.
        """
        super()._set_pickup_location(pickup_location_data)
        if self.carrier_id.delivery_type != 'in_store':
            return

        self.pickup_location_data = json.loads(pickup_location_data)
        if self.pickup_location_data:
            self.warehouse_id = self.pickup_location_data['id']
            self._compute_fiscal_position_id()
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

    def _check_cart_is_ready_to_be_paid(self):
        """ Override of `website_sale` to check if all products are in stock in the selected
        warehouse. """
        if (
            self._has_deliverable_products()
            and self.carrier_id.delivery_type == 'in_store'
            and not self._is_in_stock(self.warehouse_id.id)
        ):
            raise ValidationError(self.env._(
                "Some products are not available in the selected store."
            ))
        return super()._check_cart_is_ready_to_be_paid()

    # === TOOLING ===#

    def _prepare_in_store_default_location_data(self):
        """ Prepare the default pickup location values for each in-store delivery method available
        for the order. """
        default_pickup_locations = {}
        for dm in self._get_delivery_methods():
            if (
                dm.delivery_type == 'in_store'
                and dm.id != self.carrier_id.id
                and len(dm.warehouse_ids) == 1
            ):
                pickup_location_data = dm.warehouse_ids[0]._prepare_pickup_location_data()
                if pickup_location_data:
                    default_pickup_locations[dm.id] = {
                        'pickup_location_data': pickup_location_data,
                        'insufficient_stock_data': self._get_insufficient_stock_data(
                            pickup_location_data['id']
                        ),
                    }

        return {'default_pickup_locations': default_pickup_locations}

    def _is_in_stock(self, wh_id):
        """ Check whether all storable products of the cart are in stock in the given warehouse.

        :param int wh_id: The warehouse in which to check the stock, as a `stock.warehouse` id.
        :return: Whether all storable products are in stock.
        :rtype: bool
        """
        return not self._get_insufficient_stock_data(wh_id)

    def _get_insufficient_stock_data(self, wh_id):
        """Return the mapping of order lines with insufficient stock in the given warehouse to their
        maximum available quantity in the line's UoM.
        If there are multiple order lines for the same product, consider the sum of their
        quantities.

        :param int wh_id: The warehouse in which to check the stock, as a `stock.warehouse` id.
        :return: The mapping of order lines to their maximum available quantity.
        :rtype: dict
        """
        insufficient_stock_data = {}
        for product, ols in self.order_line.grouped('product_id').items():
            if not product.is_storable or product.allow_out_of_stock_order:
                continue
            free_qty = product.with_context(warehouse_id=wh_id).free_qty
            for ol in ols:
                free_qty_in_uom = max(int(product.uom_id._compute_quantity(
                    free_qty, ol.product_uom_id, rounding_method="DOWN"
                )), 0)  # Round down as only integer quantities can be sold.
                line_qty_in_uom = ol.product_uom_qty
                if line_qty_in_uom > free_qty_in_uom:  # Not enough stock.
                    # Set a warning on the order line.
                    insufficient_stock_data[ol] = free_qty_in_uom
                    ol.shop_warning = self.env._(
                        "%(available_qty)s/%(line_qty)s available at this location",
                        available_qty=free_qty_in_uom, line_qty=int(line_qty_in_uom),
                    )
                free_qty -= ol.product_uom_id._compute_quantity(line_qty_in_uom, product.uom_id)
        return insufficient_stock_data
