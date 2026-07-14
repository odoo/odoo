# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    property_stock_subcontractor = fields.Many2one(
        'stock.location', string="Subcontractor Location", company_dependent=True,
        help="The stock location used as source and destination when sending\
        goods to this contact during a subcontracting process.")
    is_subcontractor = fields.Boolean(
        string="Subcontractor", store=False, search="_search_is_subcontractor", compute="_compute_is_subcontractor")
    bom_ids = fields.Many2many('mrp.bom', compute='_compute_bom_ids', string="BoMs for which the Partner is one of the subcontractors")
    production_ids = fields.Many2many('mrp.production', compute='_compute_production_ids', string="MRP Productions for which the Partner is the subcontractor")
    picking_ids = fields.Many2many('stock.picking', compute='_compute_picking_ids', string="Stock Pickings for which the Partner is the subcontractor")

    def _compute_bom_ids(self):
        results = self.env['mrp.bom']._read_group([('subcontractor_ids.commercial_partner_id', 'in', self.commercial_partner_id.ids)], ['subcontractor_ids'], ['id:array_agg'])
        for partner in self:
            bom_ids = []
            for subcontractor, ids in results:
                if partner.id == subcontractor.id or subcontractor.id in partner.child_ids.ids:
                    bom_ids += ids
            partner.bom_ids = bom_ids

    def _compute_production_ids(self):
        results = self.env['mrp.production']._read_group([('subcontractor_id.commercial_partner_id', 'in', self.commercial_partner_id.ids)], ['subcontractor_id'], ['id:array_agg'])
        for partner in self:
            production_ids = []
            for subcontractor, ids in results:
                if partner.id == subcontractor.id or subcontractor.id in partner.child_ids.ids:
                    production_ids += ids
            partner.production_ids = production_ids

    def _compute_picking_ids(self):
        results = self.env['stock.picking']._read_group([('partner_id.commercial_partner_id', 'in', self.commercial_partner_id.ids)], ['partner_id'], ['id:array_agg'])
        for partner in self:
            picking_ids = []
            for partner_rg, ids in results:
                if partner_rg.id == partner.id or partner_rg.id in partner.child_ids.ids:
                    picking_ids += ids
            partner.picking_ids = picking_ids

    def _search_is_subcontractor(self, operator, value):
        assert operator in ('=', '!=', '<>') and value in (True, False), 'Operation not supported'
        subcontractor_ids = self.env['mrp.bom'].search(
            [('type', '=', 'subcontract')]).subcontractor_ids.ids
        if (operator == '=' and value is True) or (operator in ('<>', '!=') and value is False):
            search_operator = 'in'
        else:
            search_operator = 'not in'
        return [('id', search_operator, subcontractor_ids)]

    def _compute_is_subcontractor(self):
        """ Determine whether the partner is a subcontractor (for giving sudo access) """
        for partner in self:
            partner.is_subcontractor = (
                any(user._is_portal() for user in partner.user_ids)
                and partner.env['mrp.bom'].search_count([
                    ('type', '=', 'subcontract'),
                    ('subcontractor_ids', 'in', (partner | partner.commercial_partner_id).ids),
                ], limit=1)
            )
