# -*- coding: utf-8 -*-

from openerp import api, fields, models

class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    visible_discount = fields.Boolean('Visible Discount', default=True)
