# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    can_be_expensed = fields.Boolean(help='Specify whether the product can be selected in an HR expense.\n'
                                          'Depending on the modules installed, this will allow you to choose an expense invoice policy if invoice policy is delivered quantities.')
