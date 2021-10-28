# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import fields, models, _, api
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    move_line_raw_ids = fields.One2many(
        'stock.move.line', string="Detail Component", readonly=False,
        inverse='_inverse_move_line_raw_ids', compute='_compute_move_line_raw_ids'
    )

    @api.depends('move_raw_ids.move_line_ids')
    def _compute_move_line_raw_ids(self):
        for production in self:
            production.move_line_raw_ids = production.move_raw_ids.move_line_ids

    def _inverse_move_line_raw_ids(self):
        for production in self:
            line_by_product = defaultdict(lambda: self.env['stock.move.line'])
            for line in production.move_line_raw_ids:
                line_by_product[line.product_id] |= line
            for move in production.move_raw_ids:
                move.move_line_ids = line_by_product.pop(move.product_id, self.env['stock.move.line'])
            for product_id, lines in line_by_product.items():
                qty = sum(line.product_uom_id._compute_quantity(line.qty_done, product_id.uom_id) for line in lines)
                move = production._get_move_raw_values(product_id, qty, product_id.uom_id)
                move['additional'] = True
                production.move_raw_ids = [(0, 0, move)]
                production.move_raw_ids.filtered(lambda m: m.product_id == product_id)[:1].move_line_ids = lines

    def subcontracting_record_component(self):
        self.ensure_one()
        assert self.env.context.get('subcontract_move_id')
        if float_is_zero(self.qty_producing, precision_rounding=self.product_uom_id.rounding):
            return {'type': 'ir.actions.act_window_close'}
        if self.product_tracking != 'none' and not self.lot_producing_id:
            raise UserError(_('You must enter a serial number for %s') % self.product_id.name)
        for sml in self.move_raw_ids.move_line_ids:
            if sml.tracking != 'none' and not sml.lot_id:
                raise UserError(_('You must enter a serial number for each line of %s') % sml.product_id.display_name)
        self._update_finished_move()
        quantity_issues = self._get_quantity_produced_issues()
        if quantity_issues:
            backorder = self._generate_backorder_productions(close_mo=False)
            # No qty to consume to avoid propagate additional move
            # TODO avoid : stock move created in backorder with 0 as qty
            backorder.move_raw_ids.filtered(lambda m: m.additional).product_uom_qty = 0.0

            backorder.qty_producing = backorder.product_qty
            backorder._set_qty_producing()

            self.product_qty = self.qty_producing
            subcontract_move_id = self.env['stock.move'].browse(self.env.context.get('subcontract_move_id'))
            action = subcontract_move_id._action_record_components()
            action.update({'res_id': backorder.id})
            return action
        return {'type': 'ir.actions.act_window_close'}

    def action_subcontracting_discard_remaining_components(self):
        self.ensure_one()
        self.qty_producing = 0
        return {'type': 'ir.actions.act_window_close'}

    def _pre_button_mark_done(self):
        if self.env.context.get('subcontract_move_id'):
            return True
        return super()._pre_button_mark_done()

    def _update_finished_move(self):
        """ After producing, set the move line on the subcontract picking. """
        self.ensure_one()
        subcontract_move_id = self.env.context.get('subcontract_move_id')
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
            if not self._get_quantity_to_backorder():
                ml_reserved = subcontract_move_id.move_line_ids.filtered(lambda ml:
                    float_is_zero(ml.qty_done, precision_rounding=ml.product_uom_id.rounding) and
                    not float_is_zero(ml.product_uom_qty, precision_rounding=ml.product_uom_id.rounding))
                ml_reserved.unlink()
                for ml in subcontract_move_id.move_line_ids:
                    ml.product_uom_qty = ml.qty_done
                subcontract_move_id._recompute_state()

    def _subcontracting_filter_to_done(self):
        """ Filter subcontracting production where composant is already recorded and should be consider to be validate """
        def filter_in(mo):
            if mo.state in ('done', 'cancel'):
                return False
            if float_is_zero(mo.qty_producing, precision_rounding=mo.product_uom_id.rounding):
                return False
            if not all(line.lot_id for line in mo.move_raw_ids.filtered(lambda sm: sm.has_tracking != 'none').move_line_ids):
                return False
            if mo.product_tracking != 'none' and not mo.lot_producing_id:
                return False
            return True

        return self.filtered(filter_in)
