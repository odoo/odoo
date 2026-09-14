from typing import NamedTuple

from odoo import fields

from ..tools import debug_log as dbg


class ProcurementException(Exception):
    def __init__(self, procurement_exceptions):
        dbg.logic.debug(
            "ProcurementException raised for %d procurement(s): %s",
            len(procurement_exceptions),
            dbg.lazy(
                lambda: " | ".join(
                    str(error) for _procurement, error in procurement_exceptions
                ),
            ),
        )
        self.procurement_exceptions = procurement_exceptions


class Procurement(NamedTuple):
    product_id: fields.Many2one
    product_qty: fields.Float
    product_uom_id: fields.Many2one
    location_id: fields.Many2one
    name: fields.Char
    origin: fields.Char
    company_id: fields.Many2one
    values: dict
