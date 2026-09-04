# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductComboItem(models.Model):
    _name = 'product.combo.item'
    _description = "Product Combo Item"
    _check_company_auto = True

    company_id = fields.Many2one(related='combo_id.company_id', precompute=True, store=True)
    combo_id = fields.Many2one(comodel_name='product.combo', ondelete='cascade', required=True, index=True)
    product_id = fields.Many2one(
        string="Options",
        comodel_name='product.product',
        ondelete='restrict',
        domain=[('type', '!=', 'combo')],
        required=True,
        index=True,
        check_company=True,
    )
    currency_id = fields.Many2one(comodel_name='res.currency', compute='_compute_currency_id')
    lst_price = fields.Float(
        string="Original Price",
        min_display_digits='Product Price',
        compute='_compute_lst_price',
    )
    extra_price = fields.Float(string="Extra Price", min_display_digits='Product Price', default=0.0)

    @api.constrains('product_id')
    def _check_product_id_no_combo(self):
        if any(combo_item.product_id.type == 'combo' for combo_item in self):
            raise ValidationError(_("A combo choice can't contain products of type \"combo\"."))

    @api.depends('product_id.currency_id')
    @api.depends_context('company')
    def _compute_currency_id(self):
        # a plain `related` field does not recompute correctly per company here
        for combo_item in self:
            combo_item.currency_id = combo_item.product_id.currency_id

    @api.depends('product_id.lst_price')
    @api.depends_context('company')
    def _compute_lst_price(self):
        for combo_item in self:
            combo_item.lst_price = combo_item.product_id.lst_price
