# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from odoo.addons.sale.controllers.catalog import CatalogController


class CatalogControllerDelivery(CatalogController):

    @route()
    def sale_product_catalog_update_sale_order_line_info(
        self, order_id, product_id, quantity, **kwargs
    ):
        """ Override of `sale` to recompute the delivery prices.

        :param int order_id: The sale order, as a `sale.order` id.
        :param int product_id: The product, as a `product.product` id.
        :param float quantity: The quantity selected in the product catalog.
        :return: The unit price price of the product, based on the pricelist of the sale order and
                 the quantity selected.
        :rtype: float
        """
        price_unit = super().sale_product_catalog_update_sale_order_line_info(
            order_id, product_id, quantity, **kwargs
        )
        order = request.env['sale.order'].browse(order_id)
        if order:
            order.onchange_order_line()
        return price_unit
