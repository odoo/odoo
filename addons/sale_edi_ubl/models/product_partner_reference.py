# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ProductPartnerReference(models.Model):
    _name = 'product.partner.reference'
    _description = "Product Partner Reference"

    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        required=True,
        ondelete='cascade',
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Partner",
        required=True,
        ondelete='cascade',
    )
    partner_product_reference = fields.Char(string="Partner Product Reference", required=True)

    _sql_constraints = [
        ('unique_partner_product', 'unique(product_id, partner_id)',
        "The combination of product and partner must be unique!")
    ]
