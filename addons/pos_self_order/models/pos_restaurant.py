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

    @staticmethod
    def _get_identifier():
        return uuid.uuid4().hex[:8]

    @api.model
    def _update_identifier(self):
        tables = self.env["restaurant.table"].search([])
        for table in tables:
            table.identifier = self._get_identifier()

    @api.model
    def _load_pos_self_data_fields(self, config):
        return ['table_number', 'identifier', 'floor_id']

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        return [('floor_id', 'in', [floor['id'] for floor in data['restaurant.floor']])]


class RestaurantFloor(models.Model):
    _inherit = "restaurant.floor"

    @api.model
    def _load_pos_self_data_fields(self, config):
        return ['name', 'table_ids']

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        return [('id', 'in', config.floor_ids.ids)]
