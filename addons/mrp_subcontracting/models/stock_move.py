from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import OrderedSet

_debug = DebugLog(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    is_subcontract = fields.Boolean(string="The move is a subcontract receipt")
    show_subcontracting_details_visible = fields.Boolean(
        compute="_compute_show_subcontracting_details_visible"
    )

    def _compute_show_subcontracting_details_visible(self):
        self.show_subcontracting_details_visible = False
        for move in self:
            if not move.is_subcontract:
                continue
            if not move.move_line_ids or move.product_uom_id.is_zero(move.quantity):
                continue
            productions = move._get_subcontract_production().filtered(
                lambda m: m.state != "cancel"
            )
            if not productions:
                continue
            move.show_subcontracting_details_visible = True

    @api.depends("is_subcontract")
    def _compute_show_info(self):
        super()._compute_show_info()
        subcontract_moves = self.filtered(
            lambda m: m.is_subcontract and m.show_lots_text
        )
        subcontract_moves.show_lots_text = False
        subcontract_moves.show_lots_m2o = True

    @api.depends("is_subcontract", "has_tracking")
    def _compute_is_quantity_done_editable(self):
        done_moves = self.env["stock.move"]
        for move in self:
            if move.is_subcontract:
                move.is_quantity_done_editable = move.has_tracking == "none"
                done_moves |= move
        return super(StockMove, self - done_moves)._compute_is_quantity_done_editable()

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for move, vals in zip(self, vals_list, strict=True):
            if "location_id" in default or not move.is_subcontract:
                continue
            vals["location_id"] = move.picking_id.location_id.id
        return vals_list

    def write(self, vals):
        self._check_access_if_subcontractor(vals)
        res = super().write(vals)
        if "date" in vals:
            for move in self:
                if move.state in ("done", "cancel") or not move.is_subcontract:
                    continue
                move.move_orig_ids.production_id.with_context(
                    from_subcontract=True
                ).filtered(lambda p: p.state not in ("done", "cancel")).write(
                    {
                        "date_start": move.date,
                        "date_end": move.date,
                    }
                )
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_access_if_subcontractor(vals)
        return super().create(vals_list)

    def action_show_details(self):
        self.check_singleton()
        if self.is_subcontract:
            action = super(
                StockMove, self.with_context(force_lot_m2o=True)
            ).action_show_details()
            if self.env.user._is_portal():
                action["views"] = [
                    (
                        self.env.ref(
                            "mrp_subcontracting.mrp_subcontracting_view_stock_move_form_operations"
                        ).id,
                        "form",
                    )
                ]
            return action
        return super().action_show_details()

    def action_show_subcontract_details(self, lot_id=None):
        productions = self._get_subcontract_production().filtered(
            lambda m: m.state != "cancel"
        )
        if lot_id is not None:
            if lot_id:
                productions = productions.filtered(
                    lambda p: (
                        p.lot_producing_ids
                        and p.lot_producing_ids[0]
                        == self.env["stock.lot"].browse(lot_id)
                    )
                )
            else:
                productions = productions.filtered(lambda p: not p.lot_producing_ids)
        ctx = {"mrp_subcontracting": True}
        if self.env.user._is_portal():
            form_view_id = self.env.ref(
                "mrp_subcontracting.mrp_production_subcontracting_portal_form_view"
            )
            ctx.update(no_breadcrumbs=False)
        else:
            form_view_id = self.env.ref(
                "mrp_subcontracting.mrp_production_subcontracting_form_view"
            )
        action = {
            "type": "ir.actions.act_window",
            "res_model": "mrp.production",
            "target": "current",
            "context": ctx,
        }
        if len(productions) > 1:
            action.update(
                {
                    "name": _("Subcontracting MOs"),
                    "views": [
                        (
                            self.env.ref(
                                "mrp_subcontracting.mrp_production_subcontracting_tree_view"
                            ).id,
                            "list",
                        ),
                        (form_view_id.id, "form"),
                    ],
                    "domain": [("id", "in", productions.ids)],
                }
            )
        else:
            action.update(
                {
                    "views": [(form_view_id.id, "form")],
                    "res_id": productions.id,
                }
            )
        return action

    def _action_cancel(self):
        productions_to_cancel_ids = OrderedSet()
        for move in self:
            if move.is_subcontract:
                active_productions = move.move_orig_ids.production_id.filtered(
                    lambda p: p.state not in ("done", "cancel")
                )
                moves_todo = self.env.context.get("moves_todo")
                not_todo_productions = (
                    active_productions.filtered(
                        lambda p: p not in moves_todo.move_orig_ids.production_id
                    )
                    if moves_todo
                    else active_productions
                )
                if not_todo_productions:
                    productions_to_cancel_ids.update(not_todo_productions.ids)

        if productions_to_cancel_ids:
            productions_to_cancel = self.env["mrp.production"].browse(
                productions_to_cancel_ids
            )
            productions_to_cancel.with_context(skip_activity=True).action_cancel()

        return super()._action_cancel()

    def _action_confirm(self, merge=True, merge_into=False, create_proc=True):
        subcontract_details_per_picking = defaultdict(list)
        for move in self:
            if (
                move.location_id.usage != "supplier"
                or move.location_dest_id.usage == "supplier"
            ):
                continue
            if move.move_orig_ids.production_id:
                continue
            bom = move._get_subcontract_bom()
            if not bom:
                _debug.logic("subcontract_skipped", reason="no_bom", move=move.id)
                continue
            company = move.company_id
            subcontracting_location = (
                move.picking_id.partner_id.with_company(
                    company
                ).property_stock_subcontractor
                or company.subcontracting_location_id
            )
            _debug.lifecycle(
                "subcontract_move_marked",
                move=move.id,
                bom=bom.id,
                location=subcontracting_location.id,
            )
            move.write(
                {
                    "production_group_id": False,
                    "is_subcontract": True,
                    "location_id": subcontracting_location.id,
                }
            )
            move._action_assign()
        res = super()._action_confirm(
            merge=merge, merge_into=merge_into, create_proc=create_proc
        )
        for move in res:
            if move.is_subcontract:
                subcontract_details_per_picking[move.picking_id].append(
                    (move, move._get_subcontract_bom())
                )
        _debug.pipeline(
            "subcontract_confirm",
            moves=self,
            pickings=len(subcontract_details_per_picking),
        )
        for picking, subcontract_details in subcontract_details_per_picking.items():
            picking._produce_subcontracted_productions(subcontract_details)

        if subcontract_details_per_picking:
            self.env["stock.picking"].concat(
                *list(subcontract_details_per_picking.keys())
            ).action_assign()
        return res

    def _get_subcontract_bom(self):
        self.check_singleton()
        return (
            self.env["mrp.bom"]
            .sudo()
            ._get_subcontract_bom_by_product(
                self.product_id,
                picking_type=self.picking_type_id,
                company_id=self.company_id.id,
                bom_type="subcontract",
                subcontractor=self.picking_id.partner_id,
            )
        )

    def _get_subcontract_production(self):
        return self.filtered(lambda m: m.is_subcontract).move_orig_ids.production_id

    def _prepare_move_split_vals(self, qty, force_uom_id=False):
        vals = super()._prepare_move_split_vals(qty, force_uom_id=force_uom_id)
        vals["location_id"] = self.location_id.id
        return vals

    def _prepare_procurement_vals(self):
        res = super()._prepare_procurement_vals()
        if self.raw_material_production_id.subcontractor_id:
            res["warehouse_id"] = self.picking_type_id.warehouse_id
        return res

    def _is_reservation_bypass_required(self, forced_location=False):
        is_reservation_bypass_required = super()._is_reservation_bypass_required(
            forced_location=forced_location
        )
        if not is_reservation_bypass_required and self.is_subcontract:
            return True
        return is_reservation_bypass_required

    def _get_available_move_lines(self, reserved_by_this_run):
        return super(
            StockMove, self.filtered(lambda m: not m.is_subcontract)
        )._get_available_move_lines(reserved_by_this_run)

    def _check_access_if_subcontractor(self, vals):
        if self.env.user._is_portal() and not self.env.su:
            if vals.get("state") == "done":
                raise AccessError(
                    _(
                        "Portal users cannot create a stock move with a state 'Done' or change the current state to 'Done'."
                    )
                )

    def _is_subcontract_return(self):
        self.check_singleton()
        subcontracting_location = self.picking_id.partner_id.with_company(
            self.company_id
        ).property_stock_subcontractor
        return (
            not self.is_subcontract
            and self.origin_returned_move_id.is_subcontract
            and self.location_dest_id.id == subcontracting_location.id
        )

    def _is_lot_materialization_required(self, picking_type=None):
        return super()._is_lot_materialization_required(
            picking_type
        ) or self.env.context.get("force_lot_m2o")

    def _sync_subcontracting_productions(self):
        for move in self:
            productions = move._get_subcontract_production()
            if not productions:
                continue
            _debug.pipeline(
                "subcontract_sync", productions=productions, tracking=move.has_tracking
            )
            if move.has_tracking == "none":
                if (
                    productions.product_uom_id.compare(
                        productions.product_qty, move.quantity
                    )
                    != 0
                ):
                    target_qty = move.quantity or move.product_uom_qty
                    demand_driven = (
                        productions.product_uom_id.compare(
                            target_qty, productions.product_qty
                        )
                        > 0
                        and productions.product_uom_id.compare(
                            target_qty, move.product_uom_qty
                        )
                        == 0
                    )
                    already_covered = (
                        productions._get_covered_component_qties()
                        if demand_driven
                        else {}
                    )
                    self.sudo().env["change.production.qty"].with_context(
                        skip_activity=True
                    ).create(
                        [
                            {
                                "mo_id": productions.id,
                                "product_qty": target_qty,
                            }
                        ]
                    ).change_prod_qty()
                    productions.action_assign()
                    if already_covered:
                        productions.move_raw_ids.filtered(
                            lambda raw: raw.id in already_covered
                        )._run_procurement(already_covered)
            else:
                qty_by_lot = defaultdict(float)
                for move_line in move.move_line_ids:
                    qty_by_lot[move_line.lot_id] += move_line.quantity_product_uom
                mos_to_assign = self.env["mrp.production"]

                mos_to_create = {}
                for lot_id, ml_qty in qty_by_lot.items():
                    lot_mo = productions.filtered(
                        lambda p: (
                            (p.lot_producing_ids and p.lot_producing_ids[0] == lot_id)
                            or (not lot_id and not p.lot_producing_ids)
                        )
                    )
                    if not lot_mo:
                        mos_to_create[lot_id] = ml_qty
                    elif lot_mo.product_uom_id.compare(lot_mo.product_qty, ml_qty) != 0:
                        self.sudo().env["change.production.qty"].with_context(
                            skip_activity=True
                        ).create(
                            [{"mo_id": lot_mo.id, "product_qty": ml_qty}]
                        ).change_prod_qty()
                        mos_to_assign |= lot_mo

                if mos_to_create:
                    production_to_split = move._get_subcontract_production()[0]
                    new_mos = (
                        production_to_split.sudo()
                        .with_context(allow_more=True, mrp_subcontracting=False)
                        ._split_productions(
                            {
                                production_to_split: [production_to_split.product_qty]
                                + list(mos_to_create.values())
                            },
                            cancel_remaining_qty=True,
                        )[1:]
                    )
                    mos_to_assign |= new_mos
                    for mo, lot_id in zip(new_mos, mos_to_create.keys(), strict=True):
                        mo.lot_producing_ids = lot_id

                productions = move._get_subcontract_production()
                orphan_productions = productions.filtered(
                    lambda p: (
                        (
                            p.lot_producing_ids
                            and p.lot_producing_ids[0] not in qty_by_lot
                        )
                        or (
                            not p.lot_producing_ids
                            and self.env["stock.lot"] not in qty_by_lot
                        )
                    )
                )
                if len(productions) == len(orphan_productions):
                    production_to_keep = orphan_productions[-1]
                    production_to_keep.lot_producing_ids = False
                    orphan_productions = orphan_productions[:-1]
                if orphan_productions:
                    orphan_productions.sudo().with_context(skip_activity=True).unlink()
                    productions -= orphan_productions

                mos_to_assign.sudo().action_assign()

    def _update_move_lines_for_serials(
        self, next_serial, next_serial_count=False, location_id=False
    ):
        if self.is_subcontract:
            return super(
                StockMove, self.with_context(force_lot_m2o=True)
            )._update_move_lines_for_serials(
                next_serial, next_serial_count, location_id
            )
        return super()._update_move_lines_for_serials(
            next_serial, next_serial_count, location_id
        )

    def _get_partner_id(self):
        if self.raw_material_production_id.subcontractor_id:
            route = self.env.ref(
                "mrp_subcontracting.route_resupply_subcontractor_mto",
                raise_if_not_found=False,
            )
            if route and self.rule_id.route_id == route:
                return self.raw_material_production_id.subcontractor_id.id
        return super()._get_partner_id()

    def _get_domain_production_assignation(self):
        if self.move_dest_ids.raw_material_production_id.subcontractor_id:
            return []
        return super()._get_domain_production_assignation()
