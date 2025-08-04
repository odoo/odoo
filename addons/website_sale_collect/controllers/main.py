# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
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
            })
        return res

    def _prepare_checkout_page_values(self, order_sudo, **query_params):
        """ Override of `website_sale` to include the unavailable products for the selected pickup
        location and set the pickup location when there is only one warehouse available. """
        res = super()._prepare_checkout_page_values(order_sudo, **query_params)

        res.update(order_sudo._prepare_in_store_default_location_data())
        notif_enabled_ids = request.session.get('product_with_stock_notification_enabled', [])
        if order_sudo.carrier_id.delivery_type == 'in_store' and order_sudo.pickup_location_data:
            partner = order_sudo.partner_id
            unavailable_order_lines = order_sudo._get_unavailable_order_lines(
                order_sudo.pickup_location_data.get('id')
            )
            products_with_stock_notification = unavailable_order_lines.product_id.filtered(
                lambda p: p.id in notif_enabled_ids or p._has_stock_notification(partner),
            )
            email = request.session.get('stock_notification_email', partner.email) or ''
            res.update(
                unavailable_order_lines=unavailable_order_lines,
                products_with_stock_notification=products_with_stock_notification,
                stock_notification_email=email,
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
