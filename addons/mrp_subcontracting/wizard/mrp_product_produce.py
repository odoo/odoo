# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.float_utils import float_is_zero

class MrpProductProduce(models.TransientModel):
    _inherit = 'mrp.product.produce'

    subcontract_move_id = fields.Many2one('stock.move', 'stock move from the subcontract picking', check_company=True)

    def continue_production(self):
        action = super(MrpProductProduce, self).continue_production()
        action['context'] = dict(action['context'], default_subcontract_move_id=self.subcontract_move_id.id)
        return action

    def _generate_produce_lines(self):
        """ When the wizard is called in backend, the onchange that create the
        produce lines is not trigger. This method generate them and is used with
        _record_production to appropriately set the lot_produced_id and
        appropriately create raw stock move lines.
        """
        line_values = []
        for wizard in self:
            moves = (wizard.move_raw_ids | wizard.move_finished_ids).filtered(
                lambda move: move.state not in ('done', 'cancel')
            )
            for move in moves:
                qty_producing = wizard.product_uom_id._compute_quantity(wizard.qty_producing, wizard.production_id.product_uom_id)
                qty_to_consume = wizard._prepare_component_quantity(move, qty_producing)
                vals = wizard._generate_lines_values(move, qty_to_consume)
                line_values += vals
        self.env['mrp.product.produce.line'].create(line_values)

    def _update_finished_move(self):
        """ After producing, set the move line on the subcontract picking. """
        res = super(MrpProductProduce, self)._update_finished_move()
        move_line_vals = []
        for wizard in self:
            if wizard.subcontract_move_id:
                move_line_vals.append({
                    'move_id': wizard.subcontract_move_id.id,
                    'picking_id': wizard.subcontract_move_id.picking_id.id,
                    'product_id': wizard.product_id.id,
                    'location_id': wizard.subcontract_move_id.location_id.id,
                    'location_dest_id': wizard.subcontract_move_id.location_dest_id.id,
                    'product_uom_qty': 0,
                    'product_uom_id': wizard.product_uom_id.id,
                    'qty_done': wizard.qty_producing,
                    'lot_id': wizard.finished_lot_id and wizard.finished_lot_id.id,
                })
                if not wizard._get_todo(wizard.production_id):
                    ml_reserved = wizard.subcontract_move_id.move_line_ids.filtered(lambda ml:
                        float_is_zero(ml.qty_done, precision_rounding=ml.product_uom_id.rounding) and
                        not float_is_zero(ml.product_uom_qty, precision_rounding=ml.product_uom_id.rounding))
                    ml_reserved.unlink()
                    for ml in wizard.subcontract_move_id.move_line_ids:
                        ml.product_uom_qty = ml.qty_done
                    wizard.subcontract_move_id._recompute_state()
        self.env['stock.move.line'].create(move_line_vals)
        return res

