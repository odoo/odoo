# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _create_subcontracting_dropshipping_rules(self):
        route = self.env.ref('mrp_subcontracting_dropshipping.route_subcontracting_dropshipping')
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        vals = []
        for company in self:
            subcontracting_location = company.subcontracting_location_id
            dropship_picking_type = self.env['stock.picking.type'].search([
                ('company_id', '=', company.id),
                ('default_location_src_id.usage', '=', 'supplier'),
                ('default_location_dest_id.usage', '=', 'customer'),
            ], limit=1, order='sequence')
            if dropship_picking_type:
                vals.append({
                    'name': '%s → %s' % (supplier_location.name, subcontracting_location.name),
                    'action': 'buy',
                    'location_id': subcontracting_location.id,
                    'location_src_id': supplier_location.id,
                    'procure_method': 'make_to_stock',
                    'route_id': route.id,
                    'picking_type_id': dropship_picking_type.id,
                    'company_id': company.id,
                })
        if vals:
            self.env['stock.rule'].create(vals)

    @api.model
    def create_missing_subcontracting_dropshipping_rules(self):
        route = self.env.ref('mrp_subcontracting_dropshipping.route_subcontracting_dropshipping')
        company_ids = self.env['res.company'].search([])
        company_has_rules = self.env['stock.rule'].search([('route_id', '=', route.id)]).mapped('company_id')
        company_todo_rules = company_ids - company_has_rules
        company_todo_rules._create_subcontracting_dropshipping_rules()

    def _create_per_company_rules(self):
        res = super()._create_per_company_rules()
        self.create_missing_subcontracting_dropshipping_rules()
        return res
