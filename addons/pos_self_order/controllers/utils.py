# -*- coding: utf-8 -*-


import werkzeug
from typing import Optional

from odoo.http import request
from odoo.addons.http_routing.models.ir_http import unslug
from odoo.addons.pos_self_order.models.pos_config import PosConfig
from odoo.addons.pos_restaurant.models.pos_restaurant import RestaurantTable


def get_pos_config_sudo(pos_config_name: str) -> PosConfig:
    """
    Returns the PosConfig if pos_config_id exist and the pos is configured to allow the menu to be viewed online.
    If not, it raises a NotFound
    :param pos_config_name: The name of the pos config. Can be the id or the slug. ex: 3 or Bar-3
    """
    return (
        request.env["pos.config"]
        .sudo()
        .search(
            [
                ("id", "=", unslug(str(pos_config_name))[1]),
                ("self_order_view_mode", "=", True),
            ],
            limit=1,
        )
    ) or _raise(werkzeug.exceptions.NotFound())


def get_any_pos_config_sudo() -> PosConfig:
    """
    Returns a PosConfig that allows the QR code menu, if there is one,
    or raises a NotFound otherwise
    """
    return (
        request.env["pos.config"].sudo().search([("self_order_view_mode", "=", True)], limit=1)
    ) or _raise(werkzeug.exceptions.NotFound())


def get_table_sudo(access_token: Optional[str]) -> Optional[RestaurantTable]:
    return access_token and (
        request.env["restaurant.table"]
        .sudo()
        .search([("access_token", "=", access_token), ("active", "=", True)], limit=1)
    )


def _raise(e):
    raise e
