# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv.expression import OR

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        if self.config_id._get_program_ids():
            result += [
                'loyalty.program',
                'loyalty.rule',
                'loyalty.reward',
            ]
        return result

    def _loader_params_loyalty_program(self):
        return {
            'search_params': {
                'domain': [('id', 'in', self.config_id._get_program_ids().ids)],
                'fields': ['name', 'trigger', 'applies_on', 'program_type', 'date_to',
                    'limit_usage', 'max_usage', 'is_nominative', 'portal_visible', 'portal_point_name', 'trigger_product_ids'],
            },
        }

    def _loader_params_loyalty_rule(self):
        return {
            'search_params': {
                'domain': [('program_id', 'in', self.config_id._get_program_ids().ids)],
                'fields': ['program_id', 'valid_product_ids', 'any_product', 'currency_id',
                    'reward_point_amount', 'reward_point_split', 'reward_point_mode',
                    'minimum_qty', 'minimum_amount', 'minimum_amount_tax_mode', 'mode', 'code'],
            }
        }

    def _loader_params_loyalty_reward(self):
        return {
            'search_params': {
                'domain': [('program_id', 'in', self.config_id._get_program_ids().ids)],
                'fields': ['description', 'program_id', 'reward_type', 'required_points', 'clear_wallet', 'currency_id',
                    'discount', 'discount_mode', 'discount_applicability', 'all_discount_product_ids', 'is_global_discount',
                    'discount_max_amount', 'discount_line_product_id',
                    'multi_product', 'reward_product_ids', 'reward_product_qty', 'reward_product_uom_id', 'reward_product_domain'],
            }
        }

    def _get_pos_ui_loyalty_program(self, params):
        return self.env['loyalty.program'].search_read(**params['search_params'])

    def _get_pos_ui_loyalty_rule(self, params):
        return self.env['loyalty.rule'].search_read(**params['search_params'])

    def _get_pos_ui_loyalty_reward(self, params):
        return self.env['loyalty.reward'].search_read(**params['search_params'])

    def _get_pos_ui_product_product(self, params):
        result = super()._get_pos_ui_product_product(params)
        rewards = self.config_id._get_program_ids().reward_ids
        products = rewards.discount_line_product_id | rewards.reward_product_ids
        products = self.env['product.product'].search_read([('id', 'in', products.ids)], fields=params['search_params']['fields'])
        self._process_pos_ui_product_product(products)
        result.extend(products)
        return result

    def _get_pos_ui_res_partner(self, params):
        partners = super()._get_pos_ui_res_partner(params)
        self._set_loyalty_cards(partners)
        return partners

    def get_pos_ui_res_partner_by_params(self, custom_search_params):
        partners = super().get_pos_ui_res_partner_by_params(custom_search_params)
        self._set_loyalty_cards(partners)
        return partners

    def _set_loyalty_cards(self, partners):
        # Map partner_id to its loyalty cards from all loyalty programs.
        loyalty_programs = self.config_id._get_program_ids().filtered(lambda p: p.program_type == 'loyalty')
        loyalty_card_fields = ['points', 'code', 'program_id']
        partner_id_to_loyalty_card = {}
        for group in self.env['loyalty.card'].read_group(
            domain=[('partner_id', 'in', [p['id'] for p in partners]), ('program_id', 'in', loyalty_programs.ids)],
            fields=[f"{field_name}:array_agg" for field_name in loyalty_card_fields] + ["ids:array_agg(id)"],
            groupby=['partner_id']
        ):
            loyalty_cards = {}
            for i in range(group['partner_id_count']):
                loyalty_cards[group['ids'][i]] = {field_name: group[field_name][i] for field_name in loyalty_card_fields}
            partner_id_to_loyalty_card[group['partner_id'][0]] = loyalty_cards

        # Assign loyalty cards to each partner to load.
        for partner in partners:
            partner['loyalty_cards'] = partner_id_to_loyalty_card.get(partner['id'], {})

        return partners

    def _pos_data_process(self, loaded_data):
        super()._pos_data_process(loaded_data)

        # Additional post processing to link gift card and ewallet programs
        # to their rules' products.
        # Important because points from their products are only counted once.
        product_id_to_program_ids = {}
        for program in self.config_id._get_program_ids():
            if program.program_type in ['gift_card', 'ewallet']:
                for product in program.trigger_product_ids:
                    product_id_to_program_ids.setdefault(product['id'], [])
                    product_id_to_program_ids[product['id']].append(program['id'])

        loaded_data['product_id_to_program_ids'] = product_id_to_program_ids
        product_product_fields = self.env['product.product'].fields_get(self._loader_params_product_product()['search_params']['fields'])
        loaded_data['field_types'] = {
            'product.product': {f:v['type'] for f, v in product_product_fields.items()}
        }

    def _loader_params_product_product(self):
        params = super()._loader_params_product_product()
        # this is usefull to evaluate reward domain in frontend
        params['search_params']['fields'].append('all_product_tag_ids')
        return params
