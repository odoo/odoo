# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_round


class ChangeProductionQty(models.TransientModel):
    _name = 'change.production.qty'
    _description = 'Change Production Qty'

    mo_id = fields.Many2one('mrp.production', 'Manufacturing Order',
        required=True, ondelete='cascade')
    product_qty = fields.Float(
        'Quantity To Produce',
        digits='Product Unit of Measure', required=True)

    @api.model
    def default_get(self, fields):
        res = super(ChangeProductionQty, self).default_get(fields)
        if 'mo_id' in fields and not res.get('mo_id') and self._context.get('active_model') == 'mrp.production' and self._context.get('active_id'):
            res['mo_id'] = self._context['active_id']
        if 'product_qty' in fields and not res.get('product_qty') and res.get('mo_id'):
            res['product_qty'] = self.env['mrp.production'].browse(res['mo_id']).product_qty
        return res

    @api.model
    def _update_finished_moves(self, production, new_qty, old_qty):
        """ Update finished product and its byproducts. This method only update
        the finished moves not done or cancel and just increase or decrease
        their quantity according the unit_ratio. It does not use the BoM, BoM
        modification during production would not be taken into consideration.
        """
        modification = {}
        for move in production.move_finished_ids:
            if move.state in ('done', 'cancel'):
                continue
            done_qty = sum(production.move_finished_ids.filtered(
                lambda r:
                    r.product_id == move.product_id and
                    r.state == 'done'
                ).mapped('product_uom_qty')
            )
            qty = (new_qty - old_qty) * move.unit_factor + done_qty
            modification[move] = (move.product_uom_qty + qty, move.product_uom_qty)
            if (move.product_uom_qty + qty) > 0:
                move.write({'product_uom_qty': move.product_uom_qty + qty})
            else:
                move._action_cancel()

        return modification

    def change_prod_qty(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for wizard in self:
            production = wizard.mo_id
            produced = sum(production.move_finished_ids.filtered(lambda m: m.product_id == production.product_id).mapped('quantity_done'))
            if wizard.product_qty < produced:
                format_qty = '%.{precision}f'.format(precision=precision)
                raise UserError(_(
                    "You have already processed %(quantity)s. Please input a quantity higher than %(minimum)s ",
                    quantity=format_qty % produced,
                    minimum=format_qty % produced
                ))
            old_production_qty = production.product_qty
            new_production_qty = wizard.product_qty
            done_moves = production.move_finished_ids.filtered(lambda x: x.state == 'done' and x.product_id == production.product_id)
            qty_produced = production.product_id.uom_id._compute_quantity(sum(done_moves.mapped('product_qty')), production.product_uom_id)

            factor = (new_production_qty - qty_produced) / (old_production_qty - qty_produced)
            update_info = production._update_raw_moves(factor)
            documents = {}
            for move, old_qty, new_qty in update_info:
                iterate_key = production._get_document_iterate_key(move)
                if iterate_key:
                    document = self.env['stock.picking']._log_activity_get_documents({move: (new_qty, old_qty)}, iterate_key, 'UP')
                    for key, value in document.items():
                        if documents.get(key):
                            documents[key] += [value]
                        else:
                            documents[key] = [value]
            production._log_manufacture_exception(documents)
            finished_moves_modification = self._update_finished_moves(production, new_production_qty - qty_produced, old_production_qty - qty_produced)
            if finished_moves_modification:
                production._log_downside_manufactured_quantity(finished_moves_modification)
            production.write({'product_qty': new_production_qty})

            for wo in production.workorder_ids:
                operation = wo.operation_id
                wo.duration_expected = wo._get_duration_expected(ratio=new_production_qty / old_production_qty)
                quantity = wo.qty_production - wo.qty_produced
                if production.product_id.tracking == 'serial':
                    quantity = 1.0 if not float_is_zero(quantity, precision_digits=precision) else 0.0
                else:
                    quantity = quantity if (quantity > 0 and not float_is_zero(quantity, precision_digits=precision)) else 0
                wo._update_qty_producing(quantity)
                if wo.qty_produced < wo.qty_production and wo.state == 'done':
                    wo.state = 'progress'
                if wo.qty_produced == wo.qty_production and wo.state == 'progress':
                    wo.state = 'done'
                    if wo.next_work_order_id.state == 'pending':
                        wo.next_work_order_id.state = 'ready'
                # assign moves; last operation receive all unassigned moves
                # TODO: following could be put in a function as it is similar as code in _workorders_create
                # TODO: only needed when creating new moves
                moves_raw = production.move_raw_ids.filtered(lambda move: move.operation_id == operation and move.state not in ('done', 'cancel'))
                if wo == production.workorder_ids[-1]:
                    moves_raw |= production.move_raw_ids.filtered(lambda move: not move.operation_id)
                moves_finished = production.move_finished_ids.filtered(lambda move: move.operation_id == operation) #TODO: code does nothing, unless maybe by_products?
                moves_raw.mapped('move_line_ids').write({'workorder_id': wo.id})
                (moves_finished + moves_raw).write({'workorder_id': wo.id})

        # run scheduler for moves forecasted to not have enough in stock
        self.mo_id.filtered(lambda mo: mo.state in ['confirmed', 'progress']).move_raw_ids._trigger_scheduler()

        return {}
