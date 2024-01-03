# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv.expression import OR
import ast
import json

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _load_data_params(self, config_id):
        params = super()._load_data_params(config_id)
        params['product.product']['fields'].append('all_product_tag_ids')
        params.update({
            'loyalty.program': {
                'domain': [('id', 'in', self.config_id._get_program_ids().ids)],
                'fields': [
                    'name', 'trigger', 'applies_on', 'program_type', 'pricelist_ids', 'date_from',
                    'date_to', 'limit_usage', 'max_usage', 'is_nominative', 'portal_visible',
                    'portal_point_name', 'trigger_product_ids', 'rule_ids', 'reward_ids'
                ],
            },
            'loyalty.rule': {
                'domain': [('program_id', 'in', self.config_id._get_program_ids().ids)],
                'fields': ['program_id', 'valid_product_ids', 'any_product', 'currency_id',
                    'reward_point_amount', 'reward_point_split', 'reward_point_mode',
                    'minimum_qty', 'minimum_amount', 'minimum_amount_tax_mode', 'mode', 'code'],
            },
            'loyalty.reward': {
                'domain': [('program_id', 'in', self.config_id._get_program_ids().ids)],
                'fields': ['description', 'program_id', 'reward_type', 'required_points', 'clear_wallet', 'currency_id',
                    'discount', 'discount_mode', 'discount_applicability', 'all_discount_product_ids', 'is_global_discount',
                    'discount_max_amount', 'discount_line_product_id', 'reward_product_id',
                    'multi_product', 'reward_product_ids', 'reward_product_qty', 'reward_product_uom_id', 'reward_product_domain'],
            },
            'loyalty.card': {
                'domain': lambda data: [('program_id', 'in', [program["id"] for program in data["loyalty.program"]])],
                'fields': ['partner_id', 'code', 'points', 'program_id', 'expiration_date'],
            },
        })
        params['pos.order.line']['fields'] += ['is_reward_line', 'reward_id', 'reward_identifier_code', 'points_cost', 'coupon_id']
        return params

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

    def load_data(self, models_to_load, only_data=False):
        result = super().load_data(models_to_load, only_data)

        # adapt product
        if len(models_to_load) == 0 or 'product.product' in models_to_load:
            product_params = self._load_data_params(self.config_id)['product.product']
            rewards = self.config_id._get_program_ids().reward_ids
            reward_products = rewards.discount_line_product_id | rewards.reward_product_ids
            trigger_products = self.config_id._get_program_ids().filtered(lambda p: p.program_type == 'ewallet').trigger_product_ids

            products = list(set(reward_products.ids + trigger_products.ids) - set(product['id'] for product in result['data']['product.product']))
            products = self.env['product.product'].search_read([('id', 'in', products)], fields=product_params['fields'], load=False)
            self._process_pos_ui_product_product(products)

            result['custom']['pos_special_products_ids'].extend(
                [product.id for product in reward_products if product.id not in [p["id"] for p in result['data']['product.product']]]
            )
            result['data']['product.product'].extend(products)

        # adapt loyalty
        if len(models_to_load) == 0 or 'loyalty.reward' in models_to_load:
            for reward in result['data']['loyalty.reward']:
                reward['reward_product_domain'] = self._replace_ilike_with_in(reward['reward_product_domain'])

        return result
