# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
from dateutil.relativedelta import relativedelta


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.depends('picking_type_id', 'partner_id')
    def _compute_location_id(self):
        super()._compute_location_id()

        for picking in self:
            # If this is a subcontractor resupply transfer, set the destination location
            # to the vendor subcontractor location
            subcontracting_resupply_type_id = picking.picking_type_id.warehouse_id.subcontracting_resupply_type_id
            if picking.picking_type_id == subcontracting_resupply_type_id\
                and picking.partner_id.property_stock_subcontractor:
                picking.location_dest_id = picking.partner_id.property_stock_subcontractor


    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------
    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        for picking in self:
            productions_to_done = picking._get_subcontract_production().sudo()
            productions_to_done.button_mark_done()
            # For concistency, set the date on production move before the date
            # on picking. (Traceability report + Product Moves menu item)
            production_moves = productions_to_done.move_raw_ids | productions_to_done.move_finished_ids
            if production_moves:
                minimum_date = min(picking.move_line_ids.mapped('date'))
                production_moves.write({'date': minimum_date - timedelta(seconds=1)})
                production_moves.move_line_ids.write({'date': minimum_date - timedelta(seconds=1)})

        return res

    @api.depends('move_ids.is_subcontract', 'move_ids.has_tracking')
    def _compute_show_lots_text(self):
        super()._compute_show_lots_text()
        for picking in self:
            if any(move.is_subcontract and move.has_tracking != 'none' for move in picking.move_ids):
                picking.show_lots_text = False

    # -------------------------------------------------------------------------
    # Subcontract helpers
    # -------------------------------------------------------------------------
    def _is_subcontract(self):
        self.ensure_one()
        return self.picking_type_id.code == 'incoming' and any(m.is_subcontract for m in self.move_ids)

    def _get_subcontract_production(self):
        return self.move_ids._get_subcontract_production()

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
        subcontracting_location = \
            subcontract_move.picking_id.partner_id.with_company(subcontract_move.company_id).property_stock_subcontractor \
            or subcontract_move.company_id.subcontracting_location_id
        vals = {
            'company_id': subcontract_move.company_id.id,
            'procurement_group_id': group.id,
            'subcontractor_id': subcontract_move.picking_id.partner_id.commercial_partner_id.id,
            'picking_ids': [subcontract_move.picking_id.id],
            'product_id': product.id,
            'product_uom_id': subcontract_move.product_uom.id,
            'bom_id': bom.id,
            'location_src_id': subcontracting_location.id,
            'location_dest_id': subcontracting_location.id,
            'product_qty': subcontract_move.product_uom_qty or subcontract_move.quantity,
            'picking_type_id': warehouse.subcontracting_type_id.id,
            'date_start': subcontract_move.date - relativedelta(days=bom.produce_delay),
            'origin': self.name,
        }
        return vals

    def _get_subcontract_mo_confirmation_ctx(self):
        if self._is_subcontract() and not self.env.context.get('cancel_backorder', True):
            # Do not trigger rules on raw moves when creating backorder for a subcontract receipt.
            return {'no_procurement': True}
        return {}  # To override in mrp_subcontracting_purchase

    def _subcontracted_produce(self, subcontract_details):
        self.ensure_one()
        group_move = defaultdict(list)
        group_by_company = defaultdict(list)
        for move, bom in subcontract_details:
            if move.move_orig_ids.production_id:
                # Magic spicy sauce for the backorder case:
                # To ensure correct splitting of the component moves of the SBC MO, we will invoke a split of the SBC
                # MO here directly and then link the backorder MO to the backorder move.
                # If we would just run _subcontracted_produce as usual for the newly created SBC receipt move, any
                # reservations of raw component moves of the SBC MO would not be preserved properly (for example when
                # using resupply subcontractor on order)
                production_to_split = move.move_orig_ids[0].production_id
                original_qty = move.move_orig_ids[0].product_qty
                move.move_orig_ids = False
                _, new_mo = production_to_split.with_context(allow_more=True)._split_productions({production_to_split: [original_qty, move.product_qty]})
                new_mo.move_finished_ids.move_dest_ids = move
                continue
            quantity = move.product_qty or move.quantity
            if move.product_uom.compare(quantity, 0) <= 0:
                # If a subcontracted amount is decreased, don't create a MO that would be for a negative value.
                continue

            mo_subcontract = self._prepare_subcontract_mo_vals(move, bom)
            # Link the move to the id of the MO's procurement group
            group_move[mo_subcontract['procurement_group_id']] = move
            # Group the MO by company
            group_by_company[move.company_id.id].append(mo_subcontract)

        all_mo = set()
        for company, group in group_by_company.items():
            grouped_mo = self.env['mrp.production'].with_company(company).create(group)
            all_mo.update(grouped_mo.ids)

        all_mo = self.env['mrp.production'].browse(sorted(all_mo))
        ctx = self._get_subcontract_mo_confirmation_ctx()
        all_mo.with_context(ctx).action_confirm()
        if ctx.get('no_procurement'):
            # Make sure to check availability to the backorder
            all_mo.action_assign()

        for mo in all_mo:
            move = group_move[mo.procurement_group_id.id][0]
            mo.write({'date_finished': move.date})
            finished_move = mo.move_finished_ids.filtered(lambda m: m.product_id == move.product_id)
            finished_move.write({'move_dest_ids': [(4, move.id, False)]})

        all_mo.action_assign()
