# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'

    is_subcontractor = fields.Boolean('Subcontracted', compute='_compute_is_subcontractor', help="Choose a vendor of type subcontractor if you want to subcontract the product")

    @api.depends('partner_id', 'product_id', 'product_tmpl_id')
    def _compute_is_subcontractor(self):
        for supplier in self:
            boms = supplier.product_id.variant_bom_ids
            boms |= supplier.product_tmpl_id.bom_ids.filtered(lambda b: not b.product_id or b.product_id in (supplier.product_id or supplier.product_tmpl_id.product_variant_ids))
            supplier.is_subcontractor = supplier.partner_id in boms.subcontractor_ids


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _prepare_sellers(self, params=False):
        if params and params.get('subcontractor_ids'):
            return super()._prepare_sellers(params=params).filtered(lambda s: s.partner_id in params.get('subcontractor_ids'))
        return super()._prepare_sellers(params=params)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.depends('bom_line_ids', 'bom_line_ids.bom_id.type')
    def _compute_route_ids(self):
        super()._compute_route_ids()
        for template in self:
            resupply_subcontractor_route = self.env.ref('mrp_subcontracting.route_resupply_subcontractor_mto')
            has_subcontract_bom = any(bom_line.bom_id.type == 'subcontract' for bom_line in template.bom_line_ids)
            if template.qty_available and has_subcontract_bom and resupply_subcontractor_route:
                template.write({'route_ids': [(4, resupply_subcontractor_route.id)]})
            else:
                template.write({'route_ids': [(3, resupply_subcontractor_route.id)]})
