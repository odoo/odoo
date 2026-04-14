# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_free_qty(self, *, warehouse_id=None, **_kwargs):
        return self.with_context(warehouse_id=warehouse_id).free_qty
