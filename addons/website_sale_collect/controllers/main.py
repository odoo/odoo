# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleCollect(WebsiteSale):

    def _prepare_product_values(self, product, category, search, **kwargs):
        """ Override of `website_sale` to include the selected pickup location and zip code. """
        res = super()._prepare_product_values(product, category, search, **kwargs)
        if request.website.sudo().in_store_dm_id:
            order_sudo = request.website.sale_get_order()
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
        location. """
        res = super()._prepare_checkout_page_values(order_sudo, **query_params)
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
