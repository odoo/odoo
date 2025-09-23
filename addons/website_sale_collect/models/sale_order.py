# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, models
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

    def _get_cart_and_free_qty(self, product, line=None):
        """ Override of `website_sale_stock` to get free_qty of the product from the warehouse that
        was chosen rather than website's one.

        :param product.product product: The product
        :param sale.order.line line: The optional line
        """
        cart_qty, free_qty = super()._get_cart_and_free_qty(product, line=line)
        if self.carrier_id.delivery_type == 'in_store':
            free_qty = (product or line.product_id).with_context(
                warehouse_id=self.warehouse_id.id
            ).free_qty
        return cart_qty, free_qty

    def _check_cart_is_ready_to_be_paid(self):
        """ Override of `website_sale` to check if all products are in stock in the selected
        warehouse. """
        if (
            self._has_deliverable_products()
            and self.carrier_id.delivery_type == 'in_store'
            and not self._is_in_stock(self.warehouse_id.id)
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
        return not self._get_unavailable_order_lines(wh_id)

    def _get_unavailable_order_lines(self, wh_id):
        """ Return the order lines with unavailable products for the given warehouse.

        :param int wh_id: The warehouse in which to check the stock, as a `stock.warehouse` id.
        :return: The order lines with unavailable products.
        :rtype: sale.order.line
        """
        unavailable_order_lines = self.env['sale.order.line']
        for ol in self.order_line:
            if ol.is_storable:
                product_free_qty = ol.product_id.with_context(warehouse_id=wh_id).free_qty
                if ol.product_uom_qty > product_free_qty:
                    ol.shop_warning = _(
                        'Only %(new_qty)s available', new_qty=int(max(product_free_qty, 0))
                    )
                    unavailable_order_lines |= ol
        return unavailable_order_lines

    def _verify_updated_quantity(self, order_line, product_id, new_qty, **kwargs):
        """ Override of `website_sale_stock` to skip the verification when click and collect
        is activated. The quantity is verified later. """
        self.ensure_one()
        product = self.env['product.product'].browse(product_id)
        if (
            product.is_storable
            and not product.allow_out_of_stock_order
            and self.website_id.in_store_dm_id
        ):
            return new_qty, ''
        return super()._verify_updated_quantity(order_line, product_id, new_qty, **kwargs)
