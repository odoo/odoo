from odoo import api, models


class ProductProduct(models.Model):
    _inherit = ['product.product']

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['all_product_tag_ids']

        # add missing product fields used in the reward_product_domain
        missing_fields = self.env['loyalty.reward']._get_reward_product_domain_fields(config_id) - set(params)

        if missing_fields:
            params.extend([field for field in missing_fields if field in self._fields])

        return params
