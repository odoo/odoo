# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid
from typing import Dict, Callable, List, Optional

from odoo import api, fields, models


class RestaurantTable(models.Model):
    _inherit = "restaurant.table"

    identifier = fields.Char(
        "Security Token",
        copy=False,
        required=True,
        default=lambda self: self._get_identifier(),
    )

    def _get_self_order_data(self) -> Dict:
        self.ensure_one()
        return {
            'name': self.name,
            'identifier': self.identifier,
            'floor_name': self.floor_id.name
        }

    @staticmethod
    def _get_identifier():
        return uuid.uuid4().hex[:8]

    @api.model
    def _update_identifier(self):
        tables = self.env["restaurant.table"].search([])
        for table in tables:
            table.identifier = self._get_identifier()
