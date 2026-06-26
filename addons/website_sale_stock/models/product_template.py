# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _prepare_delivery_availability_values(self, product, website, uom, /, **kwargs):
        kwargs.setdefault("warehouse_id", website.warehouse_id.id)
        return super()._prepare_delivery_availability_values(product, website, uom, **kwargs)
