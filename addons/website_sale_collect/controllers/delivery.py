from odoo.http import request, route

from odoo.addons.website_sale.controllers.delivery import Delivery


class InStoreDelivery(Delivery):
    @route()
    def website_sale_get_pickup_locations(self, zip_code=None, **kwargs):
        if kwargs.get("product_id"):
            order_sudo = request.cart
            in_store_dm = request.website.sudo().in_store_dm_id
            if not order_sudo:
                temp_order = request.env["sale.order"].new(
                    {"carrier_id": in_store_dm.id}
                )
                return temp_order.sudo()._get_pickup_locations(zip_code, **kwargs)
            elif order_sudo.carrier_id.delivery_type != "in_store":
                order_sudo.set_delivery_line(
                    in_store_dm, in_store_dm.product_id.list_price
                )
        return super().website_sale_get_pickup_locations(zip_code, **kwargs)

    @route(
        "/shop/set_click_and_collect_location",
        type="jsonrpc",
        auth="public",
        website=True,
    )
    def shop_set_click_and_collect_location(self, pickup_location_data):
        order_sudo = request.cart or request.website._create_cart()
        if order_sudo.carrier_id.delivery_type != "in_store":
            in_store_dm = request.website.sudo().in_store_dm_id
            order_sudo.set_delivery_line(in_store_dm, in_store_dm.product_id.list_price)
        order_sudo._set_pickup_location(pickup_location_data)

    def _prepare_additional_delivery_context(self):
        res = super()._prepare_additional_delivery_context()
        order_sudo = request.cart
        if request.website.sudo().in_store_dm_id:
            res.update(order_sudo._prepare_in_store_default_location_data())
        return res

    @classmethod
    def _get_delivery_methods_express_checkout(cls, order_sudo):
        dm_rate_mapping = super()._get_delivery_methods_express_checkout(order_sudo)
        for dm in list(dm_rate_mapping):
            if dm.delivery_type == "in_store":
                del dm_rate_mapping[dm]
        return dm_rate_mapping
