# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request

from odoo.addons.website_sale import utils


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _get_additional_combination_info(
        self, product_or_template, quantity, uom, website, pricelist, fiscal_position
    ):
        """Override of `website_sale` to add information on whether Click & Collect is enabled and
        on the stock of the product."""
        res = super()._get_additional_combination_info(
            product_or_template, quantity, uom, website, pricelist, fiscal_position
        )
        in_store_dm = website.sudo().in_store_dm_id
        if (
            bool(in_store_dm)  # Click & Collect is enabled.
            and product_or_template.is_product_variant
            and product_or_template.is_storable
        ):
            product_sudo = product_or_template.sudo()  # To read the stock values when public user.
            res.update(self._prepare_in_store_availability_values(product_sudo, website))

        return res

    def _prepare_delivery_availability_values(self, product, website, uom, /, **kwargs):
        return super()._prepare_delivery_availability_values(
            product, website, uom, in_store=False, **kwargs
        )

    def _prepare_in_store_availability_values(self, product_sudo, website, *, uom=None, **kwargs):
        values = {"uom_id": uom and uom.id, "in_store_stock_data": {}}

        available_in_store_dm = website.sudo().in_store_dm_id.filtered_domain(
            website._get_available_delivery_methods_domain(product=product_sudo, **kwargs)
        )
        if not available_in_store_dm:
            return values

        order_sudo = (
            request.cart
            if (request and hasattr(request, "cart"))
            else self.env["sale.order"].sudo()
        )
        if (
            order_sudo
            and order_sudo.carrier_id.delivery_type == "in_store"
            and order_sudo.partner_shipping_id.pickup_location_data
        ):  # Get stock values for the product variant in the selected store.
            values["in_store_stock_data"].update(
                utils.format_product_stock_values(
                    product_sudo,
                    uom,
                    warehouse_id=order_sudo.partner_shipping_id.pickup_location_data["id"],
                )
            )
        else:
            values["in_store_stock_data"].update(
                utils.format_product_stock_values(
                    product_sudo,
                    uom,
                    free_qty=website.sudo()._get_max_in_store_product_available_qty(product_sudo),
                )
            )

        return values
