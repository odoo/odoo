# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.website_sale.controllers.product_configurator import (
    WebsiteSaleProductConfiguratorController,
)
from odoo.addons.website_sale_stock.controllers.utils import _get_stock_data


class WebsiteSaleStockProductConfiguratorController(WebsiteSaleProductConfiguratorController):

    def _get_basic_product_information(self, product_or_template, pricelist, combination, **kwargs):
        """ Override of `website_sale` to append stock data.

        :param product.product|product.template product_or_template: The product for which to seek
            information.
        :param product.pricelist pricelist: The pricelist to use.
        :param product.template.attribute.value combination: The combination of the product.
        :param dict kwargs: Locally unused data passed to `super` and `_get_stock_data`.
        :rtype: dict
        :return: A dict containing data about the specified product.
        """
        basic_product_information = super()._get_basic_product_information(
            product_or_template, pricelist, combination, **kwargs
        )

        if request.is_frontend and product_or_template.is_storable:
            basic_product_information.update(
                _get_stock_data(product_or_template, request.website, **kwargs)
            )
        return basic_product_information
