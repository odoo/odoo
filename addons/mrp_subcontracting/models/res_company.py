# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    subcontracting_location_id = fields.Many2one('stock.location')

    def _create_per_company_locations(self):
        super(ResCompany, self)._create_per_company_locations()
        self._create_subcontracting_location()

    def _create_subcontracting_location(self):
        for company in self:
            parent_location = self.env.ref('stock.stock_location_locations_partner', raise_if_not_found=False)
            subcontracting_location = self.env['stock.location'].create({
                'name': _('%s: Subcontracting Location') % company.name,
                'usage': 'internal',
                'location_id': parent_location.id,
                'company_id': company.id,
            })
            company.write({'subcontracting_location_id': subcontracting_location.id})

    @api.model
    def create_missing_subcontracting_location(self):
        company_without_subcontracting_loc = self.env['res.company'].search(
            [('subcontracting_location_id', '=', False)])
        for company in company_without_subcontracting_loc:
            company._create_subcontracting_location()

    def _create_resupply_subcontractor_rules(self):
        self.ensure_one()
        wh = self.env['stock.warehouse'].search([('company_id', '=', self.id), ('active', '=', True)], limit=1)
        subcontracting_location = self.subcontracting_location_id
        production_location = wh._get_production_location()
        resupply_route = wh._find_global_route('mrp_subcontracting.route_resupply_subcontractor_mto', _('Resupply Subcontractor on Order'))
        resupply_route.rule_ids = [(0, 0, {
            'name': '%s → %s' % (subcontracting_location.name, production_location.name),
            'action': 'pull',
            'picking_type_id': wh.subcontracting_type_id,
            'location_src_id': subcontracting_location,
            'location_id': production_location,
        })],

