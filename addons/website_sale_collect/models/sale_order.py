# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _compute_warehouse_id(self):
        """Override of `website_sale_stock` to avoid recomputations for in_store orders
        when the warehouse was set by the pickup_location_data."""
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
        """Override of `website_sale` to recompute warehouse and fiscal position when a new
        delivery method is not in-store anymore. """
        self.ensure_one()
        was_in_store_order = (
            self.carrier_id.delivery_type == 'in_store'
            and delivery_method.delivery_type != 'in_store'
        )
        super()._set_delivery_method(delivery_method, rate=rate)
        if was_in_store_order:
            fpos_before = self.fiscal_position_id
            self._compute_warehouse_id()
            self._compute_fiscal_position_id()
            if fpos_before != self.fiscal_position_id:
                self._recompute_taxes()

    def _get_preferred_delivery_method(self, available_delivery_methods):
        """Override to exclude delivery methods that cannot fulfill the order."""
        return super()._get_preferred_delivery_method(
            available_delivery_methods.filtered(self._can_be_delivered_with),
        )

    def _set_pickup_location(self, pickup_location_data):
        """Override `website_sale` to set the pickup location for in-store delivery methods.
        Set account fiscal position depending on selected pickup location to correctly calculate
        taxes.
        """
        super()._set_pickup_location(pickup_location_data)
        if self.carrier_id.delivery_type != 'in_store':
            return

        self.pickup_location_data = json.loads(pickup_location_data)
        fpos_before = self.fiscal_position_id
        if self.pickup_location_data:
            self.warehouse_id = self.pickup_location_data['id']
            self._compute_fiscal_position_id()
        else:
            self._compute_warehouse_id()
        if fpos_before != self.fiscal_position_id:
            self._recompute_taxes()

    def _get_pickup_locations(self, country=None, country_code=None, **kwargs):
        """Override of `website_sale` to include the selected country from the location selector.

        :param res.country country: The country of the shipping partner.
        :param str country_code: The country code from the location selector to look up to.
        :return: The close pickup locations data.
        :rtype: res.partner
        """
        if country_code:
            country = self.env['res.country'].search([('code', '=', country_code)], limit=1)
        return super()._get_pickup_locations(country=country, **kwargs)

    def _is_cart_ready_for_payment(self):
        """Override of `website_sale` to include errors if no pickup location is selected and to
        ensure the cart is available in the selected store, even if out-of-stock orders are
        allowed."""
        ready = super()._is_cart_ready_for_payment()
        if not self._has_deliverable_products():
            return ready

        in_store = self.carrier_id.delivery_type == 'in_store'
        if in_store and not self.pickup_location_data:
            self._add_warning_alert(self.env._("Please choose a store to collect your order."))
            return False

        # `website_sale_stock` overrides `_is_cart_ready_for_checkout` to checks stock in all
        # available warehouses on the website (store warehouses included); this checks for the
        # selected warehouse/store only.
        wh_id = self.warehouse_id.id if in_store else self._get_shop_warehouse_id()
        if wh_id and not self._is_in_stock(wh_id, add_alerts=True):
            self._add_warning_alert(
                (in_store and self.env._("Some products are not available in the selected store."))
                or self.env._(
                    "Unfortunately, we can not deliver this order with the selected delivery"
                    " method. Please update your choice and try again."
                )
            )
            return False

        return ready

    # === TOOLING ===#

    def _prepare_in_store_default_location_data(self):
        """Prepare the default pickup location values for each in-store delivery method available
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

    def _is_in_stock(self, wh_id, *, add_alerts=False):
        """Check whether all storable products of the cart are in stock in the given warehouse.

        :param int wh_id: The warehouse in which to check the stock, as a `stock.warehouse` id.
        :param bool add_alerts: Wheter to add stock alerts on the unavailable order lines.
        :return: Whether all storable products are in stock.
        :rtype: bool
        """
        insufficient_stock_data = self._get_insufficient_stock_data(wh_id)

        if add_alerts:
            for ol, avl_qty in insufficient_stock_data.items():
                ol._add_warning_alert(ol._get_shop_warning_stock(ol.product_uom_qty, avl_qty))

        return not insufficient_stock_data

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
                    free_qty, ol.product_uom_id, rounding_method='DOWN'
                )), 0)  # Round down as only integer quantities can be sold.
                line_qty_in_uom = ol.product_uom_qty
                if line_qty_in_uom > free_qty_in_uom:  # Not enough stock.
                    # Set a warning on the order line.
                    insufficient_stock_data[ol] = free_qty_in_uom
                free_qty -= ol.product_uom_id._compute_quantity(line_qty_in_uom, product.uom_id)
        return insufficient_stock_data

    def _can_be_delivered_with(self, delivery_method):
        """Determine whether the order can be delivered using the given delivery method.

        :rtype: bool
        """
        self.ensure_one()
        if not self._has_deliverable_products():
            return True

        if delivery_method.delivery_type == 'in_store':
            wh_ids = delivery_method.warehouse_ids.ids
        else:
            wh_ids = [self._get_shop_warehouse_id()]

        return any(map(self._is_in_stock, wh_ids))
