from odoo import models


class PosConfig(models.Model):
    _inherit = ['pos.config']

    def _get_special_products(self):
        result = super()._get_special_products()
        tyro_surcharge_product = self.env.ref('pos_tyro.product_product_tyro_surcharge')
        return result | tyro_surcharge_product
