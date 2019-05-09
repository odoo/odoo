# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MrpBom(models.Model):
    _name = 'mrp.bom'
    _description = 'Bill of Material'
    _inherit = 'mrp.bom'

    sub_products = fields.One2many('mrp.subproduct', 'bom_id', 'Byproducts', copy=True)

    @api.constrains('product_id', 'product_tmpl_id', 'sub_products')
    def _check_byproduct_recursion(self):
        for bom in self:
            if bom.product_id:
                if bom.sub_products.filtered(lambda x: x.product_id == bom.product_id):
                    raise ValidationError(_('Byproduct %s should not be same as BoM product.') % bom.display_name)
            elif:
                if bom.sub_products.filtered(lambda x: x.product_id.product_tmpl_id == bom.product_tmpl_id):
                    raise ValidationError(_('Byproduct product %s should not be same as BoM product.') % bom.display_name)
