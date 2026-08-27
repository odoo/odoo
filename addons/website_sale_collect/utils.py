import math


def format_product_stock_values(product, uom=None, free_qty=None, cart_qty=None, **kwargs):
    """Format product stock values for the location selector.

    :param product.product|product.template product: The product whose stock values to format.
    :param uom.uom uom: The unit of measure to use for the quantity. If not given, the product's.
    :param int free_qty: The free quantity of the product. If not given, calculated from the
                         warehouse.
    :param int cart_qty: The quantity of the product in the cart.
    :param dict kwargs: additional values given for inherited models.
    :return: The formatted product stock values.
    :rtype: dict
    """
    if product.is_product_variant:
        uom = uom or product.uom_id
        # Only available for `product.product` records.
        if free_qty is None:
            free_qty = product._get_free_qty(**kwargs)
        if cart_qty is not None:
            free_qty -= cart_qty or 0
        free_qty_in_uom = max(
            int(product.uom_id._compute_quantity(free_qty, to_unit=uom, rounding_method="DOWN")), 0
        )

        in_stock = free_qty_in_uom > 0
        show_quantity = (
            product.show_availability and in_stock and product.available_threshold >= free_qty
        )
        return {
            "in_stock": in_stock or product.allow_out_of_stock_order,
            "uom_name": uom.name,
            "show_quantity": show_quantity,
            "quantity": free_qty_in_uom,
        }
    return {}


def prepare_cac_widget_data(dm, stock_data, estimated_date):
    """Format the data exposed to the Click & Collect widget for a given delivery method.

    :param delivery.carrier dm: The delivery method.
    :param dict stock_data: The product's formatted stock data for this delivery method.
    :param str estimated_date: The delivery method's estimated delivery date, if any.
    :return: The formatted delivery method values.
    :rtype: dict
    """
    return {
        "stock_data": stock_data,
        "dm_id": dm.id,
        "dm_name": dm.name,
        "dm_type": dm.delivery_type,
        "estimated_date": estimated_date or "",
    }


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
    arcsin = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(math.radians(lat1)) * math.cos(
        math.radians(lat2)
    ) * (math.sin(dlong / 2) * math.sin(dlong / 2))
    return 2 * R * math.atan2(math.sqrt(arcsin), math.sqrt(1 - arcsin))
