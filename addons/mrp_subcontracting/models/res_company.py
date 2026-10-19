# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    subcontracting_location_id = fields.Many2one('stock.location')

    @api.model
    def _create_missing_subcontracting_location(self):
        company_without_subcontracting_loc = self.env['res.company'].with_context(active_test=False).search(
            [('subcontracting_location_id', '=', False)])
        company_without_subcontracting_loc._create_subcontracting_location()

    def _create_per_company_locations(self):
        super(ResCompany, self)._create_per_company_locations()
        self._create_subcontracting_location()

    def _create_subcontracting_location(self):
        for company in self:
            subcontracting_location = self.env['stock.location'].create({
                'name': _('Subcontracting'),
                'usage': 'internal',
                'company_id': company.id,
            })
            self.env['ir.default'].set(
                "res.partner",
                "property_stock_subcontractor",
                subcontracting_location.id,
                company_id=company.id,
            )
            company.subcontracting_location_id = subcontracting_location
