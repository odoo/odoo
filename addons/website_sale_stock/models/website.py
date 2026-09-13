from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    warehouse_id = fields.Many2one(comodel_name="stock.warehouse")

    def _get_product_available_qty(self, product, **kwargs):
        return product.with_context(warehouse_id=self.warehouse_id.id).qty_free
