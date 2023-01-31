# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
from dateutil.relativedelta import relativedelta


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # override existing field domains to prevent suboncontracting production lines from showing in Detailed Operations tab
    move_line_nosuggest_ids = fields.One2many(
        domain=['&', '|', ('location_dest_id.usage', '!=', 'production'), ('move_id.picking_code', '!=', 'outgoing'),
                     '|', ('product_qty', '=', 0.0), '&', ('product_qty', '!=', 0.0), ('qty_done', '!=', 0.0)])
    move_line_ids_without_package = fields.One2many(
        domain=['&', '|', ('location_dest_id.usage', '!=', 'production'), ('move_id.picking_code', '!=', 'outgoing'),
                     '|', ('package_level_id', '=', False), ('picking_type_entire_packs', '=', False)])
    display_action_record_components = fields.Selection(
        [('hide', 'Hide'), ('facultative', 'Facultative'), ('mandatory', 'Mandatory')],
        compute='_compute_display_action_record_components')

    @api.depends('state', 'move_lines')
    def _compute_display_action_record_components(self):
        self.display_action_record_components = 'hide'
        for picking in self:
            # Hide if not encoding state or it is not a subcontracting picking
            if picking.state in ('draft', 'cancel', 'done') or not picking._is_subcontract():
                continue
            subcontracted_moves = picking.move_lines.filtered(lambda m: m.is_subcontract)
            if subcontracted_moves._subcontrating_should_be_record():
                picking.display_action_record_components = 'mandatory'
                continue
            if subcontracted_moves._subcontrating_can_be_record():
                picking.display_action_record_components = 'facultative'

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------
    def _action_done(self):
        res = super(StockPicking, self)._action_done()

        for move in self.move_lines.filtered(lambda move: move.is_subcontract):
            # Auto set qty_producing/lot_producing_id of MO wasn't recorded
            # manually (if the flexible + record_component or has tracked component)
            productions = move._get_subcontract_production()
            recorded_productions = productions.filtered(lambda p: p._has_been_recorded())
            recorded_qty = sum(recorded_productions.mapped('qty_producing'))
            sm_done_qty = sum(productions._get_subcontract_move().mapped('quantity_done'))
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if float_compare(recorded_qty, sm_done_qty, precision_digits=rounding) >= 0:
                continue
            production = productions - recorded_productions
            if not production:
                continue
            if len(production) > 1:
                raise UserError("It shouldn't happen to have multiple production to record for the same subcontracted move")
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
                production.subcontracting_has_been_recorded = True
                if move_line != move.move_line_ids[-1]:
                    backorder = production._generate_backorder_productions(close_mo=False)
                    # The move_dest_ids won't be set because the _split filter out done move
                    backorder.move_finished_ids.filtered(lambda mo: mo.product_id == move.product_id).move_dest_ids = production.move_finished_ids.filtered(lambda mo: mo.product_id == move.product_id).move_dest_ids
                    production.product_qty = production.qty_producing
                    production = backorder

        for picking in self:
            productions_to_done = picking._get_subcontract_production()._subcontracting_filter_to_done()
            if not productions_to_done:
                continue
            productions_to_done = productions_to_done.sudo()
            production_ids_backorder = []
            if not self.env.context.get('cancel_backorder'):
                production_ids_backorder = productions_to_done.filtered(lambda mo: mo.state == "progress").ids
            productions_to_done.with_context(mo_ids_to_backorder=production_ids_backorder).button_mark_done()
            # For concistency, set the date on production move before the date
            # on picking. (Traceability report + Product Moves menu item)
            minimum_date = min(picking.move_line_ids.mapped('date'))
            production_moves = productions_to_done.move_raw_ids | productions_to_done.move_finished_ids
            production_moves.write({'date': minimum_date - timedelta(seconds=1)})
            production_moves.move_line_ids.write({'date': minimum_date - timedelta(seconds=1)})
        return res

    def action_record_components(self):
        self.ensure_one()
        move_subcontracted = self.move_lines.filtered(lambda m: m.is_subcontract)
        for move in move_subcontracted:
            production = move._subcontrating_should_be_record()
            if production:
                return move._action_record_components()
        for move in move_subcontracted:
            production = move._subcontrating_can_be_record()
            if production:
                return move._action_record_components()
        raise UserError(_("Nothing to record"))

    # -------------------------------------------------------------------------
    # Subcontract helpers
    # -------------------------------------------------------------------------
    def _is_subcontract(self):
        self.ensure_one()
        return self.picking_type_id.code == 'incoming' and any(m.is_subcontract for m in self.move_lines)

    def _get_subcontract_production(self):
        return self.move_lines._get_subcontract_production()

    def _get_warehouse(self, subcontract_move):
        return subcontract_move.warehouse_id or self.picking_type_id.warehouse_id or subcontract_move.move_dest_ids.picking_type_id.warehouse_id

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
            'date_planned_start': subcontract_move.date - relativedelta(days=product.produce_delay)
        }
        return vals

    def _subcontracted_produce(self, subcontract_details):
        self.ensure_one()
        for move, bom in subcontract_details:
            if float_compare(move.product_qty, 0, precision_rounding=move.product_uom.rounding) <= 0:
                # If a subcontracted amount is decreased, don't create a MO that would be for a negative value.
                continue
            mo = self.env['mrp.production'].with_company(move.company_id).create(self._prepare_subcontract_mo_vals(move, bom))
            self.env['stock.move'].create(mo._get_moves_raw_values())
            self.env['stock.move'].create(mo._get_moves_finished_values())
            mo.date_planned_finished = move.date  # Avoid to have the picking late depending of the MO
            mo.action_confirm()

            # Link the finished to the receipt move.
            finished_move = mo.move_finished_ids.filtered(lambda m: m.product_id == move.product_id)
            finished_move.write({'move_dest_ids': [(4, move.id, False)]})
            mo.action_assign()
