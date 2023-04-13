# -*- coding: utf-8 -*-


import werkzeug
from typing import List

from odoo import http
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import unslug
from odoo.addons.pos_self_order.models.pos_config import PosConfig
from odoo.addons.pos_restaurant.models.pos_restaurant import RestaurantTable


class PosSelfOrderUtils(http.Controller):
    def _get_pos_config_sudo(self, pos_config_name: str) -> PosConfig:
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
        ) or _raise(werkzeug.exceptions.NotFound)

    def _get_any_pos_config_sudo(self) -> PosConfig:
        """
        Returns a PosConfig that allows the QR code menu, if there is one,
        or raises a NotFound otherwise
        """
        return (
            request.env["pos.config"].sudo().search([("self_order_view_mode", "=", True)], limit=1)
        ) or _raise(werkzeug.exceptions.NotFound)

    def _get_table_sudo(self, table_access_token: str) -> RestaurantTable:
        """
        This function finds the restaurant.table record based on the access_token
        :return: the restaurant.table object
        """
        return table_access_token and (
            request.env["restaurant.table"]
            .sudo()
            .search([("access_token", "=", table_access_token), ("active", "=", True)], limit=1)
        )

    def _get_product_uniqueness_keys(self) -> List[str]:
        """ """
        return ["product_id", "description", "customer_note"]


def _raise(e):
    raise e
