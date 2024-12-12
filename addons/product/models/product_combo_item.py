# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductComboItem(models.Model):
    _name = 'product.combo.item'
    _description = "Product Combo Item"
    _check_company_auto = True

    _sql_constraints = [(
        'no_nested_combos',
        "CHECK(product_type != 'combo')",
        "A combo choice can't contain products of type \"combo\"."
    )]

    company_id = fields.Many2one(related='combo_id.company_id', precompute=True, store=True)
    combo_id = fields.Many2one(comodel_name='product.combo', ondelete='cascade', required=True)
    product_id = fields.Many2one(
        string="Product",
        comodel_name='product.product',
        ondelete='cascade',
        domain=[('type', '!=', 'combo')],
        required=True,
        check_company=True,
    )
    currency_id = fields.Many2one(comodel_name='res.currency', related='product_id.currency_id')
    product_type = fields.Selection(related='product_id.type', store=True)
    lst_price = fields.Float(
        string="Original Price",
        digits='Product Price',
        related='product_id.lst_price',
    )
    extra_price = fields.Float(string="Extra Price", digits='Product Price', default=0.0)
