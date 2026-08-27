# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request

from odoo.addons.website_sale_collect import utils


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _get_additional_combination_info(
        self, product_or_template, quantity, uom, website, pricelist, fiscal_position, **kwargs
    ):
        """Override of `website_sale` to add information on whether Click & Collect is enabled and
        on the stock of the product."""
        res = super()._get_additional_combination_info(
            product_or_template, quantity, uom, website, pricelist, fiscal_position, **kwargs
        )
        res["in_store_data"] = {}
        res["delivery_data"] = {}

        if not (product_or_template.is_product_variant and product_or_template.type == "consu"):
            # Dynamic/Impossible combination or product that is not a Goods (e.g. a service).
            return res

        in_store_dm = website.sudo().in_store_dm_id
        if not in_store_dm:  # Click & Collect is disabled
            return res

        product_sudo = product_or_template.sudo()  # To read the stock values when public user.
        order_sudo = (
            request.cart
            if (request and hasattr(request, "cart"))
            else self.env["sale.order"].sudo()
        )
        cart_qty = order_sudo._get_cart_qty(product_sudo.id)
        # Enable the Click & Collect Availability widget.
        res["show_click_and_collect_availability"] = True
        res["uom_id"] = uom.id

        # Prepare the delivery stock data.
        DeliveryCarrier = self.env["delivery.carrier"].sudo()
        available_delivery_methods_sudo = DeliveryCarrier.search([
            "|",
            ("website_id", "=", website.id),
            ("website_id", "=", False),
            ("website_published", "=", True),
            ("delivery_type", "!=", "in_store"),
        ])
        product_tags = product_or_template.all_product_tag_ids
        country_id = order_sudo.partner_shipping_id.country_id
        if not country_id and not self.env.user._is_public():
            country_id = self.env.user.partner_id.country_id
        if not country_id:
            geoip_country_code = website._get_geoip_country_code()
            if geoip_country_code:
                country_id = self.env["res.country"].search(
                    [("code", "=", geoip_country_code)], limit=1
                )
        valid_delivery_methods = available_delivery_methods_sudo.filtered(
            lambda dm: (
                not (dm.excluded_tag_ids & product_tags)
                and (not dm.country_ids or country_id in dm.country_ids)
            )
        )
        if valid_delivery_methods:
            # Suggest the fastest delivery method.
            estimated_dates_by_dm = {
                dm.id: dm._get_estimate_delivery_days()[:1] for dm in valid_delivery_methods
            }
            fastest_delivery_method = valid_delivery_methods.sorted(
                key=lambda dm: (not estimated_dates_by_dm[dm.id], estimated_dates_by_dm[dm.id])
            )[0]
            fastest_estimated_dates = estimated_dates_by_dm[fastest_delivery_method.id]
            res["delivery_data"] = utils.prepare_cac_widget_data(
                fastest_delivery_method,
                utils.format_product_stock_values(
                    product_sudo,
                    warehouse_id=website.warehouse_id.id,
                    uom=uom,
                    cart_qty=cart_qty,
                    **kwargs,
                ),
                fastest_estimated_dates[0] if fastest_estimated_dates else "",
            )

        # If C&C not excluded via tags, prepare the in-store stock data.
        if not (in_store_dm.excluded_tag_ids & product_or_template.all_product_tag_ids):
            if (
                order_sudo
                and order_sudo.carrier_id.delivery_type == "in_store"
                and order_sudo.partner_shipping_id.pickup_location_data
            ):  # Get stock values for the product variant in the selected store.
                in_store_stock_data = utils.format_product_stock_values(
                    product_sudo,
                    uom=uom,
                    warehouse_id=order_sudo.partner_shipping_id.pickup_location_data["id"],
                    cart_qty=cart_qty,
                    **kwargs,
                )
            else:
                in_store_stock_data = utils.format_product_stock_values(
                    product_sudo,
                    uom=uom,
                    free_qty=max(
                        product_sudo._get_free_qty(warehouse_id=wh.id, **kwargs)
                        for wh in website.sudo().in_store_dm_id.warehouse_ids
                    ),
                    cart_qty=cart_qty,
                    **kwargs,
                )
            in_store_estimated_dates = in_store_dm._get_estimate_delivery_days()
            res["in_store_data"] = utils.prepare_cac_widget_data(
                in_store_dm,
                in_store_stock_data,
                in_store_estimated_dates[0] if in_store_estimated_dates else "",
            )

        return res
