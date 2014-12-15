# -*- coding: utf-8 -*-

from openerp import fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    can_be_expensed = fields.Boolean(string='Can be Expensed', help="Specify if the product can be selected in an HR expense line.")
