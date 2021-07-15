# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare, float_is_zero


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    display_action_record_components = fields.Boolean(compute='_compute_display_action_record_components')

    @api.depends('state')
    def _compute_display_action_record_components(self):
        for picking in self:
            # Hide if not encoding state
            if picking.state in ('draft', 'cancel', 'done'):
                picking.display_action_record_components = False
                continue
            if not picking._is_subcontract():
                picking.display_action_record_components = False
                continue
            # Hide if no components are track
            subcontracted_productions = picking._get_subcontracted_productions()
            component_sub_moves = subcontracted_productions.mapped('move_raw_ids')
            if all(subcontracted_move.has_tracking == 'none' for subcontracted_move in component_sub_moves):
                picking.display_action_record_components = False
                continue
            # Hide if all tracked product move line have a lot and all productions are in rigth state
            tracked_move_line = component_sub_moves.filtered(lambda sm: sm.has_tracking != 'none').move_line_ids
            if all(sub_mo.state in ('to_close', 'done') for sub_mo in subcontracted_productions)\
                    and all(sub_sml.lot_id for sub_sml in tracked_move_line):
                picking.display_action_record_components = False
                continue
            picking.display_action_record_components = True

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------
    def _action_done(self):
        res = super(StockPicking, self)._action_done()

        for move in self.move_lines.filtered(lambda move: move.is_subcontract):
            # Auto set qty_producing/lot_producing_id of MO if there isn't tracked component
            # If there is tracked component, the flow use subcontracting_record_component instead
            if move._has_tracked_subcontract_components():
                continue
            production = move.move_orig_ids.production_id.filtered(lambda p: p.state not in ('done', 'cancel'))[-1:]
            if not production:
                continue
            # Manage additional quantities
            quantity_done_move = move.product_uom._compute_quantity(move.quantity_done, production.product_uom_id)
            if float_compare(production.product_qty, quantity_done_move, precision_rounding=production.product_uom_id.rounding) == -1:
                change_qty = self.env['change.production.qty'].create({
                    'mo_id': production.id,
                    'product_qty': quantity_done_move
                })
                change_qty.with_context(skip_activity=True).change_prod_qty()
            # Create backorder MO for each move lines
            for move_line in move.move_line_ids:
                if move_line.lot_id:
                    production.lot_producing_id = move_line.lot_id
                production.qty_producing = move_line.product_uom_id._compute_quantity(move_line.qty_done, production.product_uom_id)
                production._set_qty_producing()
                if move_line != move.move_line_ids[-1]:
                    backorder = production._generate_backorder_productions(close_mo=False)
                    # The move_dest_ids won't be set because the _split filter out done move
                    backorder.move_finished_ids.filtered(lambda mo: mo.product_id == move.product_id).move_dest_ids = production.move_finished_ids.filtered(lambda mo: mo.product_id == move.product_id).move_dest_ids
                    production.product_qty = production.qty_producing
                    production = backorder

        for picking in self:
            productions_to_done = picking._get_subcontracted_productions()._subcontracting_filter_to_done()
            production_ids_backorder = []
            if not self.env.context.get('cancel_backorder'):
                production_ids_backorder = productions_to_done.filtered(lambda mo: mo.state == "progress").ids
            productions_to_done.with_context(subcontract_move_id=True, mo_ids_to_backorder=production_ids_backorder).button_mark_done()
            # For concistency, set the date on production move before the date
            # on picking. (Traceability report + Product Moves menu item)
            minimum_date = min(picking.move_line_ids.mapped('date'))
            production_moves = productions_to_done.move_raw_ids | productions_to_done.move_finished_ids
            production_moves.write({'date': minimum_date - timedelta(seconds=1)})
            production_moves.move_line_ids.write({'date': minimum_date - timedelta(seconds=1)})
        return res

    def action_record_components(self):
        self.ensure_one()
        for move in self.move_lines:
            if not move._has_tracked_subcontract_components():
                continue
            productions = move.move_orig_ids.production_id
            productions_to_done = productions._subcontracting_filter_to_done()
            production = (productions - productions_to_done)[-1:]
            if not production:
                continue
            return move._action_record_components()

    # -------------------------------------------------------------------------
    # Subcontract helpers
    # -------------------------------------------------------------------------
    def _is_subcontract(self):
        self.ensure_one()
        return self.picking_type_id.code == 'incoming' and any(m.is_subcontract for m in self.move_lines)

    def _get_subcontracted_productions(self):
        return self.move_lines.filtered(lambda move: move.is_subcontract).move_orig_ids.production_id

    def _get_warehouse(self, subcontract_move):
        return subcontract_move.warehouse_id or self.picking_type_id.warehouse_id

    def _prepare_subcontract_mo_vals(self, subcontract_move, bom):
        subcontract_move.ensure_one()
        group = self.env['procurement.group'].create({
            'name': self.name,
            'partner_id': self.partner_id.id,
        })
        product = subcontract_move.product_id
        warehouse = self._get_warehouse(subcontract_move)
        vals = {
            'company_id': subcontract_move.company_id.id,
            'procurement_group_id': group.id,
            'product_id': product.id,
            'product_uom_id': subcontract_move.product_uom.id,
            'bom_id': bom.id,
            'location_src_id': subcontract_move.picking_id.partner_id.with_company(subcontract_move.company_id).property_stock_subcontractor.id,
            'location_dest_id': subcontract_move.picking_id.partner_id.with_company(subcontract_move.company_id).property_stock_subcontractor.id,
            'product_qty': subcontract_move.product_uom_qty,
            'picking_type_id': warehouse.subcontracting_type_id.id,
            'date_planned_start': subcontract_move.date
        }
        return vals

    def _subcontracted_produce(self, subcontract_details):
        self.ensure_one()
        for move, bom in subcontract_details:
            mo = self.env['mrp.production'].with_company(move.company_id).create(self._prepare_subcontract_mo_vals(move, bom))
            self.env['stock.move'].create(mo._get_moves_raw_values())
            self.env['stock.move'].create(mo._get_moves_finished_values())
            mo.date_planned_finished = move.date  # Avoid to have the picking late depending of the MO
            mo.action_confirm()

            # Link the finished to the receipt move.
            finished_move = mo.move_finished_ids.filtered(lambda m: m.product_id == move.product_id)
            finished_move.write({'move_dest_ids': [(4, move.id, False)]})
            mo.action_assign()
