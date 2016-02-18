# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import fields, models


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    subproduct_ids = fields.One2many('mrp.subproduct', inverse_name='bom_id', string='Byproducts', copy=True, oldname='sub_products')
