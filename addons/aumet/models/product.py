# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    scientific_name = fields.Many2one('aumet.scientific_name', string='Scientific Name', required=False)
