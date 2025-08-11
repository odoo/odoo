from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _load_pos_data(self, data):
        res = super()._load_pos_data(data)
        config_id = self.env['pos.config'].browse(data['pos.config'][0]['id'])
        rewards = config_id._get_program_ids().reward_ids
        reward_products = rewards.discount_line_product_id | rewards.reward_product_ids | rewards.reward_product_id
        trigger_products = config_id._get_program_ids().trigger_product_ids

        loyalty_product_tmpl_ids = set((reward_products.product_tmpl_id | trigger_products.product_tmpl_id).ids)
        already_loaded_product_tmpl_ids = {template['id'] for template in res}

        missing_product_tmpl_ids = list(loyalty_product_tmpl_ids - already_loaded_product_tmpl_ids)
        fields = self.env['product.template']._load_pos_data_fields(data['pos.config'][0]['id'])

        missing_product_templates = self.env['product.template'].browse(missing_product_tmpl_ids).read(fields=fields, load=False)
        product_ids_to_hide = reward_products.product_tmpl_id - self.env['product.template'].browse(already_loaded_product_tmpl_ids)
        if self.env.context.get('pos_limited_loading', True):
            # Filter out products that can be loaded in the PoS but are not loaded yet
            product_ids_to_hide = product_ids_to_hide - product_ids_to_hide.filtered_domain(self._load_pos_data_domain(data))
        data['pos.session'][0]['_pos_special_products_ids'] += product_ids_to_hide.product_variant_id.ids

        # Identify special loyalty products (e.g., gift cards, e-wallets) to be displayed in the POS
        loyality_products = config_id.get_record_by_ref([
            'loyalty.gift_card_product_50',
            'loyalty.ewallet_product_50',
        ])
        special_display_products = self.env['product.product'].browse(loyality_products)
        # Include trigger products from loyalty programs of type 'gift_card' or 'ewallet'
        special_display_products += self.env['loyalty.program'].search([
            ('program_type', 'in', ['gift_card', 'ewallet']),
            ('pos_config_ids', 'in', [False, config_id.id]),
        ]).trigger_product_ids

        data['pos.session'][0]['_pos_special_display_products_ids'] = special_display_products.product_tmpl_id.ids
        res.extend(missing_product_templates)

        return res
