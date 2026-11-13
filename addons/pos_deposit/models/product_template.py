# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_deposit = fields.Boolean(string='Is Deposit', help='This product is used as a deposit product.')
    deposit_product_id = fields.Many2one(
        'product.product',
        string='Deposit Product',
        index='btree_not_null',
        ui_domain="[('is_deposit', '=', True), ('available_in_pos', '=', True)]",
        help='The deposit product that is added when this product is sold.',
    )

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ['is_deposit', 'deposit_product_id']

    @api.model
    def _load_pos_data_domain(self, data):
        domain = super()._load_pos_data_domain(data)
        deposit_products = self.env['product.product'].browse([
            deposit_product.id
            for deposit_product, in self._read_group(
                Domain.AND([domain, [('deposit_product_id', '!=', False)]]),
                ['deposit_product_id'],
            )
        ])
        deposit_templates = deposit_products.product_tmpl_id
        if not deposit_templates:
            return domain
        return Domain.OR([
            domain,
            [('id', 'in', deposit_templates.ids), ('available_in_pos', '=', True)],
        ])

    @api.constrains('is_deposit', 'deposit_product_id')
    def _check_deposit_product(self):
        for template in self:
            if template.deposit_product_id and template.is_deposit:
                raise ValidationError(self.env._("A deposit product cannot have another deposit product."))
            if template.deposit_product_id and not template.deposit_product_id.is_deposit:
                raise ValidationError(self.env._(
                    "%(deposit)s cannot be the deposit of %(product)s: it is not a deposit product.",
                    deposit=template.deposit_product_id.display_name,
                    product=template.display_name,
                ))
        not_deposits = self.filtered(lambda template: not template.is_deposit)
        if not_deposits and self.with_context(active_test=False).search_count(
            [('deposit_product_id.product_tmpl_id', 'in', not_deposits.ids)], limit=1,
        ):
            raise ValidationError(self.env._("A product used as the deposit of another product must be a deposit product."))
