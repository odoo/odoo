# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.constrains('self_order_available', 'deposit_product_id')
    def _check_deposit_self_order_available(self):
        for product in self.product_variant_ids:
            if product.self_order_available and product.deposit_product_id and not product.deposit_product_id.self_order_available:
                raise ValidationError(self.env._(
                    "'%(product)s' is available in Self Order, so its deposit '%(deposit)s' needs to be available too, since it is added automatically.",
                    deposit=product.deposit_product_id.display_name,
                    product=product.display_name,
                ))
        products_using_deposit = self.env['product.product'].search([
            ('deposit_product_id.product_tmpl_id', 'in', self.filtered(lambda t: not t.self_order_available).ids),
            ('self_order_available', '=', True),
        ])
        if products_using_deposit:
            raise ValidationError(self.env._(
                "You cannot disable Available in Self Order because this product is used as a deposit for the following products:\n - %(products)s",
                products="\n - ".join(products_using_deposit.mapped('display_name')),
            ))
