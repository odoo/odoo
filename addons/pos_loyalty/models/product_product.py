from odoo import api, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ['all_product_tag_ids']

        # add missing product fields used in the reward_product_domain
        missing_fields = self.env['loyalty.reward']._get_reward_product_domain_fields(config) - set(params)

        if missing_fields:
            params.extend([field for field in missing_fields if field in self._fields])

        return params

    @api.model
    def _load_pos_data_read(self, records, config):
        read_records = super()._load_pos_data_read(records, config)
        if not read_records:
            return read_records

        rewards = config._get_program_ids().reward_ids
        reward_products = rewards.discount_line_product_id | rewards.reward_product_ids | rewards.reward_product_id
        product_tmpl_domain = self.env['product.template']._load_pos_data_domain({'pos.config': config})
        product_ids_to_hide = reward_products.product_tmpl_id - self.env['product.template'].search(product_tmpl_domain)
        product_ids_to_hide = product_ids_to_hide.product_variant_id.ids
        for record in read_records:
            if record['id'] in product_ids_to_hide:
                record['_is_pos_special_product'] = True
        return read_records
