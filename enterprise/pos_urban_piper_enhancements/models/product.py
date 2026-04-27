from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def write(self, vals):
        res = super().write(vals)
        for product in self:
            if not self.env.context.get('skip_product_config_update'):
                product.attribute_line_ids.product_template_value_ids.urbanpiper_pos_config_ids = product.urbanpiper_pos_config_ids
        return res
