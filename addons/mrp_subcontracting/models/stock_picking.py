# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import float_is_zero


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
            subcontracted_moves = subcontracted_productions.mapped('move_raw_ids')
            if all(subcontracted_move.has_tracking == 'none' for subcontracted_move in subcontracted_moves):
                picking.display_action_record_components = False
                continue
            # Hide if the production is to close
            if not subcontracted_productions.filtered(lambda mo: mo.state not in ('to_close', 'done')):
                picking.display_action_record_components = False
                continue
            picking.display_action_record_components = True

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------
    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        productions = self.env['mrp.production']
        for picking in self:
            for move in picking.move_lines:
                if not move.is_subcontract:
                    continue
                production = move.move_orig_ids.production_id.filtered(lambda p: p.state not in ('done', 'cancel'))
                if len(production) > 1:
                    production = production[-1]
                if move._has_tracked_subcontract_components():
                    move.move_orig_ids.filtered(lambda m: m.state not in ('done', 'cancel')).move_line_ids.unlink()
                    move_finished_ids = move.move_orig_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
                    for ml in move.move_line_ids:
                        ml.copy({
                            'picking_id': False,
                            'production_id': move_finished_ids.production_id.id,
                            'move_id': move_finished_ids.id,
                            'qty_done': ml.qty_done,
                            'result_package_id': False,
                            'location_id': move_finished_ids.location_id.id,
                            'location_dest_id': move_finished_ids.location_dest_id.id,
                        })
                else:
                    if not move.move_line_ids.lot_id:
                        qty_done_production_uom = move.product_uom._compute_quantity(move.quantity_done, production.product_uom_id)
                        production.qty_producing += qty_done_production_uom
                        for move in (production.move_raw_ids | production.move_finished_ids.filtered(lambda m: m.product_id != production.product_id)):
                            if move.state in ('done', 'cancel'):
                                continue
                            if float_is_zero(move.product_uom_qty, precision_rounding=move.product_uom.rounding):
                                continue
                            new_qty = production.product_uom_id._compute_quantity(
                                (production.qty_producing - production.qty_produced) * move.unit_factor, production.product_uom_id,
                                rounding_method='HALF-UP')
                            move.move_line_ids.filtered(lambda ml: ml.state not in ('done', 'cancel')).qty_done = 0
                            move.move_line_ids = move._set_quantity_done_prepare_vals(new_qty)
                productions |= production
            for subcontracted_production in productions:
                if subcontracted_production.state == 'progress':
                    subcontracted_production._post_inventory()
                else:
                    subcontracted_production.button_mark_done()
                # For concistency, set the date on production move before the date
                # on picking. (Tracability report + Product Moves menu item)
                minimum_date = min(picking.move_line_ids.mapped('date'))
                production_moves = subcontracted_production.move_raw_ids | subcontracted_production.move_finished_ids
                production_moves.write({'date': minimum_date - timedelta(seconds=1)})
                production_moves.move_line_ids.write({'date': minimum_date - timedelta(seconds=1)})
        return res

    def action_record_components(self):
        self.ensure_one()
        for move in self.move_lines:
            if not move._has_tracked_subcontract_components():
                continue
            production = move.move_orig_ids.production_id
            if not production or production.state in ('done', 'to_close'):
                continue
            return move._action_record_components()

    # -------------------------------------------------------------------------
    # Subcontract helpers
    # -------------------------------------------------------------------------
    def _is_subcontract(self):
        self.ensure_one()
        return self.picking_type_id.code == 'incoming' and any(m.is_subcontract for m in self.move_lines)

    def _get_subcontracted_productions(self):
        self.ensure_one()
        return self.move_lines.mapped('move_orig_ids.production_id')

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
            'picking_type_id': warehouse.subcontracting_type_id.id
        }
        return vals

    def _subcontracted_produce(self, subcontract_details):
        self.ensure_one()
        for move, bom in subcontract_details:
            mo = self.env['mrp.production'].with_company(move.company_id).create(self._prepare_subcontract_mo_vals(move, bom))
            self.env['stock.move'].create(mo._get_moves_raw_values())
            self.env['stock.move'].create(mo._get_moves_finished_values())
            mo.action_confirm()

            # Link the finished to the receipt move.
            finished_move = mo.move_finished_ids.filtered(lambda m: m.product_id == move.product_id)
            finished_move.write({'move_dest_ids': [(4, move.id, False)]})
            mo.action_assign()
