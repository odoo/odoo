# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from itertools import groupby
from odoo.osv.expression import AND

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        if self.config_id.module_pos_restaurant:
            result.append('restaurant.printer')
            if self.config_id.is_table_management:
                result.append('restaurant.floor')
        return result

    def _loader_params_restaurant_floor(self):
        return {
            'search_params': {
                'domain': [('pos_config_id', '=', self.config_id.id)],
                'fields': ['name', 'background_color', 'table_ids', 'sequence'],
                'order': 'sequence',
            },
        }

    def _loader_params_restaurant_table(self):
        return {
            'search_params': {
                'domain': [('active', '=', True)],
                'fields': [
                    'name', 'width', 'height', 'position_h', 'position_v',
                    'shape', 'floor_id', 'color', 'seats', 'active'
                ],
            },
        }

    def _get_pos_ui_restaurant_floor(self, params):
        floors = self.env['restaurant.floor'].search_read(**params['search_params'])
        floor_ids = [floor['id'] for floor in floors]

        table_params = self._loader_params_restaurant_table()
        table_params['search_params']['domain'] = AND([table_params['search_params']['domain'], [('floor_id', 'in', floor_ids)]])
        tables = self.env['restaurant.table'].search(table_params['search_params']['domain'], order='floor_id')
        tables_by_floor_id = {}
        for floor_id, table_group in groupby(tables, key=lambda table: table.floor_id):
            floor_tables = self.env['restaurant.table'].concat(*table_group)
            tables_by_floor_id[floor_id.id] = floor_tables.read(table_params['search_params']['fields'])

        for floor in floors:
            floor['tables'] = tables_by_floor_id.get(floor['id'], [])

        return floors

    def _loader_params_restaurant_printer(self):
        return {
            'search_params': {
                'domain': [('id', 'in', self.config_id.printer_ids.ids)],
                'fields': ['name', 'proxy_ip', 'product_categories_ids', 'printer_type'],
            },
        }
    def _get_pos_ui_restaurant_printer(self, params):
        return self.env['restaurant.printer'].search_read(**params['search_params'])
