from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def create(self, vals):
        if self.env.user.has_group('eg_product_creation_restriction.product_creation_restriction'):
            raise UserError(_("You don't have access to create product."))
        return super(ProductProduct, self).create(vals)