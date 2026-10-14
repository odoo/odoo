from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def _get_saleable_tracking_types(self):
        return super()._get_saleable_tracking_types() + ['repair']
