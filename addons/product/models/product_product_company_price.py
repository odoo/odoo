# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductProductCompanyPrice(models.Model):
    _name = 'product.product.company.price'
    _description = "Product Variant Sales Price per Company"

    product_id = fields.Many2one(
        comodel_name='product.product', ondelete='cascade', required=True, index=True,
    )
    company_id = fields.Many2one(comodel_name='res.company', ondelete='cascade', required=True)
    lst_price = fields.Float(string="Sales Price", min_display_digits='Product Price')
    computed_lst_price = fields.Float(help="Template sales price plus the extra prices.")

    _product_company_uniq = models.Constraint(
        'unique(product_id, company_id)',
        "A variant can only have one sales price per company.",
    )
