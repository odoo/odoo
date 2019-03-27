# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    is_subcontractor = fields.Boolean('Subcontracted', compute='_compute_is_subcontractor', help="Choose a vendor of type subcontractor if you want to subcontract the product")

    @api.depends('name')
    def _compute_is_subcontractor(self):
        for supplierinfo in self:
            supplierinfo.is_subcontractor = True if supplierinfo.name.type == 'subcontractor' else False

