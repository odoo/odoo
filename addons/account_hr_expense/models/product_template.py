# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        if self.env.context.get('default_can_be_expensed'):
            result['supplier_taxes_id'] = False
        return result
