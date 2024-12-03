from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _optional_product_pos_domain(self):
        return [
            *self.env['product.template']._check_company_domain(self.env.company),
            ['sale_ok', '=', True],
            ['available_in_pos', '=', True],
        ]

    def get_product_info_pos(self, price, quantity, pos_config_id, product_variant_id=False):
        res = super().get_product_info_pos(price, quantity, pos_config_id, product_variant_id)

        # Optional products
        res['optional_products'] = [
            {'name': p.name, 'price': min(p.product_variant_ids.mapped('lst_price'))}
            for p in self.optional_product_ids.filtered_domain(self._optional_product_pos_domain())
        ]

        return res

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['invoice_policy', 'optional_product_ids', 'type', 'sale_line_warn', 'sale_line_warn_msg']
        return params
