import math


def format_product_stock_values(product, wh_id=None, free_qty=None):
    """Format product stock values for the location selector.

    :param product.product|product.template product: The product whose stock values to format.
    :param int wh_id: The warehouse whose stock to check for the given product.
    :param int free_qty: The free quantity of the product. If not given, calculated from the
                         warehouse.
    :return: The formatted product stock values.
    :rtype: dict
    """
    if product.is_product_variant:  # Only available for `product.product` records.
        if free_qty is None:
            free_qty = product.with_context(warehouse_id=wh_id).free_qty

        in_stock = free_qty > 0
        show_quantity = (
            product.show_availability and in_stock and product.available_threshold >= free_qty
        )
        return {
            'in_stock': in_stock or product.allow_out_of_stock_order,
            'show_quantity': show_quantity,
            'quantity': free_qty,
        }
    return {}


def calculate_partner_distance(partner1, partner2):
    """Calculate the Haversine distance between two partners.

    See https://en.wikipedia.org/wiki/Haversine_formula.

    :param res.partner partner1: The partner to calculate distance from.
    :param res.partner partner2: The partner to calculate distance to.
    :return: The distance between the two partners (in kilometers).
    :rtype: float
    """
    R = 6371  # The radius of Earth.
    lat1, long1 = partner1.partner_latitude, partner1.partner_longitude
    lat2, long2 = partner2.partner_latitude, partner2.partner_longitude
    dlat = math.radians(lat2 - lat1)
    dlong = math.radians(long2 - long1)
    arcsin = (
        math.sin(dlat / 2) * math.sin(dlat / 2)
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
        * (math.sin(dlong / 2) * math.sin(dlong / 2))
    )
    d = 2 * R * math.atan2(math.sqrt(arcsin), math.sqrt(1 - arcsin))

    return d
