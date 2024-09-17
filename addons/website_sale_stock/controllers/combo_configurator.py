# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.website_sale.controllers.combo_configurator import (
    WebsiteSaleComboConfiguratorController,
)
from odoo.addons.website_sale_stock.controllers.utils import _get_stock_data


class WebsiteSaleStockComboConfiguratorController(WebsiteSaleComboConfiguratorController):

    def _get_combo_item_product_data(self, product, selected_combo_item, **kwargs):
        """ Override of `website_sale` to append stock data.

        :param product.product product: The product for which to get data.
        :param dict selected_combo_item: The selected combo item, in the following format:
            {
                'id': int,
                'no_variant_ptav_ids': list(int),
                'custom_ptavs': list({
                    'id': int,
                    'value': str,
                }),
            }
        :param dict kwargs: Locally unused data passed to `super` and `_get_stock_data`.
        :rtype: dict
        :return: A dict containing data about the specified product.
        """
        product_data = super()._get_combo_item_product_data(product, selected_combo_item, **kwargs)

        if request.is_frontend and product.is_storable:
            product_data.update(_get_stock_data(product, request.website, **kwargs))
        return product_data
