# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api

class PosSession(models.Model):
    _inherit = 'pos.session'

<<<<<<< HEAD
    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        data += ['loyalty.program', 'loyalty.rule', 'loyalty.reward', 'loyalty.card']
        return data
||||||| parent of cd0976d7d8b3 (temp)
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
                    'discount_max_amount', 'discount_line_product_id',
                    'multi_product', 'reward_product_ids', 'reward_product_qty', 'reward_product_uom_id', 'reward_product_domain'],
                'context': {**self.env.context},
            },
            'loyalty.card': {
                'domain': lambda data: [('program_id', 'in', [program["id"] for program in data["loyalty.program"]])],
                'fields': ['partner_id', 'code', 'points', 'program_id', 'expiration_date'],
            },
        })
=======
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
                    'discount_max_amount', 'discount_line_product_id',
                    'multi_product', 'reward_product_ids', 'reward_product_qty', 'reward_product_uom_id', 'reward_product_domain'],
            },
            'loyalty.card': {
                'domain': lambda data: [('program_id', 'in', [program["id"] for program in data["loyalty.program"]])],
                'fields': ['partner_id', 'code', 'points', 'program_id', 'expiration_date'],
            },
        })
>>>>>>> cd0976d7d8b3 (temp)

