# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools.float_utils import float_compare
from dateutil.relativedelta import relativedelta


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    show_subcontracting_details_visible = fields.Boolean(compute='_compute_show_subcontracting_details_visible')

    @api.depends('move_ids.show_subcontracting_details_visible')
    def _compute_show_subcontracting_details_visible(self):
        for picking in self:
            picking.show_subcontracting_details_visible = any(m.show_subcontracting_details_visible for m in picking.move_ids)

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

    @api.depends('move_ids.is_subcontract', 'move_ids.has_tracking')
    def _compute_show_lots_text(self):
        super()._compute_show_lots_text()
        for picking in self:
            if any(move.is_subcontract and move.has_tracking != 'none' for move in picking.move_ids):
                picking.show_lots_text = False

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

    def action_show_subcontract_details(self):
        productions = self._get_subcontract_production().filtered(lambda m: m.state != 'cancel')
        ctx = {"mrp_subcontracting": True}
        if self.env.user._is_portal():
            form_view_id = self.env.ref('mrp_subcontracting.mrp_production_subcontracting_portal_form_view')
            ctx.update(no_breadcrumbs=False)
        else:
            form_view_id = self.env.ref('mrp_subcontracting.mrp_production_subcontracting_form_view')
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'target': 'current',
            'context': ctx
        }
        if len(productions) > 1:
            action.update({
                'name': _('Subcontracting MOs'),
                'views': [
                    (self.env.ref('mrp_subcontracting.mrp_production_subcontracting_tree_view').id, 'list'),
                    (form_view_id.id, 'form'),
                ],
                'domain': [('id', 'in', productions.ids)],
            })
        elif len(productions) == 1:
            action.update({
                'views': [(form_view_id.id, 'form')],
                'res_id': productions.id,
            })
        else:
            return {}
        return action

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
        reference = self.env['stock.reference'].create({
            'name': self.name,
            'move_ids': [Command.link(subcontract_move.id)],
        })
        product = subcontract_move.product_id
        warehouse = self._get_warehouse(subcontract_move)
        subcontracting_location = \
            subcontract_move.picking_id.partner_id.with_company(subcontract_move.company_id).property_stock_subcontractor \
            or subcontract_move.company_id.subcontracting_location_id
        vals = {
            'company_id': subcontract_move.company_id.id,
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
            'reference_ids': [Command.link(reference.id)],
        }
        return vals

    def _get_subcontract_mo_confirmation_ctx(self):
        if self._is_subcontract() and not self.env.context.get('cancel_backorder', True):
            # Do not trigger rules on raw moves when creating backorder for a subcontract receipt.
            return {'no_procurement': True}
        return {}  # To override in mrp_subcontracting_purchase

    def _subcontracted_produce(self, subcontract_details):
        self.ensure_one()
        group_by_company = defaultdict(lambda: ([], []))
        for move, bom in subcontract_details:
            if move.move_orig_ids.production_id:
                if len(move.move_orig_ids.move_dest_ids) > 1:
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
                else:
                    # do not create extra production for move that have their quantity updated
                    return
            quantity = move.product_qty or move.quantity
            if move.product_uom.compare(quantity, 0) <= 0:
                # If a subcontracted amount is decreased, don't create a MO that would be for a negative value.
                continue

            mo_subcontract = self._prepare_subcontract_mo_vals(move, bom)
            # Group the MO by company
            group_by_company[move.company_id.id][0].append(mo_subcontract)
            group_by_company[move.company_id.id][1].append(move)

        for company, group in group_by_company.items():
            vals_list, moves = group
            grouped_mo = self.env['mrp.production'].with_company(company).create(vals_list)
            grouped_mo.with_context(self._get_subcontract_mo_confirmation_ctx()).action_confirm()
            for mo, move in zip(grouped_mo, moves):
                mo.date_finished = move.date
                finished_move = mo.move_finished_ids.filtered(lambda m: m.product_id == move.product_id)
                finished_move.move_dest_ids = [Command.link(move.id)]
            grouped_mo.action_assign()
