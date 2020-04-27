# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.float_utils import float_compare, float_is_zero


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('subcontract_move_id'):
            for production in self:
                if production.state not in ('cancel', 'done') and \
                        ('lot_producing_id' in vals or 'qty_producing' in vals):
                    production._update_finished_move()

    def _pre_button_mark_done(self):
        if self.env.context.get('subcontract_move_id'):
            return True
        return super()._pre_button_mark_done()

    def _update_finished_move(self):
        """ After producing, set the move line on the subcontract picking. """
        subcontract_move_id = self.env.context.get('subcontract_move_id')
        res = None
        if subcontract_move_id:
            subcontract_move_id = self.env['stock.move'].browse(subcontract_move_id)
            quantity = self.qty_producing
            if self.lot_producing_id:
                move_lines = subcontract_move_id.move_line_ids.filtered(lambda ml: ml.lot_id == self.lot_producing_id or not ml.lot_id)
            else:
                move_lines = subcontract_move_id.move_line_ids.filtered(lambda ml: not ml.lot_id)
            # Update reservation and quantity done
            for ml in move_lines:
                rounding = ml.product_uom_id.rounding
                if float_compare(quantity, 0, precision_rounding=rounding) <= 0:
                    break
                quantity_to_process = min(quantity, ml.product_uom_qty - ml.qty_done)
                quantity -= quantity_to_process

                new_quantity_done = (ml.qty_done + quantity_to_process)

                # on which lot of finished product
                if float_compare(new_quantity_done, ml.product_uom_qty, precision_rounding=rounding) >= 0:
                    ml.write({
                        'qty_done': new_quantity_done,
                        'lot_id': self.lot_producing_id and self.lot_producing_id.id,
                    })
                else:
                    new_qty_reserved = ml.product_uom_qty - new_quantity_done
                    default = {
                        'product_uom_qty': new_quantity_done,
                        'qty_done': new_quantity_done,
                        'lot_id': self.lot_producing_id and self.lot_producing_id.id,
                    }
                    ml.copy(default=default)
                    ml.with_context(bypass_reservation_update=True).write({
                        'product_uom_qty': new_qty_reserved,
                        'qty_done': 0
                    })

            if float_compare(quantity, 0, precision_rounding=self.product_uom_id.rounding) > 0:
                self.env['stock.move.line'].create({
                    'move_id': subcontract_move_id.id,
                    'picking_id': subcontract_move_id.picking_id.id,
                    'product_id': self.product_id.id,
                    'location_id': subcontract_move_id.location_id.id,
                    'location_dest_id': subcontract_move_id.location_dest_id.id,
                    'product_uom_qty': 0,
                    'product_uom_id': self.product_uom_id.id,
                    'qty_done': quantity,
                    'lot_id': self.lot_producing_id and self.lot_producing_id.id,
                })

            if not self._get_todo():
                ml_reserved = subcontract_move_id.move_line_ids.filtered(lambda ml:
                    float_is_zero(ml.qty_done, precision_rounding=ml.product_uom_id.rounding) and
                    not float_is_zero(ml.product_uom_qty, precision_rounding=ml.product_uom_id.rounding))
                ml_reserved.unlink()
                for ml in subcontract_move_id.move_line_ids:
                    ml.product_uom_qty = ml.qty_done
                subcontract_move_id._recompute_state()
        return res

    def _get_todo(self):
        """ This method will return remaining todo quantity of production. """
        main_product_moves = self.move_finished_ids.filtered(lambda x: x.product_id.id == self.product_id.id)
        todo_quantity = self.product_qty - sum(main_product_moves.mapped('quantity_done'))
        todo_quantity = todo_quantity if (todo_quantity > 0) else 0
        return todo_quantity
