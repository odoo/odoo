# Part of Odoo. See LICENSE file for full copyright and licensing details.


def gmc_format_price(price, currency):
    return f"{currency.round(price)} {currency.name}"


def format_product_stock_values(product, uom, free_qty=None, **kwargs):
    """Format product stock values for the location selector.

    :param product.product product: The product whose stock values to format.
    :param uom.uom uom: The unit of measure to use for the quantity.
    :param int free_qty: The free quantity of the product. If not given, calculated using
        :meth:`_get_free_qty`.
    :param dict kwargs: Additional arguments forwarded to :meth:`_get_free_qty`.
    :return: The formatted product stock values. Schema::

        {
            "in_stock": bool,
            "show_quantity": bool,
            "quantity": float,
        }
    :rtype: dict
    """
    if free_qty is None:
        free_qty = product._get_free_qty(**kwargs)

    free_qty_in_uom = max(
        int(product.uom_id._compute_quantity(free_qty, to_unit=uom, rounding_method="DOWN")), 0
    )
    in_stock = free_qty_in_uom > 0
    show_quantity = (
        product.show_availability and in_stock and product.available_threshold >= free_qty
    )
    return {
        "in_stock": in_stock or product.allow_out_of_stock_order,
        "show_quantity": show_quantity,
        "quantity": free_qty_in_uom,
    }
