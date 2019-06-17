# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    display_action_record_components = fields.Boolean(compute='_compute_display_action_record_components')
    display_view_subcontracted_move_lines = fields.Boolean(compute='_compute_display_view_subcontracted_move_lines')

    @api.depends('state')
    def _compute_display_action_record_components(self):
        for picking in self:
            # Hide if not encoding state
            if picking.state in ('draft', 'cancel', 'done'):
                continue
            if not picking._is_subcontract():
                continue
            # Hide if no move is tracked
            subcontracted_productions = picking._get_subcontracted_productions()
            subcontracted_moves = subcontracted_productions.mapped('move_raw_ids')
            subcontracted_moves |= subcontracted_productions.mapped('move_finished_ids')
            if all(subcontracted_move.has_tracking == 'none' for subcontracted_move in subcontracted_moves):
                continue
            # Hide if the production is to close
            if not subcontracted_productions.filtered(lambda mo: mo.state not in ('to_close', 'done')):
                continue
            picking.display_action_record_components = True

    @api.depends('state')
    def _compute_display_view_subcontracted_move_lines(self):
        for picking in self:
            # Hide if not encoding state
            if picking.state in ('draft', 'cancel'):
                continue
            if not picking._is_subcontract():
                continue
            # Hide until state done if no move is tracked, if tracked until something was produced
            subcontracted_productions = picking._get_subcontracted_productions()
            subcontracted_moves = subcontracted_productions.mapped('move_raw_ids')
            subcontracted_moves |= subcontracted_productions.mapped('move_finished_ids')
            if all(subcontracted_move.has_tracking == 'none' for subcontracted_move in subcontracted_moves):
                if picking.state != 'done':
                    continue
            # Hide if nothing was produced
            if all(subcontracted_move.quantity_done == 0 for subcontracted_move in subcontracted_moves):
                continue
            picking.display_view_subcontracted_move_lines = True

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------
    def action_done(self):
        for picking in self:
            subcontracted_productions = picking._get_subcontracted_productions()
            for subcontracted_production in subcontracted_productions:
                subcontracted_production.button_mark_done()
        return super(StockPicking, self).action_done()

    def action_view_subcontracted_move_lines(self):
        """ Returns a list view with the move lines of the subcontracted products. To find them, we
        look on the origin moves of the move lines of the picking if there is a manufacturing order.
        """
        self.ensure_one()
        subcontracted_productions = self._get_subcontracted_productions()
        subcontracted_move_lines = self.env['stock.move.line']
        for subcontracted_production in subcontracted_productions:
            subcontracted_move_lines |= subcontracted_production.move_raw_ids.mapped('move_line_ids')
            subcontracted_move_lines |= subcontracted_production.move_finished_ids.mapped('move_line_ids')
        action = self.env.ref('stock.stock_move_line_action').read()[0]
        action['context'] = {}
        action['domain'] = [('id', 'in', subcontracted_move_lines.ids)]
        return action

    def action_record_components(self):
        self.ensure_one()
        subcontracted_productions = self._get_subcontracted_productions()
        to_register = subcontracted_productions.filtered(lambda mo: mo.state not in ('to_close', 'done'))
        if to_register:
            mo = to_register[0]
            action = self.env.ref('mrp.act_mrp_product_produce').read()[0]
            action['context'] = dict(self.env.context, active_id=mo.id)
            return action

    # -------------------------------------------------------------------------
    # Subcontract helpers
    # -------------------------------------------------------------------------
    def _is_subcontract(self):
        self.ensure_one()
        if self.partner_id.type == 'subcontractor' and \
                self.picking_type_id.code == 'incoming':
            return True
        return False

    def _get_subcontracted_productions(self):
        self.ensure_one()
        return self.move_lines.mapped('move_orig_ids.production_id')

    def _prepare_subcontract_mo_vals(self, subcontract_move, bom):
        subcontract_move.ensure_one()
        product = subcontract_move.product_id
        warehouse = subcontract_move.warehouse_id or self.picking_type_id.warehouse_id
        vals = {
            'product_id': product.id,
            'product_uom_id': subcontract_move.product_uom.id,
            'bom_id': bom.id,
            'location_src_id': subcontract_move.picking_id.partner_id.property_stock_supplier.id,
            'location_dest_id': subcontract_move.location_id.id,
            'product_qty': subcontract_move.product_uom_qty,
            'picking_type_id': warehouse.subcontracting_type_id.id,
            'company_id': self.company_id.id,
        }
        return vals

    def _subcontracted_produce(self, subcontract_details):
        self.ensure_one()
        for move, bom in subcontract_details:
            mo = self.env['mrp.production'].create(self._prepare_subcontract_mo_vals(move, bom))
            self.env['stock.move'].create(mo._get_moves_raw_values())
            mo.action_confirm()

            # Link the finished to the receipt move.
            finished_move = mo.move_finished_ids.filtered(lambda m: m.product_id == move.product_id)
            finished_move.write({'move_dest_ids': [(4, move.id, False)]})
            mo.action_assign()

            # Only skip the produce wizard if no moves is tracked
            moves = mo.mapped('move_raw_ids') + mo.mapped('move_finished_ids')
            if any(move.has_tracking != 'none' for move in moves):
                continue
            for m in moves:
                m.quantity_done = m.product_uom_qty
