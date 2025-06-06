from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _load_pos_data_search_read(self, data, config):
        read_data = super()._load_pos_data_search_read(data, config)

        rewards = config._get_program_ids().reward_ids
        reward_products = rewards.discount_line_product_id | rewards.reward_product_ids | rewards.reward_product_id
        trigger_products = config._get_program_ids().trigger_product_ids

        loyalty_product_tmpl_ids = set((reward_products.product_tmpl_id | trigger_products.product_tmpl_id).ids)
        already_loaded_product_tmpl_ids = {template['id'] for template in read_data}

        missing_product_tmpl_ids = list(loyalty_product_tmpl_ids - already_loaded_product_tmpl_ids)
        fields = self.env['product.template']._load_pos_data_fields(config)

        missing_product_templates = self.env['product.template'].browse(missing_product_tmpl_ids).read(fields=fields, load=False)
        product_ids_to_hide = reward_products.product_tmpl_id - self.env['product.template'].browse(already_loaded_product_tmpl_ids)
        data['pos.config'][0]['_pos_special_products_ids'] += product_ids_to_hide.product_variant_id.ids

        read_data.extend(missing_product_templates)
        return read_data
