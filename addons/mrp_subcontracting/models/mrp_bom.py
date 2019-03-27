# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    type = fields.Selection(selection_add=[('subcontract', 'Subcontracting')])
    subcontractor_ids = fields.One2many('res.partner', 'bom_id', domain=[('type', '=', 'subcontractor')], string='Subcontractors')

    def _bom_subcontract_find(self, product_tmpl=None, product=None, picking_type=None, company_id=False, bom_type='subcontract', subcontractor=False):
        domain = self._bom_find_domain(product_tmpl=product_tmpl, product=product, picking_type=picking_type, company_id=company_id, bom_type=bom_type)
        if subcontractor:
            domain += ['|', ('subcontractor_ids', 'in', subcontractor.id), ('subcontractor_ids', '=', False)]
        else:
            domain += [('subcontractor_ids', '=', False)]
        return self.search(domain, order='subcontractor_ids, sequence, product_id', limit=1)

