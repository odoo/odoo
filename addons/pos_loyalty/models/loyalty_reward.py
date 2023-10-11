# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class LoyaltyReward(models.Model):
    _inherit = 'loyalty.reward'

    def _get_discount_product_values(self):
        res = super()._get_discount_product_values()
        for vals in res:
            vals.update({'taxes_id': False})
        return res

    def _should_compute_all_discount_product(self, reward):
        parent_res = super()._should_compute_all_discount_product(reward)
        if parent_res:
            return parent_res
        pos_loaded_data = self.env.context.get('loaded_data')
        if not pos_loaded_data:
            return False  # This is not PoS context

        reward_discount_product_domain = reward._get_discount_product_domain()
        if not reward_discount_product_domain:
            return False
        pos_loaded_data_product_product = pos_loaded_data['product.product']
        if not pos_loaded_data_product_product:
            return False  # No products were loaded in the PoS, so we don't care on the way it is loaded
        pos_product_product_loaded_fields = pos_loaded_data_product_product[0].keys()
        rewards_forced_python_loaded = self.env.context.get('rewards_forced_python_loaded')
        for leaf in reward_discount_product_domain:
            field = leaf[0]
            if len(leaf) == 3 and field not in pos_product_product_loaded_fields:
                rewards_forced_python_loaded[reward] = field
                return True  # The field won't be loaded in the JS, so we must evaluate in the python side
        return False
