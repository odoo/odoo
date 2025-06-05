# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    default_warranty_id = fields.Many2one('product.warranty',
        help="Warranty status based on delivery date can be tracked from the partner")
