# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleCollect(WebsiteSale):

    def _prepare_product_values(self, product, category, **kwargs):
        """ Override of `website_sale` to configure the Click & Collect Availability widget. """
        res = super()._prepare_product_values(product, category, **kwargs)
        if in_store_dm_sudo := request.website.sudo().in_store_dm_id:
            order_sudo = request.cart
            selected_location_data = {}
            single_location = len(in_store_dm_sudo.warehouse_ids) == 1
            if (
                order_sudo.carrier_id.delivery_type == 'in_store'
                and order_sudo.pickup_location_data
            ):
                selected_location_data = order_sudo.pickup_location_data
            elif single_location:
                selected_location_data = (
                    in_store_dm_sudo.warehouse_ids[0]._prepare_pickup_location_data()
                )
            res.update({
                'selected_location_data': selected_location_data,
                'show_select_store_button': not single_location,
                'zip_code': (  # Define the zip code.
                    order_sudo.partner_shipping_id.zip
                    or selected_location_data.get('zip_code')
                    or request.geoip.postal.code
                    or ''  # String expected for the widget.
                ),
                'country_code': (
                    order_sudo.partner_shipping_id.country_id.code
                    or selected_location_data.get('country_code')
                    or request.geoip.country_code
                    or ''
                ),
                'delivery_method': in_store_dm_sudo,
            })
        return res

    def _prepare_checkout_page_values(self, order_sudo, **query_params):
        """ Override of `website_sale` to include the unavailable products for the selected pickup
        location and set the pickup location when there is only one warehouse available. """
        res = super()._prepare_checkout_page_values(order_sudo, **query_params)

        if order_sudo.only_services:
            return res

        res.update(order_sudo._prepare_in_store_default_location_data())
        if order_sudo.carrier_id.delivery_type == 'in_store' and order_sudo.pickup_location_data:
            res['insufficient_stock_data'] = order_sudo._get_insufficient_stock_data(
                order_sudo.pickup_location_data.get('id')
            )
            for ol, available_qty in res['insufficient_stock_data'].items():
                ol._add_alert(
                    'warning', ol._get_shop_warning_stock(ol.product_uom_qty, available_qty)
                )
        return res
