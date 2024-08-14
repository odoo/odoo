# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.website_sale.controllers.product_configurator import (
    WebsiteSaleProductConfiguratorController,
)


class WebsiteSaleStockProductConfiguratorController(WebsiteSaleProductConfiguratorController):

    def _get_basic_product_information(self, product_or_template, pricelist, combination, **kwargs):
        """ Override of `website_sale` to append stock data.

        :param product.product|product.template product_or_template: The product for which to seek
            information.
        :param product.pricelist pricelist: The pricelist to use.
        :param product.template.attribute.value combination: The combination of the product.
        :param dict kwargs: Locally unused data passed to `super` and `_get_product_available_qty`.
        :rtype: dict
        :return: A dict with the following structure:
            {
                ...  # fields from `super`.
                'is_storable': bool,
                'allow_out_of_stock_order': bool,
                'free_qty': float,
            }
        """
        basic_product_information = super()._get_basic_product_information(
            product_or_template, pricelist, combination, **kwargs
        )

        if request.is_frontend and product_or_template.is_storable:
            basic_product_information.update({
                'is_storable': product_or_template.is_storable,
                'allow_out_of_stock_order': product_or_template.allow_out_of_stock_order,
                'free_qty': request.website._get_product_available_qty(
                    product_or_template.sudo(), **kwargs
                ) if product_or_template.is_product_variant else 0
            })
        return basic_product_information
