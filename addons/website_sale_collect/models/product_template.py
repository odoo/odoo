# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, models
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
        # Filter delivery methods using the same availability rules as at checkout.
        partner_sudo = order_sudo.partner_shipping_id
        if not partner_sudo.country_id:
            country_sudo = website._get_and_cache_current_country()
            if country_sudo:
                partner_sudo = self.env["res.partner"].new({"country_id": country_sudo.id})
        virtual_order_sudo = self.env["sale.order"].new({
            "order_line": [
                Command.create({"product_id": product_sudo.id, "product_uom_qty": quantity})
            ]
        })
        valid_delivery_methods = available_delivery_methods_sudo.available_carriers(
            partner_sudo, virtual_order_sudo
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

        # If Click & Collect is available for this product, prepare the in-store stock data.
        if in_store_dm.available_carriers(partner_sudo, virtual_order_sudo):
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
