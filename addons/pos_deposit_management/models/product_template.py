# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_deposit = fields.Boolean(string='Is Deposit', help='This product is used as a deposit product.')
    deposit_product_id = fields.Many2one(
        'product.product',
        string='Deposit Product',
        domain="[('is_deposit', '=', True)]",
        help='The deposit product that is added when this product is sold.',
    )

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ['is_deposit', 'deposit_product_id']
        return params

    @api.constrains('is_deposit', 'deposit_product_id')
    def _check_deposit_product(self):
        for product in self:
            if product.is_deposit and product.deposit_product_id:
                raise ValidationError(_("A deposit product cannot have another deposit product."))
