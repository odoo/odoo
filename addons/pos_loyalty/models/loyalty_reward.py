# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.fields import Domain

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
    def _load_pos_data_domain(self, data, config):
        reward_product_tag_domain = [
            ('reward_product_tag_id', '!=', False),
            '|',
            ('reward_product_tag_id.product_template_ids.active', '=', True),
            ('reward_product_tag_id.product_product_ids.active', '=', True),
        ]
        return Domain.AND([
            [('program_id', 'in', config._get_program_ids().ids)],
            Domain.OR([
                [('reward_type', '!=', 'product')],
                [('reward_product_id.active', '=', True)],
                reward_product_tag_domain,
            ]),
        ])

    @api.model
    def _load_pos_data_fields(self, config):
        return ['description', 'program_id', 'reward_type', 'required_points', 'clear_wallet', 'currency_id',
                'discount', 'discount_mode', 'discount_applicability', 'all_discount_product_ids', 'is_global_discount',
                'discount_max_amount', 'discount_line_product_id', 'reward_product_id',
                'multi_product', 'reward_product_ids', 'reward_product_qty', 'reward_product_uom_id', 'reward_product_domain']

    @api.model
    def _load_pos_data_read(self, records, config):
        read_records = super()._load_pos_data_read(records, config)
        
        # Batch transformation of ilike to in to avoid N-search problem
        keywords_by_comodel = {} # {comodel_name: {keyword}}
        rewards_with_domain = []
        
        for reward in read_records:
            domain_str = reward.get('reward_product_domain')
            if domain_str and domain_str != "null":
                try:
                    domain = json.loads(domain_str)
                    reward['_parsed_domain'] = domain
                    rewards_with_domain.append(reward)
                    
                    for condition in self._parse_domain(domain).values():
                        field_name, operator, value = condition
                        field = self.env['product.product']._fields.get(field_name)
                        if field and field.type == 'many2one' and operator in ('ilike', 'not ilike'):
                            comodel_name = field.comodel_name
                            keywords_by_comodel.setdefault(comodel_name, set()).add(value)
                except Exception:
                    continue

        # Execute batched searches
        results_by_comodel_keyword = {} # {comodel_name: {keyword: [ids]}}
        for comodel_name, keywords in keywords_by_comodel.items():
            comodel = self.env[comodel_name]
            results_by_comodel_keyword[comodel_name] = {}
            for kw in keywords:
                # We still search per keyword because display_name ilike is usually keyword-specific
                # but we could further optimize if needed. At least we only search UNIQUE keywords.
                results_by_comodel_keyword[comodel_name][kw] = list(comodel._search([('display_name', 'ilike', kw)]))

        # Update domains
        for reward in rewards_with_domain:
            domain = reward['_parsed_domain']
            domain_changed = False
            for index, condition in self._parse_domain(domain).items():
                field_name, operator, value = condition
                field = self.env['product.product']._fields.get(field_name)
                if field and field.type == 'many2one' and operator in ('ilike', 'not ilike'):
                    matching_ids = results_by_comodel_keyword.get(field.comodel_name, {}).get(value, [])
                    new_operator = 'in' if operator == 'ilike' else 'not in'
                    domain[index] = [field_name, new_operator, matching_ids]
                    domain_changed = True
            
            if domain_changed:
                reward['reward_product_domain'] = json.dumps(domain)
            del reward['_parsed_domain']

        return read_records

    def _get_reward_product_domain_fields(self, config):
        fields = set()
        search_domain = [('program_id', 'in', config._get_program_ids().ids)]
        domains = self.search_read(search_domain, fields=['reward_product_domain'], load=False)
        for domain in filter(lambda d: d['reward_product_domain'] != "null", domains):
            domain = json.loads(domain['reward_product_domain'])
            for condition in self._parse_domain(domain).values():
                field_name, _, _ = condition
                fields.add(field_name)
        return fields


    def _parse_domain(self, domain):
        parsed_domain = {}

        for index, condition in enumerate(domain):
            if isinstance(condition, (list, tuple)) and len(condition) == 3:
                parsed_domain[index] = condition
        return parsed_domain

    def unlink(self):
        if len(self) == 1 and self.env['pos.order.line'].sudo().search_count([('reward_id', 'in', self.ids)], limit=1):
            return self.action_archive()
        return super().unlink()
