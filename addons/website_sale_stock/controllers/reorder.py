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
    def my_orders_reorder(self, order_id, access_token):
        '''Handles reorder functionality when reorder button is clicked.
        Checks if the products are storable and if they are out of stock, and
        stores notification messages in the session.'''
        products = super().my_orders_reorder(order_id, access_token)
        request.session['reorder_notifications'] = []
        for product in products:
            is_storable = (
                request.env['product.product'].browse(product['product_id']).is_storable
            )

            if (
                is_storable
                and not product['combination_info']['allow_out_of_stock_order']
            ):
                free_qty = product['combination_info']['free_qty']
                product_name = product['name']
                if not product['combination_info']['free_qty']:
                    request.session['reorder_notifications'].append(
                        {
                            'type': 'danger',
                            'message': self.env._(
                                "We cannot reorder %(product_name)s as it is out of stock.",
                                product_name=product_name,
                            ),
                        }
                    )
                elif product['combination_info']['free_qty'] < product['qty']:
                    request.session['reorder_notifications'].append(
                        {
                            'type': 'warning',
                            "message": self.env._(
                                "Only %(free_qty)s %(product_name)s %(plural)s available. It has been added to your cart.",
                                free_qty=free_qty,
                                product_name=product_name,
                                plural="are" if free_qty > 1 else "is",
                            ),
                        }
                    )
        return products
