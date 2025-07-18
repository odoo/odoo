# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import models
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

    def set_delivery_line(self, carrier, amount):
        """ Override of `website_sale` to recompute warehouse and fiscal position when a new
        delivery method is not in-store anymore. """
        in_store_orders = self.filtered(
            lambda so: (
                so.carrier_id.delivery_type == 'in_store' and carrier.delivery_type != 'in_store'
            )
        )
        res = super().set_delivery_line(carrier, amount)
        in_store_orders._compute_warehouse_id()
        in_store_orders._compute_fiscal_position_id()
        return res

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

    def _is_cart_ready_for_payment(self):
        """Override of `website_sale` to includes errors if no pickup location is selected and to
        ensure the cart is available in the selected store no even if out of stock orders are
        allowed."""
        if not self._has_deliverable_products():
            return super()._is_cart_ready_for_payment()

        if self.carrier_id.delivery_type == 'in_store':
            if not self.pickup_location_data:
                self.shop_warning = self.env._("Please choose a store to collect your order.")
                return False
            # `_is_cart_ready_for_checkout` checks for all the available in-store warehouse, we must
            # now check for the selected warehouse.
            if not self._is_in_stock(self.warehouse_id.id):
                self.shop_warning = self.env._(
                    "Some products are not available in the selected store."
                )
                return False

        # If `shop_wh_id` is not False, limit the cart availability to the shop warehouse. False
        # indicates the website uses any warehouse, including in-store warehouses, which is already
        # checked in `_is_cart_ready_for_checkout`.
        elif (shop_wh_id := self._get_shop_warehouse_id()) and not self._is_in_stock(
            shop_wh_id, allow_out_of_stock=True,
        ):
            self.shop_warning = self.env._(
                "Unfortunately, we can not deliver this order with the selected delivery"
                " method. Please update your choice and try again."
            )
            return False

        return super()._is_cart_ready_for_payment()

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
                        'unavailable_order_lines': self._get_unavailable_order_lines(
                            pickup_location_data['id']
                        ),
                    }

        return {'default_pickup_locations': default_pickup_locations}

    def _is_in_stock(self, wh_id, allow_out_of_stock=False):
        """ Check whether all storable products of the cart are in stock in the given warehouse.

        :param int wh_id: The warehouse in which to check the stock, as a `stock.warehouse` id.
        :param bool allow_out_of_stock: Wheter `product.allow_out_of_stock_order` should be taken
            into account or not.
        :return: Whether all storable products are in stock.
        :rtype: bool
        """
        return not self._get_unavailable_order_lines(wh_id, allow_out_of_stock=allow_out_of_stock)

    def _get_unavailable_order_lines(self, wh_id, allow_out_of_stock=False):
        """ Return the order lines with unavailable products for the given warehouse.

        :param int wh_id: The warehouse in which to check the stock, as a `stock.warehouse` id.
        :param bool allow_out_of_stock: Wheter `product.allow_out_of_stock_order` should be taken
            into account or not.
        :return: The order lines with unavailable products.
        :rtype: sale.order.line
        """
        unavailable_order_lines = self.env['sale.order.line']
        for ol in self.order_line.filtered('is_storable'):
            product = ol.product_id
            if not (allow_out_of_stock and product.allow_out_of_stock_order):
                cart_qty = self._get_cart_qty(product.id)
                free_qty = product.with_context(warehouse_id=wh_id).free_qty
                if cart_qty > free_qty:
                    ol._set_shop_warning_stock(cart_qty, max(free_qty, 0))
                    unavailable_order_lines |= ol
        return unavailable_order_lines

    def _can_be_delivered(self, dm):
        """Whether the order can be delivered using the given delivery method.

        In-store deliveries need to ensure stock is available even if `allow_out_of_stock` is
        enabled, as customers can pick up their order at any moment without leaving time to refill
        the stock.

        :param delivery.carrier dm: The delivery method to use to check for stock availability.
        :rtype: bool
        """
        self.ensure_one()
        if not self._has_deliverable_products():
            return True

        if dm.delivery_type == 'in_store':
            return any(self._is_in_stock(wh_id) for wh_id in dm.warehouse_ids.ids)
        return self._is_in_stock(self._get_shop_warehouse_id(), allow_out_of_stock=True)
