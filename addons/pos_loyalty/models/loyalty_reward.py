# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
import ast
import json

class LoyaltyReward(models.Model):
    _name = 'loyalty.reward'
    _inherit = ['loyalty.reward', 'pos.load.mixin']

    def _get_discount_product_values(self):
        res = super()._get_discount_product_values()
        for vals in res:
            vals.update({'taxes_id': False})
        return res

    @api.model
    def _load_pos_data_domain(self, data):
        config_id = self.env['pos.config'].browse(data['pos.config']['data'][0]['id'])
        return [('program_id', 'in', config_id._get_program_ids().ids)]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['description', 'program_id', 'reward_type', 'required_points', 'clear_wallet', 'currency_id',
                'discount', 'discount_mode', 'discount_applicability', 'all_discount_product_ids', 'is_global_discount',
                'discount_max_amount', 'discount_line_product_id', 'reward_product_id',
                'multi_product', 'reward_product_ids', 'reward_product_qty', 'reward_product_uom_id', 'reward_product_domain']

    def _load_pos_data(self, data):
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(data['pos.config']['data'][0]['id'])
        rewards = self.search_read(domain, fields, load=False)
        for reward in rewards:
            reward['reward_product_domain'] = self._replace_ilike_with_in(reward['reward_product_domain'])
        return {
            'data': rewards,
            'fields': fields,
        }

    def _replace_ilike_with_in(self, domain_str):
        if domain_str == "null":
            return domain_str

        domain = ast.literal_eval(domain_str)

        for index, condition in enumerate(domain):
            if isinstance(condition, (list, tuple)) and len(condition) == 3:
                field_name, operator, value = condition
                field = self.env['product.product']._fields.get(field_name)

                if field and field.type == 'many2one' and operator in ('ilike', 'not ilike'):
                    comodel = self.env[field.comodel_name]
                    matching_ids = list(comodel._name_search(value, [], operator, limit=None))

                    new_operator = 'in' if operator == 'ilike' else 'not in'
                    domain[index] = [field_name, new_operator, matching_ids]

        return json.dumps(domain)
