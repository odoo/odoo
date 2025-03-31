# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route, Controller


class ProductCatalogController(Controller):

    @route('/product/catalog/order_lines_info', auth='user', type='json')
    def product_catalog_get_order_lines_info(self, res_model, order_id, product_ids, **kwargs):
        """ Returns products information to be shown in the catalog.

        :param string res_model: The order model.
        :param int order_id: The order id.
        :param list product_ids: The products currently displayed in the product catalog, as a list
                                 of `product.product` ids.
        :rtype: dict
        :return: A dict with the following structure:
            {
                product.id: {
                    'productId': int
                    'quantity': float (optional)
                    'price': float
                    'readOnly': bool (optional)
                }
            }
        """
        order = request.env[res_model].browse(order_id)
        return order.with_company(order.company_id)._get_product_catalog_order_line_info(
            product_ids, **kwargs,
        )

    @route('/product/catalog/update_order_line_info', auth='user', type='json')
    def product_catalog_update_order_line_info(self, res_model, order_id, product_id, quantity=0, **kwargs):
        """ Update order line information on a given order for a given product.

        :param string res_model: The order model.
        :param int order_id: The order id.
        :param int product_id: The product, as a `product.product` id.
        :return: The unit price price of the product, based on the pricelist of the order and
                 the quantity selected.
        :rtype: float
        """
        order = request.env[res_model].browse(order_id)
        return order.with_company(order.company_id)._update_order_line_info(
            product_id, quantity, **kwargs,
        )
