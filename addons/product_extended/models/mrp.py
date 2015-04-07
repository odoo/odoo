# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class MrpBom(models.Model):
    _inherit = 'mrp.bom'
            
    standard_price = fields.Float(related='product_tmpl_id.standard_price')
