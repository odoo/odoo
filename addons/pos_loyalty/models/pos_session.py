# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config):
        data = super()._load_pos_data_models(config)
        data += ['loyalty.program', 'loyalty.rule', 'loyalty.reward', 'loyalty.card']
        return data

    @api.model
    def _read_from_metadata(self, server_data, local_data, config_id):
        if 'product.template' in server_data:
            # If there is a different domain, it means that we wants specific products.

            rewards = config_id._get_program_ids().reward_ids
            reward_products = rewards.discount_line_product_id | rewards.reward_product_ids | rewards.reward_product_id
            trigger_products = config_id._get_program_ids().trigger_product_ids

            already_loaded_product_tmpl_ids = server_data['product.template']['records']

            server_data['product.template']['records'] |= reward_products.product_tmpl_id | trigger_products.product_tmpl_id

        res = super()._read_from_metadata(server_data, local_data, config_id)
        if 'pos.config' in res and len(res['pos.config']['records']) == 1:
            product_ids_to_hide = reward_products.product_tmpl_id - already_loaded_product_tmpl_ids

            # Filter out products that can be loaded in the PoS but are not loaded yet
            product_ids_to_hide = product_ids_to_hide - product_ids_to_hide.filtered_domain(self.env['product.template']._load_pos_data_domain({'pos.config': server_data['pos.config']['records']}))

            res['pos.config']['records'][0]['_pos_special_products_ids'] += product_ids_to_hide.product_variant_id.ids

            # Identify special loyalty products (e.g., gift cards, e-wallets) to be displayed in the POS
            loyality_products = config_id.get_record_by_ref([
                'loyalty.gift_card_product_50',
                'loyalty.ewallet_product_50',
            ])
            special_display_products = self.env['product.product'].browse(loyality_products)
            # Include trigger products from loyalty programs of type 'gift_card' or 'ewallet'
            special_display_products += self.env['loyalty.program'].search([
                ('program_type', 'in', ['ewallet']),
                ('pos_config_ids', 'in', [False, config_id.id]),
            ]).trigger_product_ids
            res['pos.config']['records'][0]['_pos_special_display_products_ids'] = special_display_products.product_tmpl_id.ids

        return res

    def filter_local_data(self, models_to_filter):
        res = super().filter_local_data(models_to_filter)
        if 'loyalty.program' in models_to_filter:
            loyalty_programs = self.env['loyalty.program'].search([('id', 'in', models_to_filter['loyalty.program'])])
            valid_programs = self.config_id._get_program_ids()
            res['loyalty.program'] = (loyalty_programs - valid_programs).ids
        return res
