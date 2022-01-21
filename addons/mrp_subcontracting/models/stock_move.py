# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero


class StockMove(models.Model):
    _inherit = 'stock.move'

    is_subcontract = fields.Boolean('The move is a subcontract receipt')
    show_subcontracting_details_visible = fields.Boolean(
        compute='_compute_show_subcontracting_details_visible'
    )

    def _compute_show_subcontracting_details_visible(self):
        """ Compute if the action button in order to see moves raw is visible """
        for move in self:
            if move.is_subcontract and move._has_tracked_subcontract_components() and\
                    not float_is_zero(move.quantity_done, precision_rounding=move.product_uom.rounding):
                move.show_subcontracting_details_visible = True
            else:
                move.show_subcontracting_details_visible = False

    def _compute_show_details_visible(self):
        """ If the move is subcontract and the components are tracked. Then the
        show details button is visible.
        """
        res = super(StockMove, self)._compute_show_details_visible()
        for move in self:
            if not move.is_subcontract:
                continue
            if not move._has_tracked_subcontract_components():
                continue
            move.show_details_visible = True
        return res

    def copy(self, default=None):
        self.ensure_one()
        if not self.is_subcontract or 'location_id' in default:
            return super(StockMove, self).copy(default=default)
        if not default:
            default = {}
        default['location_id'] = self.picking_id.location_id.id
        return super(StockMove, self).copy(default=default)

    def write(self, values):
        """ If the initial demand is updated then also update the linked
        subcontract order to the new quantity.
        """
        if 'product_uom_qty' in values and self.env.context.get('cancel_backorder') is not False:
            self.filtered(lambda m: m.is_subcontract and m.state not in ['draft', 'cancel', 'done'])._update_subcontract_order_qty(values['product_uom_qty'])
        res = super().write(values)
        if 'date' in values:
            for move in self:
                if move.state in ('done', 'cancel') or not move.is_subcontract:
                    continue
                move.move_orig_ids.production_id.filtered(lambda p: p.state not in ('done', 'cancel')).write({
                    'date_planned_finished': move.date,
                    'date_planned_start': move.date,
                })
        return res

    def action_show_details(self):
        """ Open the produce wizard in order to register tracked components for
        subcontracted product. Otherwise use standard behavior.
        """
        self.ensure_one()
        if self._has_components_to_record():
            return self._action_record_components()
        action = super(StockMove, self).action_show_details()
        if self.is_subcontract and self._has_tracked_subcontract_components():
            action['views'] = [(self.env.ref('stock.view_stock_move_operations').id, 'form')]
            action['context'].update({
                'show_lots_m2o': self.has_tracking != 'none',
                'show_lots_text': False,
            })
        return action

    def action_show_subcontract_details(self):
        """ Display moves raw for subcontracted product self. """
        moves = self.move_orig_ids.production_id.move_raw_ids
        tree_view = self.env.ref('mrp_subcontracting.mrp_subcontracting_move_tree_view')
        form_view = self.env.ref('mrp_subcontracting.mrp_subcontracting_move_form_view')
        ctx = dict(self._context, search_default_by_product=True, subcontract_move_id=self.id)
        return {
            'name': _('Raw Materials for %s') % (self.product_id.display_name),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'views': [(tree_view.id, 'list'), (form_view.id, 'form')],
            'target': 'current',
            'domain': [('id', 'in', moves.ids)],
            'context': ctx
        }

    def _action_cancel(self):
        for move in self:
            if move.is_subcontract:
                active_production = move.move_orig_ids.production_id.filtered(lambda p: p.state not in ('done', 'cancel'))
                moves = self.env.context.get('moves_todo')
                if not moves or active_production not in moves.move_orig_ids.production_id:
                    active_production.with_context(skip_activity=True).action_cancel()
        return super()._action_cancel()

    def _action_confirm(self, merge=True, merge_into=False):
        subcontract_details_per_picking = defaultdict(list)
        move_to_not_merge = self.env['stock.move']
        for move in self:
            if move.location_id.usage != 'supplier' or move.location_dest_id.usage == 'supplier':
                continue
            if move.move_orig_ids.production_id:
                continue
            bom = move._get_subcontract_bom()
            if not bom:
                continue
            if float_is_zero(move.product_qty, precision_rounding=move.product_uom.rounding) and\
                    move.picking_id.immediate_transfer is True:
                raise UserError(_("To subcontract, use a planned transfer."))
            subcontract_details_per_picking[move.picking_id].append((move, bom))
            move.write({
                'is_subcontract': True,
                'location_id': move.picking_id.partner_id.with_company(move.company_id).property_stock_subcontractor.id
            })
            move_to_not_merge |= move
        for picking, subcontract_details in subcontract_details_per_picking.items():
            picking._subcontracted_produce(subcontract_details)

        # We avoid merging move due to complication with stock.rule.
        res = super(StockMove, move_to_not_merge)._action_confirm(merge=False)
        res |= super(StockMove, self - move_to_not_merge)._action_confirm(merge=merge, merge_into=merge_into)
        if subcontract_details_per_picking:
            self.env['stock.picking'].concat(*list(subcontract_details_per_picking.keys())).action_assign()
        return res

    def _action_record_components(self):
        self.ensure_one()
        production = self.move_orig_ids.production_id[-1:]
        view = self.env.ref('mrp_subcontracting.mrp_production_subcontracting_form_view')
        return {
            'name': _('Subcontract'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mrp.production',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': production.id,
            'context': dict(self.env.context, subcontract_move_id=self.id),
        }

    def _get_subcontract_bom(self):
        self.ensure_one()
        bom = self.env['mrp.bom'].sudo()._bom_subcontract_find(
            product=self.product_id,
            picking_type=self.picking_type_id,
            company_id=self.company_id.id,
            bom_type='subcontract',
            subcontractor=self.picking_id.partner_id,
        )
        return bom

    def _has_components_to_record(self):
        """ Returns true if the move has still some tracked components to record. """
        self.ensure_one()
        if not self.is_subcontract:
            return False
        rounding = self.product_uom.rounding
        production = self.move_orig_ids.production_id[-1:]
        return self._has_tracked_subcontract_components() and\
            float_compare(production.qty_produced, production.product_uom_qty, precision_rounding=rounding) < 0 and\
            float_compare(self.quantity_done, self.product_uom_qty, precision_rounding=rounding) < 0

    def _has_tracked_subcontract_components(self):
        self.ensure_one()
        return any(m.has_tracking != 'none' for m in self.move_orig_ids.production_id.move_raw_ids)

    def _prepare_extra_move_vals(self, qty):
        vals = super(StockMove, self)._prepare_extra_move_vals(qty)
        vals['location_id'] = self.location_id.id
        return vals

    def _prepare_move_split_vals(self, qty):
        vals = super(StockMove, self)._prepare_move_split_vals(qty)
        vals['location_id'] = self.location_id.id
        return vals

    def _should_bypass_set_qty_producing(self):
        if self.env.context.get('subcontract_move_id'):
            return False
        return super()._should_bypass_set_qty_producing()

    def _should_bypass_reservation(self):
        """ If the move is subcontracted then ignore the reservation. """
        should_bypass_reservation = super(StockMove, self)._should_bypass_reservation()
        if not should_bypass_reservation and self.is_subcontract:
            return True
        return should_bypass_reservation

    def _update_subcontract_order_qty(self, new_quantity):
        for move in self:
            quantity_to_remove = move.product_uom_qty - new_quantity
            productions = move.move_orig_ids.production_id.filtered(lambda p: p.state not in ('done', 'cancel'))[::-1]
            # Cancel productions until reach new_quantity
            for production in productions:
                if quantity_to_remove <= 0.0:
                    break
                if quantity_to_remove >= production.product_qty:
                    quantity_to_remove -= production.product_qty
                    production.with_context(skip_activity=True).action_cancel()
                else:
                    self.env['change.production.qty'].with_context(skip_activity=True).create({
                        'mo_id': production.id,
                        'product_qty': production.product_uom_qty - quantity_to_remove
                    }).change_prod_qty()
