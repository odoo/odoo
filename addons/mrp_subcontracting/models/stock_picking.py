# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    display_action_record_components = fields.Boolean(compute='_compute_display_action_record_components')

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

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------
    def action_done(self):
        res = super(StockPicking, self).action_done()
        for picking in self:
            subcontracted_productions = picking._get_subcontracted_productions()
            for subcontracted_production in subcontracted_productions:
                subcontracted_production.button_mark_done()
        return res

    def action_record_components(self):
        self.ensure_one()
        for move in self.move_lines:
            production = move.move_orig_ids.production_id
            if not production or production.state in ('done', 'to_close'):
                continue
            action = self.env.ref('mrp.act_mrp_product_produce').read()[0]
            action['context'] = dict(
                self.env.context,
                active_id=production.id,
                default_subcontract_move_id=move.id
            )
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
            'picking_type_id': warehouse.subcontracting_type_id.id
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
