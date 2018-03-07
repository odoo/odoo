# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def action_cancel(self):
        res = super(MrpProduction, self).action_cancel()
        if self.procurement_group_id:
            self._log_production_order_changes(self.product_qty)
        return res

    def _log_production_order_changes(self, product_qty):

        def _keys_in_sorted(move):
            return (move.picking_id.id, move.product_id.responsible_id.id)

        def _keys_in_groupby(move):
            return (move.picking_id, move.product_id.responsible_id)

        def _render_note_exception_quantity_production_order(order_exceptions):
            move_ids = self.env['stock.move'].concat(*rendering_context.keys())
            impacted_pickings = move_ids.mapped('picking_id')._get_impacted_pickings(move_ids) - move_ids.mapped('picking_id')
            values = {
                'prod_order_ids': self,
                'order_exceptions': order_exceptions.values(),
                'impacted_pickings': impacted_pickings,
                'impacted_prod_orders': self.move_dest_ids.mapped('raw_material_production_id')
            }
            return self.env.ref('sale_mrp.exception_on_mrp').render(values=values)

        Picking = self.env['stock.picking']
        to_log = {}
        for mrp in self:
            if mrp.move_dest_ids.mapped('picking_id'):
                to_log[mrp] = (mrp.product_qty, product_qty)
                documents = Picking._log_activity_get_documents(to_log, 'move_dest_ids', 'DOWN', _keys_in_sorted, _keys_in_groupby)
            else:
                to_log[mrp.move_dest_ids.mapped('raw_material_production_id')] = (mrp.product_qty, product_qty)
                documents = Picking._log_activity_get_documents(to_log, 'move_dest_ids', 'UP')
            filtered_documents = {}
            for (parent, responsible), rendering_context in documents.items():
                if parent._name == 'stock.picking' or parent._name == 'mrp.production':
                    if parent.state == 'cancel':
                        continue
                filtered_documents[(parent, responsible)] = rendering_context
            if mrp.move_dest_ids.mapped('picking_id'):
                Picking._log_activity(_render_note_exception_quantity_production_order, filtered_documents)
            else:
                self._log_activity_for_multi_level_production_order(filtered_documents, cancel=True)

    def _log_activity_for_multi_level_production_order(self, documents, cancel=False):

        def _render_note_exception_quantity_mrp_order(rendering_context):
            move_ids = self.env['stock.move'].concat(*rendering_context[0].keys())
            impacted_pickings = move_ids.mapped('picking_id')._get_impacted_pickings(move_ids)
            values = {
                'prod_order_ids': self,
                'order_exceptions': rendering_context[0].values(),
                'impacted_pickings': impacted_pickings,
                'impacted_prod_orders': self.move_dest_ids.mapped('raw_material_production_id')
            }
            return self.env.ref('sale_mrp.exception_on_mrp').render(values=values)
        self.env['stock.picking']._log_activity(_render_note_exception_quantity_mrp_order, documents)


class ChangeProductionQty(models.TransientModel):
    _inherit = 'change.production.qty'

    @api.multi
    def change_prod_qty(self):
        prev_qty = self.mo_id.product_qty
        res = super(ChangeProductionQty, self).change_prod_qty()
        if (prev_qty > self.mo_id.product_qty) and self.mo_id.procurement_group_id:
            self.mo_id._log_production_order_changes(prev_qty)
        return res
