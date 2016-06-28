# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models

class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    discount_policy = fields.Selection([
        ('with_discount', 'Discount included in the price'),
        ('without_discount', 'Show discount in the sale order')],
        default='with_discount')
