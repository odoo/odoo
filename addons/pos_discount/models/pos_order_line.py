from odoo import models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    def _is_discount_product(self):
        config = self.order_id.config_id
        return super()._is_discount_product() or bool(
            config.module_pos_discount and self.product_id == config.discount_product_id,
        )
