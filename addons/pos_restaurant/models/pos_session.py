# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, Command, api
from odoo.tools import convert
from odoo.osv.expression import OR
import json

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _load_data_params(self, config_id):
        params = super()._load_data_params(config_id)

        if self.config_id.module_pos_restaurant:
            params.update({
                'restaurant.floor': {
                    'domain': [('pos_config_ids', '=', self.config_id.id)],
                    'fields': ['name', 'background_color', 'table_ids', 'sequence', 'floor_background_image'],
                },
                'restaurant.table': {
                    'domain': lambda data: [('active', '=', True), ('floor_id', 'in', [floor['id'] for floor in data['restaurant.floor']])],
                    'fields': [
                        'name', 'width', 'height', 'position_h', 'position_v', 'parent_id',
                        'shape', 'floor_id', 'color', 'seats', 'active'
                    ],
                }
            })
            params['account.fiscal.position']['domain'] = OR([params['account.fiscal.position']['domain'], [('id', '=', self.config_id.takeaway_fp_id.id)]])

        params['pos.order.line']['fields'] += ['note']

        return params

    def get_onboarding_data(self):
        results = super().get_onboarding_data()

        if self.config_id.module_pos_restaurant:
            response = self.load_data(['restaurant.floor', 'restaurant.table'], True)
            results.update(response['data'])

        return results

    @api.model
    def _load_onboarding_data(self):
        super()._load_onboarding_data()
        convert.convert_file(self.env, 'pos_restaurant', 'data/pos_restaurant_onboarding.xml', None, mode='init', kind='data')
        restaurant_config = self.env.ref('pos_restaurant.pos_config_main_restaurant', raise_if_not_found=False)
        if restaurant_config:
            convert.convert_file(self.env, 'pos_restaurant', 'data/pos_restaurant_onboarding_main_config.xml', None, mode='init', kind='data')
            if len(restaurant_config.session_ids.filtered(lambda s: s.state == 'opened')) == 0:
                self.env['pos.session'].create({
                    'config_id': restaurant_config.id,
                    'user_id': self.env.ref('base.user_admin').id,
                })
            convert.convert_file(self.env, 'pos_restaurant', 'data/pos_restaurant_onboarding_open_session.xml', None, mode='init', kind='data')

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
