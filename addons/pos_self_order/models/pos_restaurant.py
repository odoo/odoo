# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid
from typing import Dict, Callable, List, Optional

from odoo import api, fields, models


class RestaurantFloor(models.Model):
    _inherit = "restaurant.floor"

    def _get_data_for_qr_codes_page(self, url: Callable):
        return [
            {
                "name": floor.name,
                "tables": floor.table_ids.filtered("active")._get_data_for_qr_codes_page(url),
            }
            for floor in self
        ]


class RestaurantTable(models.Model):
    _inherit = "restaurant.table"

    access_token = fields.Char(
        "Security Token",
        copy=False,
        required=True,
        readonly=True,
        default=lambda self: self._get_access_token(),
    )

    @staticmethod
    def _get_access_token():
        return uuid.uuid4().hex[:8]

    def _get_self_order_data(self) -> Dict:
        self.ensure_one()
        return self.read(["name", "access_token"])[0]

    def _get_data_for_qr_codes_page(self, url: Callable[[Optional[int]], str]) -> List[Dict]:
        return [
            {
                "access_token": table.access_token,
                "id": table.id,
                "name": table.name,
                "url": url(table.id),
            }
            for table in self
        ]

    @api.model
    def _update_access_token(self):
        """
        We define a new access token field in this file.
        There might already be databases that have restaurant.table records.
        They will now also get an access token each; the problem is that
        because of the way `default` values work, all those tables that
        exist in the db will get the same access token.
        This method will be ran at the moment the pos_self_order module
        is installed and will thus make sure that every record has a
        different access token.
        """
        tables = self.env["restaurant.table"].search([])
        for table in tables:
            table.access_token = self._get_access_token()
