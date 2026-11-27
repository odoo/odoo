# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    deposit_product_id = fields.Many2one(
        'product.product',
        ondelete='restrict',
        index='btree_not_null',
        ui_domain="[('is_deposit', '=', True), ('available_in_pos', '=', True)]",
        help='The product used to charge a refundable deposit when this product is sold.',
    )

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ['deposit_product_id']

    @api.constrains('deposit_product_id')
    def _check_deposit_product(self):
        for product in self.filtered('deposit_product_id'):
            if product.is_deposit:
                raise ValidationError(self.env._("A deposit product cannot have another deposit product."))
            if not product.deposit_product_id.is_deposit:
                raise ValidationError(self.env._(
                    "%(deposit)s must be configured as a deposit product before it can be assigned to %(product)s.",
                    deposit=product.deposit_product_id.display_name,
                    product=product.display_name,
                ))
