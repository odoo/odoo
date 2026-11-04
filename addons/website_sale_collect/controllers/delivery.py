# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.website_sale.controllers.delivery import Delivery


class InStoreDelivery(Delivery):

    @route()
    def website_sale_get_pickup_locations(self, zip_code=None, **kwargs):
        """ Override of `website_sale` to set the pickup in store delivery method on the order in
        order to retrieve pickup locations when called from the the product page.
        """
        if kwargs.get('product_id'):  # Called from the product page.
            order_sudo = request.website.sale_get_order(force_create=True)
            in_store_dm = request.website.sudo().in_store_dm_id
            if order_sudo.carrier_id.delivery_type != 'in_store':
                order_sudo.set_delivery_line(in_store_dm, in_store_dm.product_id.list_price)
        return super().website_sale_get_pickup_locations(zip_code, **kwargs)

    @route('/shop/set_click_and_collect_location', type='json', auth='public', website=True)
    def shop_set_click_and_collect_location(self, pickup_location_data):
        """ Set the pickup location and the in-store delivery method on the current order.

        This route is distinct from /website_sale/get_pickup_locations as the latter is only called
        from the checkout page after the delivery method is selected.

        :param str pickup_location_data: The JSON-formatted pickup location data.
        :return: None
        """
        order_sudo = request.website.sale_get_order()
        if order_sudo.carrier_id.delivery_type != 'in_store':
            in_store_dm = request.website.sudo().in_store_dm_id
            order_sudo.set_delivery_line(in_store_dm, in_store_dm.product_id.list_price)
        order_sudo._set_pickup_location(pickup_location_data)

    @classmethod
    def _get_delivery_methods_express_checkout(cls, order_sudo):
        """Override to exclude `in_store` delivery methods from exress checkout delivery options."""
        dm_rate_mapping = super()._get_delivery_methods_express_checkout(order_sudo)
        for dm in list(dm_rate_mapping):
            if dm.delivery_type == 'in_store':
                del dm_rate_mapping[dm]
        return dm_rate_mapping
