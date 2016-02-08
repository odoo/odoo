# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = "res.company"

    propagation_minimum_delta = fields.Integer(string='Minimum Delta for Propagation of a Date Change on moves linked together', defaulat=1)
    internal_transit_location_id = fields.Many2one('stock.location', string='Internal Transit Location', help="Technical field used for resupply routes between warehouses that belong to this company", on_delete="restrict")

    def create_transit_location(self):
        '''Create a transit location with company_id being the given company_id. This is needed
           in case of resuply routes between warehouses belonging to the same company, because
           we don't want to create accounting entries at that time.
        '''
        try:
            parent_loc = self.env.ref('stock.stock_location_locations').id
        except:
            parent_loc = False
        location_vals = {
            'name': _('%s: Transit Location') % self.name,
            'usage': 'transit',
            'company_id': self.id,
            'location_id': parent_loc,
        }
        location_id = self.env['stock.location'].create(location_vals)
        self.write({'internal_transit_location_id': location_id.id})

    @api.model
    def create(self, vals):
        company_id = super(ResCompany, self).create(vals)
        self.env['stock.warehouse'].create({
            'name': vals['name'],
            'code': vals['name'][:5],
            'company_id': company_id.id,
        })
        company_id.create_transit_location()
        return company_id
