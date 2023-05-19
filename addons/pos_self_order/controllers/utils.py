# -*- coding: utf-8 -*-


import werkzeug
from typing import Optional

from odoo.http import request
from odoo.addons.http_routing.models.ir_http import unslug
from odoo.addons.point_of_sale.models.pos_config import PosConfig
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
            ],
            limit=1,
        )
    )


def get_any_pos_config_sudo(access_token: Optional[str] = None) -> Optional[PosConfig]:
    """
    Returns any PosConfig that allows the QR code menu, if there is one
    """
    # TODO: it would be nicer to have: search([("pos_config.allows_qr_menu(access_token)","=", True)])
    # but i don't know how to make it work
    return (
        request.env["pos.config"]
        .sudo()
        .search([])
        .filtered(lambda pos_config: pos_config._allows_qr_menu(access_token))[0]
    )


def get_table_sudo(table_access_token: Optional[str]) -> Optional[RestaurantTable]:
    return table_access_token and (
        request.env["restaurant.table"]
        .sudo()
        .search([("access_token", "=", table_access_token), ("active", "=", True)], limit=1)
    )
