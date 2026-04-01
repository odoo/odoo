# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    subcontracting_source_purchase_count = fields.Integer(
        "Number of subcontracting PO Source", compute='_compute_subcontracting_source_purchase_count',
        help="Number of subcontracting Purchase Order Source")

    @api.depends('move_ids.move_dest_ids.raw_material_production_id')
    def _compute_subcontracting_source_purchase_count(self):
        for picking in self:
            picking.subcontracting_source_purchase_count = len(picking._get_subcontracting_source_purchase())

    def action_view_subcontracting_source_purchase(self):
        purchase_order_ids = self._get_subcontracting_source_purchase().ids
        action = {
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
        }
        if len(purchase_order_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': purchase_order_ids[0],
            })
        else:
            action.update({
                'name': _("Source PO of %s", self.name),
                'domain': [('id', 'in', purchase_order_ids)],
                'view_mode': 'list,form',
            })
        return action

    def _get_subcontracting_source_purchase(self):
        moves_subcontracted = self.move_ids.move_dest_ids.raw_material_production_id.move_finished_ids.move_dest_ids.filtered(lambda m: m.is_subcontract)
        return moves_subcontracted.purchase_line_id.order_id

    def _get_subcontract_mo_confirmation_ctx(self):
        res = super()._get_subcontract_mo_confirmation_ctx()
        res['po_to_notify'] = self.move_ids.purchase_line_id.order_id
        return res
