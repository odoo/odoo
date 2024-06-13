from odoo import api, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['all_product_tag_ids']

        # add missing product fields used in the reward_product_domain
        missing_fields = self.env['loyalty.reward']._get_reward_product_domain_fields(config_id) - set(params)

        if missing_fields:
            params.extend([field for field in missing_fields if field in self._fields])

        return params

    def _load_pos_data(self, data):
        res = super()._load_pos_data(data)
        config_id = self.env['pos.config'].browse(data['pos.config']['data'][0]['id'])
        rewards = config_id._get_program_ids().reward_ids
        reward_products = rewards.discount_line_product_id | rewards.reward_product_ids | rewards.reward_product_id
        trigger_products = config_id._get_program_ids().filtered(lambda p: p.program_type in ['ewallet', 'gift_card']).trigger_product_ids

        loyalty_product_ids = set(reward_products.ids + trigger_products.ids)
        classic_product_ids = {product['id'] for product in res['data']}
        products = self.env['product.product'].browse(list(loyalty_product_ids - classic_product_ids))
        products = products.read(fields=res['fields'], load=False)
        self._process_pos_ui_product_product(products, config_id)

        data['pos.session']['data'][0]['_pos_special_products_ids'] += [product.id for product in reward_products if product.id not in [p["id"] for p in res['data']]]
        res['data'].extend(products)

        return res
