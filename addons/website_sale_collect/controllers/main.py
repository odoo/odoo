# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleCollect(WebsiteSale):

    def _prepare_product_values(self, product, category, search, **kwargs):
        """ Override of `website_sale` to include the selected pickup location and zip code. """
        res = super()._prepare_product_values(product, category, search, **kwargs)
        if request.website.sudo().in_store_dm_id:
            order_sudo = request.cart
            if (
                order_sudo.carrier_id.delivery_type == 'in_store'
                and order_sudo.pickup_location_data
            ):
                res['selected_wh_location'] = order_sudo.pickup_location_data
            res['zip_code'] = (  # Define the zip code.
                order_sudo.partner_shipping_id.zip
                or res.get('selected_wh_location', {}).get('zip_code')
                or request.geoip.postal.code
            )
        return res

    def _prepare_checkout_page_values(self, order_sudo, **query_params):
        """ Override of `website_sale` to include the unavailable products for the selected pickup
        location and set the pickup location when there is only one warehouse available. """
        res = super()._prepare_checkout_page_values(order_sudo, **query_params)

        res['default_pickup_locations'] = {
            in_store_dm.id: {
                'pickup_location_data': (
                    pickup_location_data := in_store_dm._in_store_get_close_locations(
                        partner_address=order_sudo.partner_shipping_id,
                    )[0]
                ),
                'unavailable_order_lines': order_sudo._get_unavailable_order_lines(
                    pickup_location_data['id']
                ),
            }
            for in_store_dm in order_sudo._get_delivery_methods().filtered(
                lambda dm: dm.delivery_type == 'in_store' and len(dm.warehouse_ids) == 1
            ) - order_sudo.carrier_id # If Pickup is selected, assume location data is included.
        }
        if order_sudo.carrier_id.delivery_type == 'in_store' and order_sudo.pickup_location_data:
            res['unavailable_order_lines'] = order_sudo._get_unavailable_order_lines(
                order_sudo.pickup_location_data.get('id')
            )
        return res

    def _get_shop_payment_errors(self, order):
        """ Override of `website_sale` to includes errors if no pickup location is selected or some
        products are unavailable. """
        errors = super()._get_shop_payment_errors(order)
        if order._has_deliverable_products() and order.carrier_id.delivery_type == 'in_store':
            if not order.pickup_location_data:
                errors.append((
                    _("Sorry, we are unable to ship your order."),
                    _("Please choose a store to collect your order."),
                ))
            else:
                selected_wh_id = order.pickup_location_data['id']
                if not order._is_in_stock(selected_wh_id):
                    errors.append((
                        _("Sorry, we are unable to ship your order."),
                        _("Some products are not available in the selected store."),
                    ))
        return errors
