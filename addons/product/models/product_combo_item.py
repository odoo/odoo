# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductComboItem(models.Model):
    _name = 'product.combo.item'
    _description = "Product Combo Item"

    combo_id = fields.Many2one(comodel_name='product.combo')
    product_id = fields.Many2one(string="Product", comodel_name='product.product', required=True)
    lst_price = fields.Float(string="Original Price", related='product_id.lst_price')
    extra_price = fields.Float(string="Extra Price", default=0.0)
