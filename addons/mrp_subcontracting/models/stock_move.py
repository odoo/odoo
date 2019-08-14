# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    is_subcontract = fields.Boolean(copy=False)
    subcontract_components_ids = fields.One2many('stock.move.line',
        compute='_compute_subcontract_move_line_ids',
        inverse='_inverse_subcontract_move_line_ids',
        string='Subcontracted Components', readonly=False)

    def action_show_details(self):
        action = super(StockMove, self).action_show_details()
        action['context'].update({
            'show_lots_m2o': True,
            'show_lots_text': False,
        })
        return action

    def _compute_subcontract_move_line_ids(self):
        for move in self:
            if move.is_subcontract:
                move.subcontract_components_ids = move.move_orig_ids.production_id.move_raw_ids.move_line_ids

    def _inverse_subcontract_move_line_ids(self):
        for move in self:
            if move.is_subcontract:
                (move.move_orig_ids.production_id.move_raw_ids.move_line_ids - move.subcontract_components_ids).unlink()

    def _get_subcontract_bom(self):
        self.ensure_one()
        bom = self.env['mrp.bom'].sudo()._bom_subcontract_find(
            product=self.product_id,
            picking_type=self.picking_type_id,
            company_id=self.company_id.id,
            bom_type='subcontract',
            subcontractor=self.picking_id.partner_id,
        )
        return bom
    def write(self, values):
        res = super(StockMove, self).write(values)
        if 'product_uom_qty' in values:
            self.filtered(lambda m: m.is_subcontract and
            m.state not in ['draft', 'cancel', 'done'])._update_subcontract_order_qty()
        return res

    def _action_confirm(self, merge=True, merge_into=False):
        subcontract_details_per_picking = defaultdict(list)
        for move in self:
            if move.location_id.usage != 'supplier' or move.location_dest_id.usage == 'supplier':
                continue
            if not move.picking_id:
                continue
            bom = move._get_subcontract_bom()
            if not bom:
                continue
            subcontract_details_per_picking[move.picking_id].append((move, bom))
            move.write({
                'is_subcontract': True,
                'location_id': self.picking_id.partner_id.property_stock_subcontractor.id
            })
        for picking, subcontract_details in subcontract_details_per_picking.items():
            picking._subcontracted_produce(subcontract_details)
        return super(StockMove, self)._action_confirm(merge=merge, merge_into=merge_into)

    def _update_subcontract_order_qty(self):
        for move in self:
            production = move.move_orig_ids.production_id
            if production:
                self.env['change.production.qty'].with_context(skip_activity=True).create({
                    'mo_id': production.id,
                    'product_qty': move.product_uom_qty
                }).change_prod_qty()
