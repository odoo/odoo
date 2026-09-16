import json

from odoo import models
from odoo.exceptions import ValidationError
from odoo.http import request


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _compute_warehouse_id(self):
        in_store_orders_with_pickup_data = self.filtered(
            lambda so: (
                so.carrier_id.delivery_type == "in_store" and so.pickup_location_data
            )
        )
        super(
            SaleOrder, self - in_store_orders_with_pickup_data
        )._compute_warehouse_id()
        for order in in_store_orders_with_pickup_data:
            order.warehouse_id = order.pickup_location_data["id"]

    def _compute_fiscal_position_id(self):
        in_store_orders = self.filtered(
            lambda so: (
                so.carrier_id.delivery_type == "in_store" and so.pickup_location_data
            )
        )
        AccountFiscalPosition = self.env["account.fiscal.position"].sudo()
        for order in in_store_orders:
            order.fiscal_position_id = AccountFiscalPosition._get_fiscal_position(
                order.partner_id, delivery=order.warehouse_id.partner_id
            )
        super(SaleOrder, self - in_store_orders)._compute_fiscal_position_id()

    def _set_delivery_method(self, delivery_method, rate=None):

        self.check_singleton()
        was_in_store_order = (
            self.carrier_id.delivery_type == "in_store"
            and delivery_method.delivery_type != "in_store"
        )
        super()._set_delivery_method(delivery_method, rate=rate)
        if was_in_store_order:
            self._compute_warehouse_id()
            self._compute_fiscal_position_id()

    def _set_pickup_location(self, pickup_location_data):
        super()._set_pickup_location(pickup_location_data)
        if self.carrier_id.delivery_type != "in_store":
            return

        self.pickup_location_data = json.loads(pickup_location_data)
        if self.pickup_location_data:
            self.warehouse_id = self.pickup_location_data["id"]
            self._compute_fiscal_position_id()
        else:
            self._compute_warehouse_id()

    def _get_pickup_locations(self, zip_code=None, country=None, **kwargs):
        if zip_code and not country:
            country_code = None
            if self.pickup_location_data:
                country_code = self.pickup_location_data["country_code"]
            elif request.geoip.country_code:
                country_code = request.geoip.country_code
            country = self.env["res.country"].search(
                [("code", "=", country_code)], limit=1
            )
            if not country:
                zip_code = None
        return super()._get_pickup_locations(
            zip_code=zip_code, country=country, **kwargs
        )

    def _get_shop_warehouse_id(self):
        self.check_singleton()
        if self.carrier_id.delivery_type == "in_store":
            return self.warehouse_id.id
        return super()._get_shop_warehouse_id()

    def _check_cart_is_ready_to_be_paid(self):
        if (
            self._has_deliverable_products()
            and self.carrier_id.delivery_type == "in_store"
            and not self._is_in_stock(self.warehouse_id.id)
        ):
            raise ValidationError(
                self.env._("Some products are not available in the selected store.")
            )
        return super()._check_cart_is_ready_to_be_paid()

    def _prepare_in_store_default_location_data(self):
        default_pickup_locations = {}
        for dm in self._get_delivery_methods():
            if (
                dm.delivery_type == "in_store"
                and dm.id != self.carrier_id.id
                and len(dm.warehouse_ids) == 1
            ):
                warehouse = dm.warehouse_ids[0]
                warehouse._update_missing_coordinates()
                pickup_location_data = warehouse._prepare_pickup_location_data()
                if pickup_location_data:
                    default_pickup_locations[dm.id] = {
                        "pickup_location_data": pickup_location_data,
                        "insufficient_stock_data": self._get_insufficient_stock_data(
                            pickup_location_data["id"]
                        ),
                    }

        return {"default_pickup_locations": default_pickup_locations}

    def _is_in_stock(self, wh_id):
        return not self._get_insufficient_stock_data(wh_id)

    def _get_insufficient_stock_data(self, wh_id):
        insufficient_stock_data = {}
        for product, ols in self.line_ids.grouped("product_id").items():
            if not product.is_storable or product.allow_out_of_stock_order:
                continue
            qty_free = product.with_context(warehouse_id=wh_id).qty_free
            for ol in ols:
                free_qty_in_uom = max(
                    int(
                        product.uom_id._get_quantity_in_unit(
                            qty_free, ol.product_uom_id, rounding_method="DOWN"
                        )
                    ),
                    0,
                )
                line_qty_in_uom = ol.product_qty
                if line_qty_in_uom > free_qty_in_uom:
                    insufficient_stock_data[ol] = free_qty_in_uom
                    ol.shop_warning = self.env._(
                        "%(available_qty)s/%(line_qty)s available at this location",
                        available_qty=free_qty_in_uom,
                        line_qty=int(line_qty_in_uom),
                    )
                qty_free -= ol.product_uom_id._get_quantity_in_unit(
                    line_qty_in_uom, product.uom_id
                )
        return insufficient_stock_data

    def _get_updated_quantity(self, order_line, product_id, new_qty, uom_id, **kwargs):
        product = self.env["product.product"].browse(product_id)
        if (
            product.is_storable
            and not product.allow_out_of_stock_order
            and self.website_id.in_store_dm_id
        ):
            return new_qty, ""
        return super()._get_updated_quantity(
            order_line, product_id, new_qty, uom_id, **kwargs
        )
