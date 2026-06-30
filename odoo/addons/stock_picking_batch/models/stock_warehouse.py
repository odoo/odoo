# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    def _get_picking_type_create_values(self, max_sequence):
        data, next_sequence = super()._get_picking_type_create_values(max_sequence)
        updatable_types = {k: v for (k, v) in data.items() if v.get('code') in ('incoming', 'outgoing')}
        for picking_type in updatable_types.values():
            picking_type.update({
                'auto_batch': True,
                'batch_group_by_partner': True,
            })
        return data, next_sequence
