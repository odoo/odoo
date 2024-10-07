from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _load_pos_data(self, data):
        res = super()._load_pos_data(data)
        config_id = self.env['pos.config'].browse(data['pos.config']['data'][0]['id'])
        rewards = config_id._get_program_ids().reward_ids
        reward_products = rewards.discount_line_product_id | rewards.reward_product_ids | rewards.reward_product_id
        trigger_products = config_id._get_program_ids().filtered(lambda p: p.program_type in ['ewallet', 'gift_card']).trigger_product_ids

        loyalty_product_ids = set(reward_products.ids + trigger_products.ids)
        classic_product_ids = {product['id'] for product in res['data']}
        products = self.env['product.product'].browse(list(loyalty_product_ids - classic_product_ids))
        product_tmpl_ids = products.product_tmpl_id.read(fields=res['fields'], load=False)
        self._process_pos_ui_product_product(product_tmpl_ids, config_id)

        data['pos.session']['data'][0]['_pos_special_products_ids'] += [product.id for product in reward_products if product.id not in [p["id"] for p in res['data']]]
        res['data'].extend(product_tmpl_ids)

        return res
