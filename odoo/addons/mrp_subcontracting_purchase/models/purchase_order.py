# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    subcontracting_resupply_picking_count = fields.Integer(
        "Count of Subcontracting Resupply", compute='_compute_subcontracting_resupply_picking_count',
        help="Count of Subcontracting Resupply for component")

    @api.depends('order_line.move_ids')
    def _compute_subcontracting_resupply_picking_count(self):
        for purchase in self:
            purchase.subcontracting_resupply_picking_count = len(purchase._get_subcontracting_resupplies())

    def action_view_subcontracting_resupply(self):
        return self._get_action_view_picking(self._get_subcontracting_resupplies())

    def _get_subcontracting_resupplies(self):
        moves_subcontracted = self.order_line.move_ids.filtered(lambda m: m.is_subcontract)
        subcontracted_productions = moves_subcontracted.move_orig_ids.production_id
        return subcontracted_productions.picking_ids

    def _get_mrp_productions(self, **kwargs):
        productions = super()._get_mrp_productions(**kwargs)
        if kwargs.get('remove_archived_picking_types', True):
            productions = productions.filtered(lambda production: production.with_context(active_test=False).picking_type_id.active)
        return productions
