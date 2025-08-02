# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import fields, models, api, _
from odoo.exceptions import AccessError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import OrderedSet


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
            if not productions or move.has_tracking == 'none':
                continue
            if productions._has_tracked_component() or productions[:1].consumption != 'strict':
                move.display_assign_serial = False

    def _compute_show_subcontracting_details_visible(self):
        """ Compute if the action button in order to see moves raw is visible """
        self.show_subcontracting_details_visible = False
        for move in self:
            if not move.is_subcontract:
                continue
            if not move.picked or move.product_uom.is_zero(move.quantity):
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
            if self.env.user._is_portal():
                move.show_details_visible = any(not p._has_been_recorded() for p in move._get_subcontract_production())
                continue
            productions = move._get_subcontract_production()
            if not productions._has_tracked_component() and productions[:1].consumption == 'strict':
                continue
            move.show_details_visible = True
        return res

    def _set_quantity_done(self, qty):
        to_set_moves = self
        for move in self:
            if move.is_subcontract and move._subcontracting_possible_record():
                # If 'done' quantity is changed through the move, record components as if done through the wizard.
                move._auto_record_components(qty)
                to_set_moves -= move
        if to_set_moves:
            super(StockMove, to_set_moves)._set_quantity_done(qty)

    def _set_quantity(self):
        to_set_moves = self
        for move in self:
            if move.is_subcontract and move._subcontracting_possible_record():
                move_line_quantities = sum(move.move_line_ids.filtered(lambda ml: ml.picked).mapped('quantity'))
                delta_qty = move.quantity - move_line_quantities
                if move.product_uom.compare(delta_qty, 0) > 0:
                    move._auto_record_components(delta_qty)
                    to_set_moves -= move
                elif move.product_uom.compare(delta_qty, 0) < 0:
                    move.with_context(transfer_qty=True)._reduce_subcontract_order_qty(abs(delta_qty))
        if to_set_moves:
            super(StockMove, to_set_moves)._set_quantity()

    def _auto_record_components(self, qty):
        self.ensure_one()
        subcontracted_productions = self._get_subcontract_production()
        production = subcontracted_productions.filtered(lambda p: not p._has_been_recorded())[-1:]
        if not production:
            # If new quantity is over the already recorded quantity and we have no open production, then create a new one for the missing quantity.
            production = subcontracted_productions[-1:]
            production = production.sudo().with_context(allow_more=True)._split_productions({production: [production.qty_producing, qty]})[-1:]
        qty = self.product_uom._compute_quantity(qty, production.product_uom_id)

        if production.product_tracking == 'serial':
            qty = float_round(qty, precision_digits=0, rounding_method='UP')  # Makes no sense to have partial quantities for serial number
            if production.product_uom_id.compare(qty, production.product_qty) < 0:
                remaining_qty = production.product_qty - qty
                productions = production.sudo()._split_productions({production: ([1] * int(qty)) + [remaining_qty]})[:-1]
            else:
                productions = production.sudo().with_context(allow_more=True)._split_productions({production: ([1] * int(qty))})

            for production in productions:
                production.qty_producing = 1
                if not production.lot_producing_id:
                    production.action_generate_serial()
                production.with_context(cancel_backorder=False).subcontracting_record_component()
        else:
            production.qty_producing = qty
            if production.product_uom_id.compare(production.qty_producing, production.product_qty) > 0:
                self.env['change.production.qty'].with_context(skip_activity=True).create({
                    'mo_id': production.id,
                    'product_qty': qty
                }).change_prod_qty()
            if production.product_tracking == 'lot' and not production.lot_producing_id:
                production.action_generate_serial()
            production._set_qty_producing()
            production.with_context(cancel_backorder=False).subcontracting_record_component()

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for move, vals in zip(self, vals_list):
            if 'location_id' in default or not move.is_subcontract:
                continue
            vals['location_id'] = move.picking_id.location_id.id
        return vals_list

    def write(self, values):
        """ If the initial demand is updated then also update the linked
        subcontract order to the new quantity.
        """
        self._check_access_if_subcontractor(values)
        if 'product_uom_qty' in values and self.env.context.get('cancel_backorder') is not False and not self._context.get('extra_move_mode'):
            self.filtered(
                lambda m: m.is_subcontract and m.state not in ['draft', 'cancel', 'done']
                and m.product_uom.compare(m.product_uom_qty, values['product_uom_qty']) != 0
            )._update_subcontract_order_qty(values['product_uom_qty'])
        res = super().write(values)
        if 'date' in values:
            for move in self:
                if move.state in ('done', 'cancel') or not move.is_subcontract:
                    continue
                move.move_orig_ids.production_id.with_context(from_subcontract=True).filtered(lambda p: p.state not in ('done', 'cancel')).write({
                    'date_start': move.date,
                    'date_finished': move.date,
                })
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_access_if_subcontractor(vals)
        return super().create(vals_list)

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
        elif self.env.user._is_portal():
            action['views'] = [(self.env.ref('mrp_subcontracting.mrp_subcontracting_view_stock_move_operations').id, 'form')]
        return action

    def action_show_subcontract_details(self):
        """ Display moves raw for subcontracted product self. """
        moves = self._get_subcontract_production().move_raw_ids.filtered(lambda m: m.state != 'cancel')
        list_view = self.env.ref('mrp_subcontracting.mrp_subcontracting_move_tree_view')
        form_view = self.env.ref('mrp_subcontracting.mrp_subcontracting_move_form_view')
        ctx = dict(self._context, search_default_by_product=True)
        if self.env.user._is_portal():
            form_view = self.env.ref('mrp_subcontracting.mrp_subcontracting_portal_move_form_view')
            ctx.update(no_breadcrumbs=False)
        return {
            'name': _('Raw Materials for %s', self.product_id.display_name),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'views': [(list_view.id, 'list'), (form_view.id, 'form')],
            'target': 'current',
            'domain': [('id', 'in', moves.ids)],
            'context': ctx
        }

    def _action_cancel(self):
        productions_to_cancel_ids = OrderedSet()
        for move in self:
            if move.is_subcontract:
                active_productions = move.move_orig_ids.production_id.filtered(lambda p: p.state not in ('done', 'cancel'))
                moves_todo = self.env.context.get('moves_todo')
                not_todo_productions = active_productions.filtered(lambda p: p not in moves_todo.move_orig_ids.production_id) if moves_todo else active_productions
                if not_todo_productions:
                    productions_to_cancel_ids.update(not_todo_productions.ids)

        if productions_to_cancel_ids:
            productions_to_cancel = self.env['mrp.production'].browse(productions_to_cancel_ids)
            productions_to_cancel.with_context(skip_activity=True).action_cancel()

        return super()._action_cancel()

    def _action_confirm(self, merge=True, merge_into=False, create_proc=True):
        subcontract_details_per_picking = defaultdict(list)
        for move in self:
            if move.location_id.usage != 'supplier' or move.location_dest_id.usage == 'supplier':
                continue
            if move.move_orig_ids.production_id:
                continue
            bom = move._get_subcontract_bom()
            if not bom:
                continue
            company = move.company_id
            subcontracting_location = \
                move.picking_id.partner_id.with_company(company).property_stock_subcontractor \
                or company.subcontracting_location_id
            move.write({
                'is_subcontract': True,
                'location_id': subcontracting_location.id
            })
            move._action_assign()  # Re-reserve as the write on location_id will break the link
        res = super()._action_confirm(merge=merge, merge_into=merge_into, create_proc=create_proc)
        for move in res:
            if move.is_subcontract:
                subcontract_details_per_picking[move.picking_id].append((move, move._get_subcontract_bom()))
        for picking, subcontract_details in subcontract_details_per_picking.items():
            picking._subcontracted_produce(subcontract_details)

        if subcontract_details_per_picking:
            self.env['stock.picking'].concat(*list(subcontract_details_per_picking.keys())).action_assign()
        return res

    def _action_record_components(self):
        self.ensure_one()
        production = self._get_subcontract_production()[-1:]
        view = self.env.ref('mrp_subcontracting.mrp_production_subcontracting_form_view')
        if self.env.user._is_portal():
            view = self.env.ref('mrp_subcontracting.mrp_production_subcontracting_portal_form_view')
        context = dict(self._context)
        context.pop('skip_consumption', False)
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

    def _subcontracting_possible_record(self):
        return self._get_subcontract_production().filtered(lambda p: p._has_tracked_component() or p.consumption != 'strict')

    def _get_subcontract_production(self):
        return self.filtered(lambda m: m.is_subcontract).move_orig_ids.production_id

    # TODO: To be deleted, use self._get_subcontract_production()._has_tracked_component() instead
    def _has_tracked_subcontract_components(self):
        return any(m.has_tracking != 'none' for m in self._get_subcontract_production().move_raw_ids)

    def _prepare_move_split_vals(self, qty):
        vals = super(StockMove, self)._prepare_move_split_vals(qty)
        vals['location_id'] = self.location_id.id
        return vals

    def _prepare_procurement_values(self):
        res = super()._prepare_procurement_values()
        if self.raw_material_production_id.subcontractor_id:
            res['warehouse_id'] = self.picking_type_id.warehouse_id
        return res

    def _should_bypass_reservation(self, forced_location=False):
        """ If the move is subcontracted then ignore the reservation. """
        should_bypass_reservation = super()._should_bypass_reservation(forced_location=forced_location)
        if not should_bypass_reservation and self.is_subcontract:
            return True
        return should_bypass_reservation

    def _get_available_move_lines(self, assigned_moves_ids, partially_available_moves_ids):
        return super(StockMove, self.filtered(lambda m: not m.is_subcontract))._get_available_move_lines(assigned_moves_ids, partially_available_moves_ids)

    def _update_subcontract_order_qty(self, new_quantity):
        for move in self:
            quantity_to_remove = move.product_uom_qty - new_quantity
            if not move.product_uom.is_zero(quantity_to_remove):
                move._reduce_subcontract_order_qty(quantity_to_remove)

    def _reduce_subcontract_order_qty(self, quantity_to_remove):
        self.ensure_one()
        productions = self.move_orig_ids.production_id.filtered(lambda p: p.state not in ('done', 'cancel'))[::-1]
        wip_production = productions[0] if self._context.get('transfer_qty') and len(productions) > 1 else self.env['mrp.production']

        # Transfer removed qty to WIP production
        if wip_production:
            self.env['change.production.qty'].with_context(skip_activity=True).create({
                'mo_id': wip_production.id,
                'product_qty': wip_production.product_qty + quantity_to_remove
            }).change_prod_qty()

        # Cancel productions until reach new_quantity
        for production in (productions - wip_production):
            if float_compare(quantity_to_remove, production.product_qty, precision_rounding=production.product_uom_id.rounding) >= 0:
                quantity_to_remove -= production.product_qty
                production.with_context(skip_activity=True).action_cancel()
            else:
                if production.product_uom_id.is_zero(quantity_to_remove):
                    # No need to do change_prod_qty for no change at all.
                    break
                self.env['change.production.qty'].with_context(skip_activity=True).create({
                    'mo_id': production.id,
                    'product_qty': production.product_qty - quantity_to_remove
                }).change_prod_qty()
                break

    def _check_access_if_subcontractor(self, vals):
        if self.env.user._is_portal() and not self.env.su:
            if vals.get('state') == 'done':
                raise AccessError(_("Portal users cannot create a stock move with a state 'Done' or change the current state to 'Done'."))

    def _is_subcontract_return(self):
        self.ensure_one()
        subcontracting_location = self.picking_id.partner_id.with_company(self.company_id).property_stock_subcontractor
        return (
                not self.is_subcontract
                and self.origin_returned_move_id.is_subcontract
                and self.location_dest_id.id == subcontracting_location.id
        )
