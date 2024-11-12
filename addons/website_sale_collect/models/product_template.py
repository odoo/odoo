# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.website_sale_collect import utils


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_additionnal_combination_info(self, product_or_template, quantity, date, website):
        """ Override of `website_sale` to add information on whether Click & Collect is enabled and
        on the in-store stock of the product. """
        res = super()._get_additionnal_combination_info(
            product_or_template, quantity, date, website
        )
        if (
            bool(website.sudo().in_store_dm_id)  # Click & Collect is enabled.
            and product_or_template.is_product_variant
            and product_or_template.is_storable
        ):
            res['show_click_and_collect_availability'] = True
            order_sudo = website.sale_get_order()
            if (
                order_sudo
                and order_sudo.carrier_id.delivery_type == 'in_store'
                and order_sudo.pickup_location_data
            ):  # Get stock values for the product variant in the selected store.
                res['in_store_stock'] = utils.format_product_stock_values(
                    product_or_template.sudo(), order_sudo.pickup_location_data['id']
                )
            else:
                res['in_store_stock'] = {}
        return res
