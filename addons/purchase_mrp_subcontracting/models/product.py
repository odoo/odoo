# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    is_subcontractor = fields.Boolean('Subcontracted', compute='_compute_is_subcontractor', help="Choose a vendor of type subcontractor if you want to subcontract the product")

    @api.depends('name', 'product_id', 'product_tmpl_id')
    def _compute_is_subcontractor(self):
        for supplier in self:
            boms = supplier.product_id.variant_bom_ids
            boms |= supplier.product_tmpl_id.bom_ids.filtered(lambda b: not b.product_id)
            supplier.is_subcontractor = supplier.name in boms.subcontractor_ids
