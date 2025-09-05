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

    def _compute_show_subcontracting_details_visible(self):
        """ Compute if the action button in order to see moves raw is visible """
        self.show_subcontracting_details_visible = False
        for move in self:
            if not move.is_subcontract:
                continue
            if not move.move_line_ids or move.product_uom.is_zero(move.quantity):
                continue
            productions = move._get_subcontract_production().filtered(lambda m: m.state != 'cancel')
            if not productions:
                continue
            move.show_subcontracting_details_visible = True

    @api.depends('is_subcontract')
    def _compute_show_info(self):
        super()._compute_show_info()
        subcontract_moves = self.filtered(lambda m: m.is_subcontract and m.show_lots_text)
        subcontract_moves.show_lots_text = False
        subcontract_moves.show_lots_m2o = True

    @api.depends('is_subcontract', 'has_tracking')
    def _compute_is_quantity_done_editable(self):
        done_moves = self.env['stock.move']
        for move in self:
            if move.is_subcontract:
                move.is_quantity_done_editable = move.has_tracking == 'none'
                done_moves |= move
        return super(StockMove, self - done_moves)._compute_is_quantity_done_editable()

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for move, vals in zip(self, vals_list):
            if 'location_id' in default or not move.is_subcontract:
                continue
            vals['location_id'] = move.picking_id.location_id.id
        return vals_list

    def write(self, vals):
        """ If the initial demand is updated then also update the linked
        subcontract order to the new quantity.
        """
        self._check_access_if_subcontractor(vals)
        res = super().write(vals)
        if 'date' in vals:
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
        if self.is_subcontract:
            action = super(StockMove, self.with_context(force_lot_m2o=True)).action_show_details()
            if self.env.user._is_portal():
                action['views'] = [(self.env.ref('mrp_subcontracting.mrp_subcontracting_view_stock_move_operations').id, 'form')]
            return action
        return super().action_show_details()

    def action_show_subcontract_details(self, lot_id=None):
        """ Display moves raw for subcontracted product self. """
        productions = self._get_subcontract_production().filtered(lambda m: m.state != 'cancel')
        if lot_id is not None:
            if lot_id:
                productions = productions.filtered(lambda p: p.lot_producing_ids and p.lot_producing_ids[0] == self.env['stock.lot'].browse(lot_id))
            else:
                productions = productions.filtered(lambda p: not p.lot_producing_ids)
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
        else:
            action.update({
                'views': [(form_view_id.id, 'form')],
                'res_id': productions.id,
            })
        return action

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

    def _get_subcontract_production(self):
        return self.filtered(lambda m: m.is_subcontract).move_orig_ids.production_id

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

    def _can_create_lot(self):
        return super()._can_create_lot() or self.env.context.get('force_lot_m2o')

    def _sync_subcontracting_productions(self):
        """
            Enforce the relationship between subcontracting receipt moves and their respective subcontracting productions.
            * For untracked moves:
                * There will always be only 1 production.
                * Updating the move quantity will update the production quantity.
            * For tracked moves:
                * There will be 1 production for every lot on this move.
                * This method will enforce the synchronisation between the total quantity per lot on the move and the linked productions.
                * The split mechanism for productions will be used to create new subcontracting MOs.
                * We take care to always keep at least 1 subcontracting production linked to the subcontracting receipt.
                  This ensures there will always be a production available for splitting.
        """
        for move in self:
            productions = move._get_subcontract_production()
            if not productions:
                continue
            if move.has_tracking == 'none':
                if productions.product_uom_id.compare(productions.product_qty, move.quantity) != 0:
                    self.sudo().env['change.production.qty'].with_context(skip_activity=True).create([{
                        'mo_id': productions.id,
                        'product_qty': move.quantity or move.product_uom_qty,
                    }]).change_prod_qty()
                    productions.action_assign()
            else:
                qty_by_lot = dict(move.move_line_ids._read_group([('move_id', '=', move.id)], ['lot_id'], ['quantity_product_uom:sum']))
                mos_to_assign = self.env['mrp.production']

                # 1. Ensure quantities of linked MOs still match the quantities on the move
                mos_to_create = {}  # lot -> qty
                for lot_id, ml_qty in qty_by_lot.items():
                    lot_mo = productions.filtered(lambda p: (p.lot_producing_ids and p.lot_producing_ids[0] == lot_id) or (not lot_id and not p.lot_producing_ids))
                    if not lot_mo:
                        mos_to_create[lot_id] = ml_qty
                    elif lot_mo.product_uom_id.compare(lot_mo.product_qty, ml_qty) != 0:
                        self.sudo().env['change.production.qty'].with_context(skip_activity=True).create([{
                            'mo_id': lot_mo.id,
                            'product_qty': ml_qty
                        }]).change_prod_qty()
                        mos_to_assign |= lot_mo

                # 2. Create new MOs where needed, by splitting them from an existing subcontracting MO
                if mos_to_create:
                    production_to_split = move._get_subcontract_production()[0]
                    new_mos = production_to_split.sudo().with_context(allow_more=True, mrp_subcontracting=False)._split_productions({
                        production_to_split: [production_to_split.product_qty] + list(mos_to_create.values())
                    }, cancel_remaining_qty=True)[1:]
                    mos_to_assign |= new_mos
                    for mo, lot_id in zip(new_mos, mos_to_create.keys()):
                        mo.lot_producing_ids = lot_id

                # 3. Delete 'orphan' MOs with lot not linked to any move line
                productions = move._get_subcontract_production()
                orphan_productions = productions.filtered(lambda p: (p.lot_producing_ids and p.lot_producing_ids[0] not in qty_by_lot) or (not p.lot_producing_ids and self.env['stock.lot'] not in qty_by_lot))
                if len(productions) == len(orphan_productions):
                    # Make sure not to delete all MOs, leave 1 subcontracting MO as 'open' MO for splitting later
                    production_to_keep = orphan_productions[-1]
                    production_to_keep.lot_producing_ids = False
                    orphan_productions = orphan_productions[:-1]
                if orphan_productions:
                    orphan_productions.with_context(skip_activity=True).unlink()
                    productions -= orphan_productions

                mos_to_assign.sudo().action_assign()

    def _generate_serial_numbers(self, next_serial, next_serial_count=False, location_id=False):
        if self.is_subcontract:
            return super(StockMove, self.with_context(force_lot_m2o=True))._generate_serial_numbers(next_serial, next_serial_count, location_id)
        return super()._generate_serial_numbers(next_serial, next_serial_count, location_id)
