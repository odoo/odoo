# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons.stock_landed_costs.models.stock_landed_cost import SPLIT_METHOD


class ProductTemplate(models.Model):
    _inherit = "product.template"

    landed_cost_ok = fields.Boolean('Is a Landed Cost', help='Indicates whether the product is a landed cost.')
    split_method_landed_cost = fields.Selection(SPLIT_METHOD, string="Default Split Method",
                                                help="Default Split Method when used for Landed Cost")
