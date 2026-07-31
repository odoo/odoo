# -*- coding: utf-8 -*-

from odoo import models, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model_create_multi
    def create(self, vals_list):
        """Track stock move creation."""
        moves = super().create(vals_list)

        for move in moves:
            try:
                # Only log moves that are not part of a picking (to avoid duplication)
                # or log important standalone moves
                if not move.picking_id or move.inventory_id:
                    self.env['camtel.audit.log'].sudo().create_log(
                        event_type='stock_move_create',
                        description=f'Stock move created: {move.product_id.name} ({move.product_uom_qty} {move.product_uom.name})',
                        model_name='stock.move',
                        res_id=move.id,
                        resource_name=f'{move.product_id.name} - {move.name}',
                        severity='info',
                        success=True,
                        new_values={
                            'product': move.product_id.name,
                            'quantity': move.product_uom_qty,
                            'uom': move.product_uom.name,
                            'location_src': move.location_id.complete_name,
                            'location_dest': move.location_dest_id.complete_name,
                            'picking': move.picking_id.name if move.picking_id else None,
                        }
                    )
            except:
                pass

        return moves

    def _action_done(self, cancel_backorder=False):
        """Track stock move completion."""
        # Store info before completion
        move_info = [
            (m.id, m.product_id.name, m.product_uom_qty, m.product_uom.name, m.picking_id.name if m.picking_id else 'Direct')
            for m in self
        ]

        result = super()._action_done(cancel_backorder=cancel_backorder)

        for move_id, product_name, qty, uom, picking_name in move_info:
            try:
                move = self.browse(move_id)
                # Only log standalone moves or inventory adjustments (pickings are logged separately)
                if not move.picking_id or move.inventory_id:
                    self.env['camtel.audit.log'].sudo().create_log(
                        event_type='stock_move_done',
                        description=f'Stock move completed: {product_name} ({qty} {uom}) - {picking_name}',
                        model_name='stock.move',
                        res_id=move_id,
                        resource_name=f'{product_name} - {move.name}',
                        severity='info',
                        success=True,
                        additional_data={
                            'product': product_name,
                            'quantity': qty,
                            'uom': uom,
                            'picking': picking_name,
                            'location_src': move.location_id.complete_name,
                            'location_dest': move.location_dest_id.complete_name,
                        }
                    )
            except:
                pass

        return result
