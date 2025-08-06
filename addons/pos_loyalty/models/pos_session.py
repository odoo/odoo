# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        data += ['loyalty.program', 'loyalty.rule', 'loyalty.reward', 'loyalty.card']
        return data

    @api.model
    def _read_from_metadata(self, server_data, local_data, config_id):
        if 'product.template' in server_data:
            # If there is a different domain, it means that we wants specific products.
            config = self.env['pos.config'].browse(config_id)

            rewards = config._get_program_ids().reward_ids
            reward_products = rewards.discount_line_product_id | rewards.reward_product_ids | rewards.reward_product_id
            trigger_products = config._get_program_ids().trigger_product_ids

            already_loaded_product_tmpl_ids = server_data['product.template']['records']
            product_ids_to_hide = reward_products.product_tmpl_id - already_loaded_product_tmpl_ids

            server_data['product.template']['records'] = server_data['product.template']['records'] | reward_products.product_tmpl_id | trigger_products.product_tmpl_id

        res = super()._read_from_metadata(server_data, local_data, config_id)
        if 'pos.session' in res and len(res['pos.session']['records']) == 1:
            res['pos.session']['records'][0]['_pos_special_products_ids'] += product_ids_to_hide.product_variant_id.ids

        return res
