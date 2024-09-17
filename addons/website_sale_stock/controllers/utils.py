# Part of Odoo. See LICENSE file for full copyright and licensing details.


def _get_stock_data(product_or_template, website, **kwargs):
    """ Return data about the provided product's stock.

    :param product.product|product.template product_or_template: The product for which to get data.
    :param website website: The website from which the request was made.
    :param dict kwargs: Locally unused data passed to `_get_product_available_qty`.
    :rtype: dict
    :return: A dict with the following structure:
        {
            'free_qty': float,
        }
    """
    if not product_or_template.allow_out_of_stock_order:
        available_qty = website._get_product_available_qty(
            product_or_template.sudo(), **kwargs
        ) if product_or_template.is_product_variant else 0
        cart_quantity = product_or_template._get_cart_qty(website)
        return {
            'free_qty': available_qty - cart_quantity,
        }
    return {}
