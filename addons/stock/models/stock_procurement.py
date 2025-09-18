from typing import NamedTuple

from odoo import fields


class ProcurementException(Exception):
    """An exception raised by StockRule `run` containing all the faulty
    procurements.
    """

    def __init__(self, procurement_exceptions):
        """:param procurement_exceptions: a list of tuples containing the faulty
        procurement and their error messages
        :type procurement_exceptions: list
        """
        self.procurement_exceptions = procurement_exceptions


class Procurement(NamedTuple):
    """Procurement data structure representing a need for products at a location.

    A procurement represents a request for a specific quantity of a product to be
    available at a destination location. The stock rules system uses procurements
    to trigger the creation of stock moves, purchase orders, or manufacturing orders.
    """
    product_id: fields.Many2one
    product_qty: fields.Float
    product_uom: fields.Many2one
    location_id: fields.Many2one
    name: fields.Char
    origin: fields.Char
    company_id: fields.Many2one
    values: dict
