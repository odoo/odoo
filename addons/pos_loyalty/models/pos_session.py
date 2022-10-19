# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv.expression import OR

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        if self.config_id.all_program_ids:
            result += [
                'loyalty.program',
                'loyalty.rule',
                'loyalty.reward',
            ]
        return result

    def _loader_params_loyalty_program(self):
        return {
            'search_params': {
                'domain': [('id', 'in', self.config_id.all_program_ids.ids)],
                'fields': ['name', 'trigger', 'applies_on', 'program_type', 'date_to',
                    'limit_usage', 'max_usage', 'is_nominative', 'portal_point_name'],
            },
        }

    def _loader_params_loyalty_rule(self):
        return {
            'search_params': {
                'domain': [('program_id', 'in', self.config_id.all_program_ids.ids)],
                'fields': ['program_id', 'valid_product_ids', 'any_product', 'currency_id',
                    'reward_point_amount', 'reward_point_split', 'reward_point_mode',
                    'minimum_qty', 'minimum_amount', 'minimum_amount_tax_mode', 'mode', 'code'],
            }
        }

    def _loader_params_loyalty_reward(self):
        return {
            'search_params': {
                'domain': [('program_id', 'in', self.config_id.all_program_ids.ids)],
                'fields': ['description', 'program_id', 'reward_type', 'required_points', 'clear_wallet', 'currency_id',
                    'discount', 'discount_mode', 'discount_applicability', 'all_discount_product_ids', 'is_global_discount',
                    'discount_max_amount', 'discount_line_product_id',
                    'multi_product', 'reward_product_ids', 'reward_product_qty', 'reward_product_uom_id'],
            }
        }

    def _get_pos_ui_loyalty_program(self, params):
        return self.env['loyalty.program'].search_read(**params['search_params'])

    def _get_pos_ui_loyalty_rule(self, params):
        return self.env['loyalty.rule'].search_read(**params['search_params'])

    def _get_pos_ui_loyalty_reward(self, params):
        return self.env['loyalty.reward'].search_read(**params['search_params'])

    def _get_pos_ui_res_partner(self, params):
        result = super()._get_pos_ui_res_partner(params)
        # In order to make loyalty programs work offline we load the partner's point into
        # a non-existant field 'loyalty_points'.
        if self.config_id.loyalty_program_id:
            # collect ids in a list, group by id and default points to 0
            partner_ids = []
            res_by_id = {}
            for res in result:
                partner_ids.append(res['id'])
                res_by_id[res['id']] = res
                res['loyalty_points'] = 0
                res['loyalty_card_id'] = False
            # Direct query to avoid loading loyalty cards in the cache for no reason.
            # There is no context where we would need to flush.
            query = self.env['loyalty.card']._search(
                [('program_id', '=', self.config_id.loyalty_program_id.id), ('partner_id', 'in', partner_ids)]
            )
            if query:
                query_str, params = query.select('id', 'partner_id', 'points')
                self.env.cr.execute(query_str, params)
                for res in self.env.cr.dictfetchall():
                    # The result of where_calc also includes partner_id is null.
                    if not res.get('partner_id'):
                        continue
                    res_by_id[res['partner_id']]['loyalty_points'] = res['points']
                    res_by_id[res['partner_id']]['loyalty_card_id'] = res['id']
        return result

    def _loader_params_product_product(self):
        result = super(PosSession, self)._loader_params_product_product()
        config = self.config_id
        if config.all_program_ids:
            programs = config.all_program_ids
            rewards = programs.reward_ids
            products = (programs.rule_ids.valid_product_ids | rewards.discount_line_product_id) |\
                (rewards.all_discount_product_ids | rewards.reward_product_ids)
            result['search_params']['domain'] = OR([result['search_params']['domain'], [('id', 'in', products.ids)]])
        return result
