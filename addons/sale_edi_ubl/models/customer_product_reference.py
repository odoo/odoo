# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class CustomerProductReference(models.Model):
    _name = 'customer.product.reference'
    _description = "Customer Product Reference"

    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        required=True,
        ondelete='cascade',
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Customer",
        required=True,
        ondelete='cascade',
    )
    customer_product_reference = fields.Char(string="Customer Product Reference", required=True)
