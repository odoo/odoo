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

    def _get_preferred_delivery_method(self, available_delivery_methods):
        """Override to exclude delivery methods that cannot fulfill the order."""
        return super()._get_preferred_delivery_method(
            available_delivery_methods.filtered(self._can_be_delivered),
        )

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
        """Override of `website_sale` to include errors if no pickup location is selected and to
        ensure the cart is available in the selected store, even if out-of-stock orders are
        allowed."""
        if not self._has_deliverable_products():
            return super()._is_cart_ready_for_payment()

        in_store = self.carrier_id.delivery_type == 'in_store'
        if in_store and not self.pickup_location_data:
            self.shop_warning = self.env._("Please choose a store to collect your order.")
            return False

        # `_is_cart_ready_for_checkout` checks stock in all available warehouses; this checks for
        # the selected warehouse/store.
        warehouse_id = self.warehouse_id.id if in_store else self._get_shop_warehouse_id()
        if warehouse_id and not self._is_in_stock(warehouse_id, allow_out_of_stock=not in_store):
            self.shop_warning = (
                in_store and self.env._("Some products are not available in the selected store.")
                or self.env._(
                    "Unfortunately, we can not deliver this order with the selected delivery"
                    " method. Please update your choice and try again.",
                )
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
                        'insufficient_stock_data': self.with_context(
                            save_shop_warning=False
                        )._get_insufficient_stock_data(pickup_location_data['id']),
                    }

        return {'default_pickup_locations': default_pickup_locations}

    def _is_in_stock(self, wh_id, allow_out_of_stock=False):
        """ Check whether all storable products of the cart are in stock in the given warehouse.

        :param int wh_id: The warehouse in which to check the stock, as a `stock.warehouse` id.
        :param bool allow_out_of_stock: Whether `product.allow_out_of_stock_order` should be taken
            into account or not.
        :return: Whether all storable products are in stock.
        :rtype: bool
        """
        return not self._get_insufficient_stock_data(wh_id, allow_out_of_stock=allow_out_of_stock)

    def _get_insufficient_stock_data(self, wh_id, allow_out_of_stock=False):
        """Return the mapping of order lines with insufficient stock in the given warehouse to their
        maximum available quantity in the line's UoM.
        If there are multiple order lines for the same product, consider the sum of their
        quantities.

        :param int wh_id: The warehouse in which to check the stock, as a `stock.warehouse` id.
        :param bool allow_out_of_stock: Wheter `product.allow_out_of_stock_order` should be taken
            into account or not.
        :return: The mapping of order lines to their maximum available quantity.
        :rtype: dict
        """
        insufficient_stock_data = {}
        for product, ols in self.order_line.grouped('product_id').items():
            if not product.is_storable:
                continue
            if allow_out_of_stock and product.allow_out_of_stock_order:
                continue
            free_qty = product.with_context(warehouse_id=wh_id).free_qty
            for ol in ols:
                free_qty_in_uom = max(
                    int(product.uom_id._compute_quantity(free_qty, ol.product_uom_id)), 0
                )  # Round down as only integer quantities can be sold.
                if ol.product_uom_qty > free_qty_in_uom:
                    insufficient_stock_data[ol] = free_qty_in_uom
                    if self.env.context.get('save_shop_warning', True):
                        ol.shop_warning = self.env._(
                            "%(available_qty)s/%(line_qty)s available at this location",
                            available_qty=free_qty_in_uom, line_qty=int(ol.product_uom_qty),
                        )
                free_qty -= ol.product_uom_id._compute_quantity(free_qty_in_uom, product.uom_id)
        return insufficient_stock_data

    def _can_be_delivered(self, dm):
        """Determine whether the order can be delivered using the given delivery method.

        For in-store deliveries, stock availability must be ensured even if `allow_out_of_stock` is
        enabled, since customers may collect their order at any time without notice.

        :param delivery.carrier dm: The delivery method to check for stock availability.
        :rtype: bool
        """
        self.ensure_one()
        if not self._has_deliverable_products():
            return True

        if dm.delivery_type == 'in_store':
            return any(
                self.with_context(save_shop_warning=False)._is_in_stock(wh_id)
                for wh_id in dm.warehouse_ids.ids
            )

        return self.with_context(save_shop_warning=False)._is_in_stock(
            self._get_shop_warehouse_id(), allow_out_of_stock=True,
        )
