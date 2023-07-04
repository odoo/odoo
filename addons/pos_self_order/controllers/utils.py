# -*- coding: utf-8 -*-


import werkzeug
from typing import Optional

from odoo.http import request
from odoo.addons.pos_self_order.models.pos_config import PosConfig

def get_any_pos_config_sudo() -> PosConfig:
    """
    Returns a PosConfig that allows the QR code menu, if there is one,
    or raises a NotFound otherwise
    """
    return (
        request.env["pos.config"].sudo().search([("self_order_view_mode", "=", True)], limit=1)
    ) or _raise(werkzeug.exceptions.NotFound())


def get_table_sudo(identifier):
    return identifier and (
        request.env["restaurant.table"]
        .sudo()
        .search([("identifier", "=", identifier), ("active", "=", True)], limit=1)
    )


def _raise(e):
    raise e
