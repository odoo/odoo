# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route, Controller
from odoo.tools import groupby


class CatalogController(Controller):

    @route('/sales/catalog/sale_order_lines_info', auth='user', type='json')
    def sale_product_catalog_get_sale_order_lines_info(self, order_id, product_ids, **kwargs):
        """ Returns products information to be shown in the catalog.

        :param int order_id: The sale order, as a `sale.order` id.
        :param list product_ids: The products currently displayed in the product catalog, as a list
                                 of `product.product` ids.
        :rtype: dict
        :return: A dict with the following structure:
            {
                'productId': int
                'quantity': float (optional)
                'price': float
                'readOnly': bool (optional)
            }
        """
        order = request.env['sale.order'].browse(order_id)
        sale_order_line_info = dict()
        for product, lines in groupby(
            order.order_line.filtered(lambda line: not line.display_type),
            lambda line: line.product_id
        ):
            if(product.id not in product_ids):
                continue

            sale_order_line_info[product.id] = request.env['sale.order.line'].browse(
                line.id for line in lines # groupby gives a list and not a recordset
            )._get_catalog_info()

            product_ids.remove(product.id)

        default_data = request.env['sale.order.line']._get_catalog_info()
        default_data['readOnly'] = order._is_readonly()

        sale_order_line_info.update({
            id: {
                **default_data,
                'price': price,
            }
            for id, price in order.pricelist_id._get_products_price(
                quantity=1.0,
                products=request.env['product.product'].browse(product_ids),
                currency=order.currency_id,
                date=order.date_order,
                **kwargs,
            ).items()
        })
        return sale_order_line_info

    @route('/sales/catalog/update_sale_order_line_info', auth='user', type='json')
    def sale_product_catalog_update_sale_order_line_info(
        self, order_id, product_id, quantity, **kwargs
    ):
        """ Update sale order line information on a given sale order for a given product.

        :param int order_id: The sale order, as a `sale.order` id.
        :param int product_id: The product, as a `product.product` id.
        :param float quantity: The quantity selected in the product catalog.
        :return: The unit price price of the product, based on the pricelist of the sale order and
                 the quantity selected.
        :rtype: float
        """
        sol = request.env['sale.order.line'].search([
            ('order_id', '=', order_id), ('product_id', '=', product_id),
        ])
        if sol:
            if quantity != 0:
                sol.product_uom_qty = quantity
            elif sol.order_id.state in ['draft', 'sent']:
                price_unit = sol.order_id.pricelist_id._get_product_price(
                    product=sol.product_id,
                    quantity=1.0,
                    currency=sol.order_id.currency_id,
                    date=sol.order_id.date_order,
                    **kwargs,
                )
                sol.unlink()
                return price_unit
            else:
                sol.product_uom_qty = 0
        elif quantity > 0:
            order = request.env['sale.order'].browse(order_id)
            sol = request.env['sale.order.line'].create({
                'order_id': order.id,
                'product_id': product_id,
                'product_uom_qty': quantity,
                'sequence': ((order.order_line and order.order_line[-1].sequence + 1) or 10),  # put it at the end of the order
            })
        return sol.price_unit
