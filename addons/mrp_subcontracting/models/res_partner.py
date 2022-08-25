# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    property_stock_subcontractor = fields.Many2one(
        'stock.location', string="Subcontractor Location", company_dependent=True,
        domain="[('is_subcontracting_location', '=', True)]",
        help="The stock location used as source and destination when sending\
        goods to this contact during a subcontracting process.")
    is_subcontractor = fields.Boolean(
        string="Subcontractor", store=False, search="_search_is_subcontractor", compute="_compute_is_subcontractor")
    bom_ids = fields.Many2many('mrp.bom', compute='_compute_bom_ids', string="BoMs for which the Partner is one of the subcontractors")
    production_ids = fields.Many2many('mrp.production', compute='_compute_production_ids', string="MRP Productions for which the Partner is the subcontractor")
    picking_ids = fields.Many2many('stock.picking', compute='_compute_picking_ids', string="Stock Pickings for which the Partner is the subcontractor")

    def _compute_bom_ids(self):
        results = self.env['mrp.bom'].read_group([('subcontractor_ids.commercial_partner_id', 'in', self.commercial_partner_id.ids)], ['ids:array_agg(id)', 'subcontractor_ids'], ['subcontractor_ids'])
        for partner in self:
            bom_ids = []
            for res in results:
                if partner.id == res['subcontractor_ids'][0] or res['subcontractor_ids'][0] in partner.child_ids.ids:
                    bom_ids += res['ids']
            partner.bom_ids = bom_ids

    def _compute_production_ids(self):
        results = self.env['mrp.production'].read_group([('subcontractor_id.commercial_partner_id', 'in', self.commercial_partner_id.ids)], ['ids:array_agg(id)'], ['subcontractor_id'])
        for partner in self:
            production_ids = []
            for res in results:
                if partner.id == res['subcontractor_id'][0] or res['subcontractor_id'][0] in partner.child_ids.ids:
                    production_ids += res['ids']
            partner.production_ids = production_ids

    def _compute_picking_ids(self):
        results = self.env['stock.picking'].read_group([('partner_id.commercial_partner_id', 'in', self.commercial_partner_id.ids)], ['ids:array_agg(id)'], ['partner_id'])
        for partner in self:
            picking_ids = []
            for res in results:
                if partner.id == res['partner_id'][0] or res['partner_id'][0] in partner.child_ids.ids:
                    picking_ids += res['ids']
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

    @api.depends_context('uid')
    def _compute_is_subcontractor(self):
        """ Check if the user is a subcontractor before giving sudo access
        """
        for partner in self:
            partner.is_subcontractor = (partner.user_has_groups('base.group_portal') and partner.env['mrp.bom'].search_count([
                ('type', '=', 'subcontract'),
                ('subcontractor_ids', 'in', (partner.env.user.partner_id | partner.env.user.partner_id.commercial_partner_id).ids),
            ]))
