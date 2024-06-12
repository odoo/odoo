# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    dropship_subcontractor_pick_type_id = fields.Many2one('stock.picking.type')

    def _create_subcontracting_dropshipping_sequence(self):
        seq_vals = [{
            'name': 'Dropship Subcontractor (%s)' % company.name,
            'code': 'mrp.subcontracting.dropshipping',
            'company_id': company.id,
            'prefix': 'DSC/',
            'padding': 5,
        } for company in self]

        if seq_vals:
            self.env['ir.sequence'].create(seq_vals)

    def _create_subcontracting_dropshipping_picking_type(self):
        pick_type_vals = []
        for company in self:
            sequence = self.env['ir.sequence'].search([
                ('code', '=', 'mrp.subcontracting.dropshipping'),
                ('company_id', '=', company.id),
            ])
            pick_type_vals.append({
                'name': 'Dropship Subcontractor',
                'company_id': company.id,
                'warehouse_id': False,
                'sequence_id': sequence.id,
                'code': 'incoming',
                'default_location_src_id': self.env.ref('stock.stock_location_suppliers').id,
                'default_location_dest_id': company.subcontracting_location_id.id,
                'sequence_code': 'DSC',
                'use_existing_lots': False,
            })
        if pick_type_vals:
            pick_type_ids = self.env['stock.picking.type'].create(pick_type_vals)
            for pick_type in pick_type_ids:
                pick_type.company_id.dropship_subcontractor_pick_type_id = pick_type.id

    def _create_subcontracting_dropshipping_rules(self):
        route = self.env.ref('mrp_subcontracting_dropshipping.route_subcontracting_dropshipping')
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        vals = []
        for company in self:
            subcontracting_location = company.subcontracting_location_id
            dropship_picking_type = self.env['stock.picking.type'].search([
                ('company_id', '=', company.id),
                ('default_location_src_id.usage', '=', 'supplier'),
                ('default_location_dest_id', '=', subcontracting_location.id),
            ], limit=1, order='sequence')
            if dropship_picking_type:
                vals.append({
                    'name': '%s → %s' % (supplier_location.name, subcontracting_location.name),
                    'action': 'buy',
                    'location_dest_id': subcontracting_location.id,
                    'location_src_id': supplier_location.id,
                    'procure_method': 'make_to_stock',
                    'route_id': route.id,
                    'picking_type_id': dropship_picking_type.id,
                    'company_id': company.id,
                })
        if vals:
            self.env['stock.rule'].create(vals)

    @api.model
    def _create_missing_subcontracting_dropshipping_rules(self):
        route = self.env.ref('mrp_subcontracting_dropshipping.route_subcontracting_dropshipping')
        company_ids = self.env['res.company'].search([])
        company_has_rules = self.env['stock.rule'].search([('route_id', '=', route.id)]).mapped('company_id')
        company_todo_rules = company_ids - company_has_rules
        company_todo_rules._create_subcontracting_dropshipping_rules()

    @api.model
    def _create_missing_subcontracting_dropshipping_sequence(self):
        company_ids = self.env['res.company'].search([])
        company_has_seq = self.env['ir.sequence'].search([('code', '=', 'mrp.subcontracting.dropshipping')]).mapped('company_id')
        company_todo_sequence = company_ids - company_has_seq
        company_todo_sequence._create_subcontracting_dropshipping_sequence()

    @api.model
    def _create_missing_subcontracting_dropshipping_picking_type(self):
        company_ids = self.env['res.company'].search([])
        company_has_dropship_subcontractor_picking_type = self.env['stock.picking.type'].search([
            ('default_location_src_id.usage', '=', 'supplier'),
            ('default_location_dest_id', 'in', company_ids.subcontracting_location_id.ids),
        ]).mapped('company_id')
        company_todo_picking_type = company_ids - company_has_dropship_subcontractor_picking_type
        company_todo_picking_type._create_subcontracting_dropshipping_picking_type()

    def _create_per_company_sequences(self):
        super()._create_per_company_sequences()
        self._create_subcontracting_dropshipping_sequence()

    def _create_per_company_rules(self):
        res = super()._create_per_company_rules()
        self._create_subcontracting_dropshipping_rules()
        return res

    def _create_per_company_picking_types(self):
        super()._create_per_company_picking_types()
        self._create_subcontracting_dropshipping_picking_type()
