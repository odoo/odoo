# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Date
from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleCollect(WebsiteSale):
    def _prepare_product_values(self, product, **kwargs):
        """Override of `website_sale` to configure the Click & Collect Availability widget."""
        res = super()._prepare_product_values(product, **kwargs)
        if not res.get("combination_info", {}).get("show_click_and_collect_availability", False):
            # Click & Collect disabled, product doesn't require delivery or a redirection is needed.
            return res

        in_store_dm_sudo = self.env.website.sudo().in_store_dm_id
        order_sudo = request.cart
        selected_location_data = {}
        single_location = len(in_store_dm_sudo.warehouse_ids) == 1
        is_in_store_selected = order_sudo.carrier_id.delivery_type == "in_store"
        estimated_dates = [
            Date.from_string(date) for date in in_store_dm_sudo._get_estimate_delivery_days()
        ]

        if is_in_store_selected and order_sudo.partner_shipping_id.pickup_location_data:
            selected_location_data = order_sudo.partner_shipping_id.pickup_location_data
            selected_location_data.update(
                **order_sudo.warehouse_id._prepare_pickup_availability_data(estimated_dates=estimated_dates)
            )
        elif single_location:
            warehouse_sudo = in_store_dm_sudo.warehouse_ids[0]
            selected_location_data = warehouse_sudo._prepare_pickup_location_data(
                estimated_dates=estimated_dates
            )

        res.update({
            "selected_location_data": selected_location_data,
            "show_select_store_button": not single_location,
            "is_in_store_selected": is_in_store_selected,
            "zip_code": (  # Define the zip code.
                order_sudo.partner_shipping_id.zip
                or selected_location_data.get("zip_code")
                or ""  # String expected for the widget.
            ),
            "country_code": (
                order_sudo.partner_shipping_id.country_id.code
                or selected_location_data.get("country_code")
                or request.geoip.country_code
                or ""
            ),
        })
        return res

    def _prepare_checkout_page_values(self, order_sudo, **query_params):
        """Override of `website_sale` to include the unavailable products for the selected pickup
        location and set the pickup location when there is only one warehouse available."""
        res = super()._prepare_checkout_page_values(order_sudo, **query_params)

        if order_sudo.only_services:
            return res

        res.update(order_sudo._prepare_in_store_default_location_data())
        if (
            order_sudo.carrier_id.delivery_type == "in_store"
            and order_sudo.partner_shipping_id.pickup_location_data
        ):
            res["insufficient_stock_data"] = order_sudo._get_insufficient_stock_data(
                order_sudo.partner_shipping_id.pickup_location_data.get("id"), add_alerts=True
            )
        return res
