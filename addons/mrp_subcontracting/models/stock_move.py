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
        bom = self.env['mrp.bom']._bom_subcontract_find(
            product=self.product_id,
            picking_type=self.picking_type_id,
            company_id=self.company_id.id,
            bom_type='subcontract',
            subcontractor=self.picking_id.partner_id,
        )
        return bom

    def _action_confirm(self, merge=True, merge_into=False):
        subcontract_details_per_picking = defaultdict(list)
        for move in self:
            if not move.picking_id:
                continue
            if not move.picking_id._is_subcontract():
                continue
            bom = move._get_subcontract_bom()
            if not bom:
                error_message = _('Please define a BoM of type subcontracting for the product "%s". If you don\'t want to subcontract the product "%s", do not select a partner of type subcontractor.')
                error_message += '\n\n'
                error_message += _('If there is well a BoM of type subcontracting defined, check if you have set the correct subcontractors on it.')
                raise UserError(error_message % (move.product_id.name, move.product_id.name))
            subcontract_details_per_picking[move.picking_id].append((move, bom))
            move.write({
                'is_subcontract': True,
            })
        for picking, subcontract_details in subcontract_details_per_picking.items():
            picking._subcontracted_produce(subcontract_details)
        return super(StockMove, self)._action_confirm(merge=merge, merge_into=merge_into)
