# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers import reorder
from odoo.http import request, route


class CustomerPortal(reorder.CustomerPortal):

    def _sale_reorder_get_line_context(self):
        return {
            **super()._sale_reorder_get_line_context(),
            'website_sale_stock_get_quantity': True,
        }

    @route()
    def my_orders_reorder_modal_content(self, order_id, access_token):
        result = super().my_orders_reorder_modal_content(order_id, access_token)
        for product in result['products']:
            product['is_storable'] = request.env['product.product'].browse(product['product_id']).is_storable
        return result
