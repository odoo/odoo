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

    def _compute_display_assign_serial(self):
        super(StockMove, self)._compute_display_assign_serial()
        for move in self:
            if not move.is_subcontract:
                continue
            productions = move._get_subcontract_production()
            if not productions or move.has_tracking != 'serial':
                continue
            if productions._has_tracked_component() or productions[:1].consumption != 'strict':
                move.display_assign_serial = False

    def _compute_show_subcontracting_details_visible(self):
        """ Compute if the action button in order to see moves raw is visible """
        self.show_subcontracting_details_visible = False
        for move in self:
            if not move.is_subcontract:
                continue
            if float_is_zero(move.quantity_done, precision_rounding=move.product_uom.rounding):
                continue
            productions = move._get_subcontract_production()
            if not productions or (productions[:1].consumption == 'strict' and not productions[:1]._has_tracked_component()):
                continue
            move.show_subcontracting_details_visible = True

    def _compute_show_details_visible(self):
        """ If the move is subcontract and the components are tracked. Then the
        show details button is visible.
        """
        res = super(StockMove, self)._compute_show_details_visible()
        for move in self:
            if not move.is_subcontract:
                continue
            productions = move._get_subcontract_production()
            if not productions._has_tracked_component() and productions[:1].consumption == 'strict':
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
        if self.state != 'done' and (self._subcontrating_should_be_record() or self._subcontrating_can_be_record()):
            return self._action_record_components()
        action = super(StockMove, self).action_show_details()
        if self.is_subcontract and all(p._has_been_recorded() for p in self._get_subcontract_production()):
            action['views'] = [(self.env.ref('stock.view_stock_move_operations').id, 'form')]
            action['context'].update({
                'show_lots_m2o': self.has_tracking != 'none',
                'show_lots_text': False,
            })
        return action

    def action_show_subcontract_details(self):
        """ Display moves raw for subcontracted product self. """
        moves = self._get_subcontract_production().move_raw_ids
        tree_view = self.env.ref('mrp_subcontracting.mrp_subcontracting_move_tree_view')
        form_view = self.env.ref('mrp_subcontracting.mrp_subcontracting_move_form_view')
        ctx = dict(self._context, search_default_by_product=True)
        return {
            'name': _('Raw Materials for %s') % (self.product_id.display_name),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'views': [(tree_view.id, 'list'), (form_view.id, 'form')],
            'target': 'current',
            'domain': [('id', 'in', moves.ids)],
            'context': ctx
        }

    def _set_quantities_to_reservation(self):
        move_untouchable = self.filtered(lambda m: m.is_subcontract and m._get_subcontract_production()._has_tracked_component())
        return super(StockMove, self - move_untouchable)._set_quantities_to_reservation()

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
            if float_compare(move.product_qty, 0, precision_rounding=move.product_uom.rounding) <= 0:
                # If a subcontracted amount is decreased, don't create a MO that would be for a negative value.
                # We don't care if the MO decreases even when done since everything is handled through picking
                continue
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
        production = self._get_subcontract_production()[-1:]
        view = self.env.ref('mrp_subcontracting.mrp_production_subcontracting_form_view')
        context = dict(self._context)
        context.pop('default_picking_id', False)
        return {
            'name': _('Subcontract'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mrp.production',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': production.id,
            'context': context,
        }

    def _get_subcontract_bom(self):
        self.ensure_one()
        bom = self.env['mrp.bom'].sudo()._bom_subcontract_find(
            self.product_id,
            picking_type=self.picking_type_id,
            company_id=self.company_id.id,
            bom_type='subcontract',
            subcontractor=self.picking_id.partner_id,
        )
        return bom

    def _subcontrating_should_be_record(self):
        return self._get_subcontract_production().filtered(lambda p: not p._has_been_recorded() and p._has_tracked_component())

    def _subcontrating_can_be_record(self):
        return self._get_subcontract_production().filtered(lambda p: not p._has_been_recorded() and p.consumption != 'strict')

    def _get_subcontract_production(self):
        return self.filtered(lambda m: m.is_subcontract).move_orig_ids.production_id

    # TODO: To be deleted, use self._get_subcontract_production()._has_tracked_component() instead
    def _has_tracked_subcontract_components(self):
        return any(m.has_tracking != 'none' for m in self._get_subcontract_production().move_raw_ids)

    def _prepare_extra_move_vals(self, qty):
        vals = super(StockMove, self)._prepare_extra_move_vals(qty)
        vals['location_id'] = self.location_id.id
        return vals

    def _prepare_move_split_vals(self, qty):
        vals = super(StockMove, self)._prepare_move_split_vals(qty)
        vals['location_id'] = self.location_id.id
        return vals

    def _should_bypass_set_qty_producing(self):
        if (self.production_id | self.raw_material_production_id)._get_subcontract_move():
            return False
        return super()._should_bypass_set_qty_producing()

    def _should_bypass_reservation(self, forced_location=False):
        """ If the move is subcontracted then ignore the reservation. """
        should_bypass_reservation = super()._should_bypass_reservation(forced_location=forced_location)
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
