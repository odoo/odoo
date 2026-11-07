# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, Command, api
from odoo.tools import convert
from itertools import groupby
from odoo.osv.expression import AND
import json

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        if self.config_id.module_pos_restaurant:
            result.append('restaurant.floor')
        return result

    def _loader_params_restaurant_floor(self):
        return {
            'search_params': {
                'domain': [('pos_config_ids', '=', self.config_id.id)],
                'fields': ['name', 'background_color', 'table_ids', 'sequence'],
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

    def get_pos_ui_restaurant_floor(self):
        return self._get_pos_ui_restaurant_floor(self._loader_params_restaurant_floor())

    def get_onboarding_data(self):
        results = super().get_onboarding_data()
        if self.config_id.module_pos_restaurant:
            results.update({
                'restaurant.floor': self._load_model('restaurant.floor'),
            })
        return results

    @api.model
    def _load_onboarding_data(self):
        super()._load_onboarding_data()
        convert.convert_file(self.env, 'pos_restaurant', 'data/pos_restaurant_onboarding.xml', None, mode='init', noupdate=True, kind='data')
        restaurant_config = self.env.ref('pos_restaurant.pos_config_main_restaurant', raise_if_not_found=False)
        if restaurant_config:
            convert.convert_file(self.env, 'pos_restaurant', 'data/pos_restaurant_onboarding_main_config.xml', None, mode='init', noupdate=True, kind='data')
            if len(restaurant_config.session_ids.filtered(lambda s: s.state == 'opened')) == 0:
                self.env['pos.session'].create({
                    'config_id': restaurant_config.id,
                    'user_id': self.env.ref('base.user_admin').id,
                })
            convert.convert_file(self.env, 'pos_restaurant', 'data/pos_restaurant_onboarding_open_session.xml', None, mode='init', noupdate=True, kind='data')

    def _after_load_onboarding_data(self):
        super()._after_load_onboarding_data()
        configs = self.config_id.filtered('module_pos_restaurant')
        if configs:
            configs.with_context(bypass_categories_forbidden_change=True).write({
                'limit_categories': True,
                'iface_available_categ_ids': [Command.link(self.env.ref('pos_restaurant.food').id), Command.link(self.env.ref('pos_restaurant.drinks').id)]
            })

    @api.model
    def _set_last_order_preparation_change(self, order_ids):
        for order_id in order_ids:
            order = self.env['pos.order'].browse(order_id)
            last_order_preparation_change = {}
            for orderline in order['lines']:
                last_order_preparation_change[orderline.uuid + " - "] = {
                    "line_uuid": orderline.uuid,
                    "name": orderline.full_product_name,
                    "note": "",
                    "product_id": orderline.product_id.id,
                    "quantity": orderline.qty,
                    "attribute_value_ids": orderline.attribute_value_ids.ids,
                }
            order.write({'last_order_preparation_change': json.dumps(last_order_preparation_change)})
