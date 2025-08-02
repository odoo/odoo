# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv.expression import AND

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    type = fields.Selection(selection_add=[
        ('subcontract', 'Subcontracting')
    ], ondelete={'subcontract': lambda recs: recs.write({'type': 'normal', 'active': False})})
    subcontractor_ids = fields.Many2many('res.partner', 'mrp_bom_subcontractor', string='Subcontractors', check_company=True)

    def _bom_subcontract_find(self, product, picking_type=None, company_id=False, bom_type='subcontract', subcontractor=False):
        domain = self._bom_find_domain(product, picking_type=picking_type, company_id=company_id, bom_type=bom_type)
        if subcontractor:
            domain = AND([domain, [('subcontractor_ids', 'parent_of', subcontractor.ids)]])
            return self.search(domain, order='sequence, product_id, id', limit=1)
        else:
            return self.env['mrp.bom']

    @api.model
    def _bom_subcontract_find_for_products(self, products, picking_type=None, company_id=False, bom_type='subcontract', subcontractors=False):
        """ Batched version of _bom_subcontract_find with multiple
        products and subcontractors.

        :return dict: dictionary mapping (product_id, partner_id) -> mrp.bom
        """
        def get_subcontractor_hierarchy_dict(subcontractors, subcontractor_dict=None):
            """Return a dictionary mapping a subcontractor to all its parents"""
            subcontractor_dict = subcontractor_dict or defaultdict(set)
            for subcontractor in subcontractors:
                # A subcontractor is its own parent
                subcontractor_dict[subcontractor].add(subcontractor.id)
                if subcontractor.parent_id:
                    get_subcontractor_hierarchy_dict(subcontractor.parent_id, subcontractor_dict)
                    subcontractor_dict[subcontractor].update(subcontractor_dict[subcontractor.parent_id])
            return subcontractor_dict

        bom_by_product_subcontractor = defaultdict(lambda: self.env['mrp.bom'])
        if not products or not subcontractors:
            return bom_by_product_subcontractor
        domain = self._bom_find_domain(products, picking_type=picking_type, company_id=company_id, bom_type=bom_type)
        domain = AND([domain, [('subcontractor_ids', 'parent_of', subcontractors.ids)]])
        if len(products) == 1 and len(subcontractors) == 1:
            bom_by_product_subcontractor[products, subcontractors] = self._bom_subcontract_find(
                products, picking_type, company_id, bom_type, subcontractors
            )
            return bom_by_product_subcontractor

        boms = self.search(domain, order='sequence, product_id, id')
        subcontractor_dict = get_subcontractor_hierarchy_dict(subcontractors)

        products_ids = set(products.ids)
        for bom in boms:
            bom_subcontractor_ids = set(bom.subcontractor_ids.ids)
            products_implies = bom.product_id or bom.product_tmpl_id.product_variant_ids
            for product in products_implies.filtered(lambda p: p in products_ids):
                for subcontractor in subcontractors:
                    if (
                        (product, subcontractor) not in bom_by_product_subcontractor
                        and bom_subcontractor_ids.intersection(subcontractor_dict[subcontractor])
                    ):
                        bom_by_product_subcontractor[product, subcontractor] = bom

        return bom_by_product_subcontractor

    @api.constrains('operation_ids', 'byproduct_ids', 'type')
    def _check_subcontracting_no_operation(self):
        if self.filtered_domain([('type', '=', 'subcontract'), '|', ('operation_ids', '!=', False), ('byproduct_ids', '!=', False)]):
            raise ValidationError(_('You can not set a Bill of Material with operations or by-product line as subcontracting.'))
