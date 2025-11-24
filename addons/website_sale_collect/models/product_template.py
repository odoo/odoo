# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request

from odoo.addons.website_sale_collect import utils


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _get_additionnal_combination_info(self, product_or_template, quantity, uom, date, website):
        """Override of `website_sale` to add information on whether Click & Collect is enabled and
        on the stock of the product."""
        res = super()._get_additionnal_combination_info(
            product_or_template, quantity, uom, date, website
        )
        in_store_dm = website.sudo().in_store_dm_id
        if (
            bool(in_store_dm)  # Click & Collect is enabled.
            and product_or_template.is_product_variant
        ):
            product_sudo = product_or_template.sudo()  # To read the stock values when public user.
            order_sudo = request.cart
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
            valid_delivery_methods = available_delivery_methods_sudo.filtered(
                lambda dm: not (dm.excluded_tag_ids & product_tags)
            )
            if valid_delivery_methods:
                res["delivery_stock_data"] = utils.format_product_stock_values(
                    product_sudo, uom=uom, cart_qty=cart_qty
                )
            else:
                res["delivery_stock_data"] = {}

            # If C&C not excluded via tags, prepare the in-store stock data.
            if not (in_store_dm.excluded_tag_ids & product_or_template.all_product_tag_ids):
                if (
                    order_sudo
                    and order_sudo.carrier_id.delivery_type == "in_store"
                    and order_sudo.partner_shipping_id.pickup_location_data
                ):  # Get stock values for the product variant in the selected store.
                    res["in_store_stock_data"] = utils.format_product_stock_values(
                        product_sudo,
                        uom=uom,
                        wh_id=order_sudo.partner_shipping_id.pickup_location_data["id"],
                        cart_qty=cart_qty,
                    )
                else:
                    res["in_store_stock_data"] = utils.format_product_stock_values(
                        product_sudo,
                        uom=uom,
                        free_qty=website.sudo()._get_max_in_store_product_available_qty(
                            product_sudo
                        ),
                        cart_qty=cart_qty,
                    )
            else:
                # In-store dm is not compatible with the product.
                res["in_store_stock_data"] = {}

        return res
