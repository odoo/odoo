# Part of Odoo. See LICENSE file for full copyright and licensing details.

class DeliveryPackage:
    """ Each provider need similar information about its packages. """
    def __init__(self, commodities, weight, package_type, name=None, total_cost=0, currency=None, picking=False, order=False):
        """ The UOMs are based on the config parameters, which is very convenient:
        we do not need to keep those stored."""
        self.picking_id = picking
        self.order_id = order
        self.company_id = order and order.company_id or picking and picking.company_id
        self.commodities = commodities or []  # list of DeliveryCommodity objects
        self.weight = weight
        self.dimension = {
            'length': package_type.packaging_length,
            'width': package_type.width,
            'height': package_type.height
        }
        self.packaging_type = package_type.shipper_package_code or False
        self.name = name
        self.total_cost = total_cost
        self.currency_id = currency


class DeliveryCommodity:
    """ Commodities information are needed for Commercial invoices with each provider. """
    def __init__(self, product, amount, monetary_value, country_of_origin):
        self.product_id = product
        self.qty = amount
        self.monetary_value = monetary_value  # based on company currency
        self.country_of_origin = country_of_origin
