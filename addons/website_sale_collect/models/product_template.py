# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request

from odoo.addons.website_sale_collect import utils


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_additionnal_combination_info(self, product_or_template, quantity, date, website):
        """ Override of `website_sale` to add information on whether Click & Collect is enabled and
        on the in-store stock of the product. """
        res = super()._get_additionnal_combination_info(
            product_or_template, quantity, date, website
        )
        order_sudo = request.cart
        if (
            bool(website.sudo().in_store_dm_id)  # Click & Collect is enabled.
            and len(order_sudo.carrier_id.warehouse_ids) > 1
            and product_or_template.is_product_variant
            and product_or_template.is_storable
        ):
            res['show_click_and_collect_availability'] = True
            if (
                order_sudo
                and order_sudo.carrier_id.delivery_type == 'in_store'
                and order_sudo.pickup_location_data
            ):  # Get stock values for the product variant in the selected store.
                res['in_store_stock'] = utils.format_product_stock_values(
                    product_or_template.sudo(), wh_id=order_sudo.pickup_location_data['id']
                )
            else:
                res['in_store_stock'] = utils.format_product_stock_values(
                    product_or_template.sudo(),
                    free_qty=website.sudo()._get_max_in_store_product_available_qty(
                        product_or_template.sudo()
                    )
                )
        return res
