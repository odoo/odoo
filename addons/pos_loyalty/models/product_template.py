from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _load_pos_metadata(self, data, search_params={}):
        super()._load_pos_metadata(data, search_params)
        domain = search_params.get('domain', False)
        if domain or 'pos.config' not in data:
            return data
        config = data['pos.config']['records']
        rewards = config._get_program_ids().reward_ids
        reward_products = rewards.discount_line_product_id | rewards.reward_product_ids | rewards.reward_product_id
        trigger_products = config._get_program_ids().trigger_product_ids

        loyalty_product_tmpl_ids = reward_products.product_tmpl_id | trigger_products.product_tmpl_id
        data['product.template']['records'] |= loyalty_product_tmpl_ids
        return data
