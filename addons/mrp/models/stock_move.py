from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import OrderedSet, float_is_zero

_debug = DebugLog(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)
        production_id = self.env.context.get(
            "default_raw_material_production_id"
        ) or self.env.context.get("default_production_id")
        if not production_id:
            return defaults
        production = self.env["mrp.production"].browse(production_id)
        if production.state == "draft":
            defaults["reference_ids"] = production.reference_ids.ids
            defaults["reference"] = production.name
        elif production.state == "done":
            defaults["state"] = "done"
            defaults["additional"] = True
            defaults["product_uom_qty"] = 0.0
        elif production.state != "cancel":
            defaults["state"] = "draft"
            defaults["product_uom_qty"] = 0.0
        return defaults

    created_production_id = fields.Many2one(
        comodel_name="mrp.production",
        string="Created Production Order",
        index="btree_not_null",
        check_company=True,
    )
    production_id = fields.Many2one(
        comodel_name="mrp.production",
        string="Production Order for finished products",
        index="btree_not_null",
        ondelete="cascade",
        check_company=True,
    )
    raw_material_production_id = fields.Many2one(
        comodel_name="mrp.production",
        string="Production Order for components",
        index="btree_not_null",
        ondelete="cascade",
        check_company=True,
    )
    production_group_id = fields.Many2one(
        comodel_name="mrp.production.group",
        string="Used for Productions",
        index="btree_not_null",
    )
    unbuild_id = fields.Many2one(
        comodel_name="mrp.unbuild",
        string="Disassembly Order",
        index="btree_not_null",
        check_company=True,
    )
    consume_unbuild_id = fields.Many2one(
        comodel_name="mrp.unbuild",
        string="Consumed Disassembly Order",
        index="btree_not_null",
        check_company=True,
    )
    allowed_operation_ids = fields.One2many(
        comodel_name="mrp.routing.workcenter",
        related="raw_material_production_id.bom_id.operation_ids",
    )
    operation_id = fields.Many2one(
        comodel_name="mrp.routing.workcenter",
        string="Operation To Consume",
        domain="[('id', 'in', allowed_operation_ids)]",
        check_company=True,
    )
    workorder_id = fields.Many2one(
        comodel_name="mrp.workorder",
        string="Work Order To Consume",
        index="btree_not_null",
        copy=False,
        check_company=True,
    )
    bom_line_id = fields.Many2one(
        comodel_name="mrp.bom.line",
        string="BoM Line",
        check_company=True,
    )
    byproduct_id = fields.Many2one(
        comodel_name="mrp.bom.byproduct",
        string="By-products",
        check_company=True,
        help="By-product line that generated the move in a manufacturing order",
    )
    unit_factor = fields.Float(
        compute="_compute_unit_factor",
        store=True,
    )
    order_finished_lot_ids = fields.Many2many(
        comodel_name="stock.lot",
        related="raw_material_production_id.lot_producing_ids",
        string="Finished Lot/Serial Number",
    )
    should_consume_qty = fields.Float(
        string="Quantity To Consume",
        digits="Product Unit",
        compute="_compute_should_consume_qty",
    )
    cost_share = fields.Float(
        string="Cost Share (%)",
        digits=0,
        help="The percentage of the final production cost for this by-product. The total of all by-products' cost share must be smaller or equal to 100.",
    )
    product_qty_available = fields.Float(
        related="product_id.qty_available",
        string="Product On Hand Quantity",
        depends=["product_id"],
    )
    product_virtual_available = fields.Float(
        related="product_id.qty_available_virtual",
        string="Product Forecasted Quantity",
        depends=["product_id"],
    )
    manual_consumption = fields.Boolean(
        compute="_compute_manual_consumption",
        store=True,
        readonly=False,
        help="When activated, then the registration of consumption for that component is recorded manually exclusively.\n"
        "If not activated, and any of the components consumption is edited manually on the manufacturing order, Odoo assumes manual consumption also.",
    )

    _one_production = models.Constraint(
        "CHECK (production_id IS NULL"
        " OR raw_material_production_id IS NULL"
        " OR production_id = raw_material_production_id)",
        "A stock move cannot be a component of one manufacturing order and an "
        "output of another.",
    )

    def _get_production(self):
        self.check_singleton()
        return self.raw_material_production_id or self.production_id

    @api.depends("product_id.bom_ids", "product_id.bom_ids.product_uom_id")
    def _compute_allowed_uom_ids(self):
        super()._compute_allowed_uom_ids()
        for move in self:
            move.allowed_uom_ids |= move.product_id.bom_ids.product_uom_id

    @api.depends("production_id")
    def _compute_packaging_uom_id(self):
        super()._compute_packaging_uom_id()
        for move in self:
            if move.production_id:
                move.packaging_uom_id = move.production_id.product_uom_id

    @api.depends("product_id", "bom_line_id", "bom_line_id.operation_id")
    def _compute_manual_consumption(self):
        for move in self:
            if move != move._origin:
                move.manual_consumption = move._origin.manual_consumption
            elif not move.manual_consumption:
                move.manual_consumption = move._is_manual_consumption()

    @api.depends(
        "raw_material_production_id.location_src_id",
        "production_id.production_location_id",
    )
    def _compute_location_id(self):
        ids_to_super = set()
        for move in self:
            if move.production_id:
                move.location_id = move.production_id.production_location_id
            elif move.raw_material_production_id:
                move.location_id = move.raw_material_production_id.location_src_id
            else:
                ids_to_super.add(move.id)
        return super(StockMove, self.browse(ids_to_super))._compute_location_id()

    @api.depends(
        "raw_material_production_id.production_location_id",
        "production_id.location_dest_id",
    )
    def _compute_location_dest_id(self):
        ids_to_super = set()
        for move in self:
            if move.production_id:
                move.location_dest_id = move.production_id.location_dest_id
            elif move.raw_material_production_id:
                move.location_dest_id = (
                    move.raw_material_production_id.production_location_id
                )
            else:
                ids_to_super.add(move.id)
        return super(StockMove, self.browse(ids_to_super))._compute_location_dest_id()

    @api.depends("bom_line_id")
    def _compute_description_picking(self):
        super()._compute_description_picking()
        stored = self.filtered("id")
        siblings = (
            self
            | stored.picking_id.move_ids
            | stored.raw_material_production_id.move_raw_ids
        )
        present_lines = siblings.bom_line_id
        bom_line_description = {}
        for bom in present_lines.bom_id:
            if bom.type != "phantom":
                continue
            line_ids = [line.id for line in bom.bom_line_ids if line in present_lines]
            total = len(line_ids)
            for i, line_id in enumerate(line_ids):
                bom_line_description[line_id] = "%s - %d/%d" % (
                    bom.display_name,
                    i + 1,
                    total,
                )

        for move in self:
            description = bom_line_description.get(move.bom_line_id.id)
            if move.description_picking_manual or not description:
                continue
            if move.description_picking == move.product_id.display_name:
                move.description_picking = ""
            move.description_picking += (
                "\n" if move.description_picking else ""
            ) + description

    @api.depends("raw_material_production_id.priority")
    def _compute_priority(self):
        super()._compute_priority()
        for move in self:
            move.priority = (
                move.raw_material_production_id.priority or move.priority or "0"
            )

    @api.depends(
        "raw_material_production_id.picking_type_id", "production_id.picking_type_id"
    )
    def _compute_picking_type_id(self):
        super()._compute_picking_type_id()
        for move in self:
            production = move._get_production()
            if production:
                move.picking_type_id = production.picking_type_id

    @api.depends("raw_material_production_id.is_locked", "production_id.is_locked")
    def _compute_is_locked(self):
        super()._compute_is_locked()
        for move in self:
            production = move._get_production()
            if production:
                move.is_locked = production.is_locked

    @api.depends(
        "product_uom_qty",
        "raw_material_production_id",
        "raw_material_production_id.product_qty",
        "raw_material_production_id.qty_produced",
        "production_id",
        "production_id.product_qty",
        "production_id.qty_produced",
    )
    def _compute_unit_factor(self):
        for move in self:
            production = move._get_production()
            if production:
                move.unit_factor = move.product_uom_qty / (
                    (production.product_qty - production.qty_produced) or 1
                )
            else:
                move.unit_factor = 1.0

    @api.depends(
        "raw_material_production_id",
        "raw_material_production_id.name",
        "production_id",
        "production_id.name",
        "unbuild_id",
        "unbuild_id.name",
    )
    def _compute_reference(self):
        ids_to_super = []
        for move in self:
            source = move.unbuild_id or move._get_production()
            if source.name:
                move.reference = source.name
            else:
                ids_to_super.append(move.id)
        super(StockMove, self.browse(ids_to_super))._compute_reference()

    def _update_references(self):
        super()._update_references()
        for move in self:
            if move.reference_ids:
                continue
            production = move._get_production()
            if production:
                move.reference_ids = [Command.set(production.reference_ids.ids)]

    def _get_qty_to_process(self):
        self.check_singleton()
        production = self._get_production()
        if not production or not self.product_uom_id:
            return 0.0
        return self.product_uom_id.round(
            (production.qty_producing - production.qty_produced) * self.unit_factor
        )

    @api.depends(
        "raw_material_production_id.qty_producing",
        "raw_material_production_id.qty_produced",
        "unit_factor",
        "product_uom_id",
    )
    def _compute_should_consume_qty(self):
        for move in self:
            move.should_consume_qty = (
                move._get_qty_to_process() if move.raw_material_production_id else 0.0
            )

    @api.depends("byproduct_id", "production_id.move_finished_ids")
    def _compute_show_info(self):
        super()._compute_show_info()
        finished_moves = self.production_id.move_finished_ids
        byproduct_moves = self.filtered(lambda m: m.byproduct_id or m in finished_moves)
        byproduct_moves.show_quant = False
        byproduct_moves.show_lots_m2o = True

    @api.onchange("product_uom_qty", "product_uom_id")
    def _onchange_product_uom_qty(self):
        if (
            self.product_uom_id
            and self.raw_material_production_id
            and self.has_tracking == "none"
            and self.state not in ("draft", "cancel", "done")
        ):
            self.quantity = self._get_qty_to_process()

    @api.onchange("quantity", "product_uom_id", "picked")
    def _onchange_quantity(self):
        if (
            self.raw_material_production_id
            and self.product_uom_id
            and not float_is_zero(
                self.quantity, precision_rounding=self.product_uom_id.rounding
            )
            and self.product_uom_id.compare(self.product_uom_qty, self.quantity) != 0
        ):
            self.manual_consumption = True
            self.picked = True

    @api.constrains("quantity", "raw_material_production_id")
    def _check_negative_quantity(self):
        for move in self:
            if (
                move.raw_material_production_id
                and move.product_uom_id.compare(move.quantity, 0) < 0
            ):
                raise ValidationError(
                    _("A component cannot be consumed in a negative quantity.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("force_manual_consumption"):
            for vals in vals_list:
                if "quantity" in vals:
                    vals["manual_consumption"] = self._is_quantity_edited(
                        vals.get("product_uom_qty"),
                        vals["quantity"],
                        self.env["uom.uom"].browse(vals.get("product_uom_id")),
                    )
                vals["picked"] = True
        production_ids = OrderedSet()
        location_ids = OrderedSet()
        for values in vals_list:
            mo_id = values.get("raw_material_production_id") or values.get(
                "production_id"
            )
            if mo_id:
                production_ids.add(mo_id)
            if values.get("location_dest_id"):
                location_ids.add(values["location_dest_id"])
        productions_by_id = {
            mo.id: mo for mo in self.env["mrp.production"].browse(production_ids)
        }
        locations_by_id = {
            location.id: location
            for location in self.env["stock.location"].browse(location_ids)
        }
        no_location = self.env["stock.location"]
        for values in vals_list:
            mo_id = values.get("raw_material_production_id", False) or values.get(
                "production_id", False
            )
            location_dest = locations_by_id.get(
                values.get("location_dest_id"), no_location
            )
            if mo_id and location_dest.usage != "inventory":
                mo = productions_by_id[mo_id]
                values["origin"] = mo._get_origin()
                values["propagate_cancel"] = mo.propagate_cancel
                values["reference_ids"] = mo.reference_ids.ids
                values["production_group_id"] = mo.production_group_id.id
                if values.get("raw_material_production_id", False):
                    values["location_dest_id"] = mo.production_location_id.id
                    if not values.get("location_id"):
                        values["location_id"] = mo.location_src_id.id
                    if mo.state in ["progress", "to_close"] and mo.qty_producing > 0:
                        values["picked"] = True
                    continue
                values["location_id"] = mo.production_location_id.id
                values["date"] = mo.date_end
                values["date_deadline"] = mo.date_deadline
                if not values.get("location_dest_id"):
                    values["location_dest_id"] = mo.location_dest_id.id
                if not values.get("location_final_id"):
                    values["location_final_id"] = mo.warehouse_id.lot_stock_id.id
        _debug.lifecycle(
            "create",
            count=len(vals_list),
            productions=len(productions_by_id),
            locations=len(locations_by_id),
        )
        return super().create(vals_list)

    @api.model
    def _is_quantity_edited(self, demand, quantity, uom):
        if not uom or demand is None:
            return True
        return uom.compare(demand, quantity) != 0

    def write(self, vals):
        moves_to_rereserve = self.env["stock.move"]
        if "product_id" in vals:
            moves_to_rereserve = self.filtered(
                lambda m: (
                    m.product_id.id != vals.get("product_id")
                    and m.production_id
                    and m.state not in ("draft", "cancel", "done")
                )
            )
            moves_to_rereserve._unreserve()
        moves_to_update = False
        if self.env.context.get("force_manual_consumption") and "quantity" in vals:
            moves_to_update = self.filtered(
                lambda move: move._is_quantity_edited(
                    move.product_uom_qty, vals["quantity"], move.product_uom_id
                )
            )
        if "product_uom_qty" in vals and "move_line_ids" in vals:
            move_line_vals = vals.pop("move_line_ids")
            super().write({"move_line_ids": move_line_vals})
        old_demand = (
            {move.id: move.product_uom_qty for move in self}
            if "product_uom_qty" in vals
            else {}
        )
        res = super().write(vals)
        _debug.lifecycle(
            "write",
            moves=self,
            fields=list(vals),
            rereserve=len(moves_to_rereserve),
            manual=len(moves_to_update) if moves_to_update else 0,
        )
        if moves_to_rereserve:
            moves_to_rereserve._action_assign()
        if moves_to_update:
            moves_to_update.write({"manual_consumption": True, "picked": True})
        if "product_uom_qty" in vals and not self.env.context.get(
            "no_procurement", False
        ):
            self.filtered(
                lambda m: (
                    m.raw_material_production_id.state
                    in ("confirmed", "progress", "to_close")
                )
            )._run_procurement(old_demand)
        return res

    def _run_procurement(self, old_qties=False):
        procurements = []
        old_qties = old_qties or {}
        to_assign_ids = OrderedSet()
        proc_move = OrderedSet()
        self._update_procure_method()
        for move in self:
            if (
                move.product_uom_id.compare(
                    move.product_uom_qty - old_qties.get(move.id, 0), 0
                )
                < 0
                and move.procure_method == "make_to_order"
                and move.move_orig_ids
                and all(m.state == "done" for m in move.move_orig_ids)
            ):
                continue
            if move.product_uom_id.compare(move.product_uom_qty, 0) > 0:
                if move._is_assign_at_confirm_required():
                    to_assign_ids.add(move.id)
            proc_move.add(move.id)

        to_assign = self.browse(to_assign_ids)
        before_assign_qties = {move.id: move.quantity for move in to_assign}
        to_assign._action_assign()
        delta_qties = {
            move.id: (
                move.quantity - before_assign_qties.get(move.id, 0)
                if move.product_id.is_storable
                else 0
            )
            for move in to_assign
        }

        proc_move = self.browse(proc_move)
        for move in proc_move:
            if (
                move.procure_method == "make_to_order"
                or move.rule_id.procure_method == "mts_else_mto"
            ):
                procurement_qty = (
                    move.product_uom_qty
                    - old_qties.get(move.id, 0)
                    - delta_qties.get(move.id, 0)
                )
                if move.move_orig_ids:
                    possible_reduceable_qty = -sum(
                        move.move_orig_ids.filtered(
                            lambda m: (
                                m.state not in ("done", "cancel") and m.product_uom_qty
                            )
                        ).mapped("product_uom_qty")
                    )
                    procurement_qty = max(procurement_qty, possible_reduceable_qty)
                values = move._prepare_procurement_vals()
                procurements.append(
                    self.env["stock.rule"].Procurement(
                        move.product_id,
                        procurement_qty,
                        move.product_uom_id,
                        move.location_id,
                        move.reference,
                        move.origin,
                        move.company_id,
                        values,
                    )
                )

        _debug.pipeline(
            "move_reprocurement",
            moves=self,
            assigned=len(to_assign),
            candidates=len(proc_move),
            procurements=len(procurements),
        )
        if procurements:
            self.env["stock.rule"].run(procurements)

    def _action_assign(self, force_qty=False):
        res = super()._action_assign(force_qty=force_qty)
        lines_by_owner = defaultdict(list)
        for move in self.filtered("raw_material_production_id"):
            if move.move_line_ids:
                key = (move.raw_material_production_id.id, move.workorder_id.id)
                lines_by_owner[key].extend(move.move_line_ids.ids)
        move_lines = self.env["stock.move.line"]
        _debug.pipeline("raw_move_lines_owned", moves=self, owners=len(lines_by_owner))
        for (production_id, workorder_id), line_ids in lines_by_owner.items():
            move_lines.browse(line_ids).write(
                {"production_id": production_id, "workorder_id": workorder_id}
            )
        return res

    def _action_confirm(self, merge=True, merge_into=False, create_proc=True):
        moves = self.action_explode()
        merge_into = merge_into and merge_into.action_explode()
        return super(StockMove, moves)._action_confirm(
            merge=merge, merge_into=merge_into, create_proc=create_proc
        )

    def _action_done(self, cancel_backorder=False):
        moves_to_explode = self.filtered(
            lambda m: m.product_id.is_kit and m.state not in ("cancel", "done")
        )
        exploded_moves = moves_to_explode.action_explode()
        moves = (self - moves_to_explode) | exploded_moves
        return super(StockMove, moves)._action_done(cancel_backorder)

    def _is_reservation_bypass_required(self, forced_location=False):
        return (
            super()._is_reservation_bypass_required(forced_location)
            or self.product_id.with_company(self.company_id).is_kit
        )

    def _is_explodable(self):
        self.check_singleton()
        if not self.picking_type_id and not (
            self.env.context.get("is_scrap")
            or self.env.context.get("skip_picking_assignation")
        ):
            return False
        return not (
            self.production_id and self.production_id.product_id == self.product_id
        )

    def _get_kit_boms(self):
        boms = {}
        moves_by_company = defaultdict(list)
        for move in self:
            moves_by_company[move.company_id].append(move.id)
        for company, move_ids in moves_by_company.items():
            boms.update(
                self.env["mrp.bom"]
                .sudo()
                ._get_bom_by_product(
                    self.browse(move_ids).product_id,
                    company_id=company.id,
                    bom_type="phantom",
                )
            )
        return boms

    def action_explode(self):
        moves_ids_to_return = OrderedSet()
        moves_ids_to_unlink = OrderedSet()
        phantom_moves_vals_list = []
        self = self.with_context(
            bom_cost_share_cache=self.env["mrp.bom"]._get_explosion_scratch()
        )
        explodable = self.filtered(lambda move: move._is_explodable())
        kit_boms = explodable._get_kit_boms()
        _debug.pipeline(
            "move_explode",
            moves=self,
            explodable=len(explodable),
            kits=len(kit_boms),
        )
        for move in self:
            bom = kit_boms.get(move.product_id) if move in explodable else None
            if not bom:
                moves_ids_to_return.add(move.id)
                continue
            quantity = (
                move.quantity
                if move.product_uom_id.is_zero(move.product_uom_qty)
                else move.product_uom_qty
            )
            factor = (
                move.product_uom_id._get_quantity_in_unit(quantity, bom.product_uom_id)
                / bom.product_qty
            )
            _dummy, lines = bom.sudo()._explode(
                move.product_id,
                factor,
                picking_type=bom.picking_type_id,
                never_attribute_values=move.never_product_template_attribute_value_ids,
            )
            phantom_moves_vals_list += move._prepare_phantom_moves_vals(lines)
            moves_ids_to_unlink.add(move.id)

        if phantom_moves_vals_list:
            phantom_moves = self.env["stock.move"].create(phantom_moves_vals_list)
            _debug.lifecycle("phantom_moves_created", moves=phantom_moves)
            phantom_moves._update_procure_method()
            moves_ids_to_return |= phantom_moves.action_explode().ids
        move_to_unlink = self.env["stock.move"].browse(moves_ids_to_unlink).sudo()
        move_to_unlink.quantity = 0
        move_to_unlink._action_cancel()
        move_to_unlink.unlink()
        return self.env["stock.move"].browse(moves_ids_to_return)

    def action_show_details(self):
        self.check_singleton()
        action = super().action_show_details()
        if self.raw_material_production_id:
            action["name"] = _("Components")
            action["views"] = [
                (self.env.ref("mrp.view_stock_move_form_operations_raw").id, "form")
            ]
            action["context"]["show_destination_location"] = False
            action["context"]["force_manual_consumption"] = True
            action["context"]["active_mo_id"] = self.raw_material_production_id.id
        elif self.production_id:
            action["name"] = _("Move Byproduct")
            action["views"] = [
                (
                    self.env.ref("mrp.view_stock_move_form_operations_finished").id,
                    "form",
                )
            ]
            action["context"]["show_source_location"] = False
            action["context"]["show_reserved_quantity"] = False
        return action

    def _action_add_from_catalog(self, child_field):
        production = self.env["mrp.production"].browse(self.env.context.get("order_id"))
        return production.with_context(
            child_field=child_field
        ).action_add_from_catalog()

    def action_add_from_catalog_raw(self):
        return self._action_add_from_catalog("move_raw_ids")

    def action_add_from_catalog_byproduct(self):
        return self._action_add_from_catalog("move_byproduct_ids")

    def _action_cancel(self):
        res = super()._action_cancel()
        if not self.env.context.get("skip_mo_check"):
            mo_to_cancel = self.mapped("raw_material_production_id").filtered(
                lambda p: all(m.state == "cancel" for m in p.move_raw_ids)
            )
            if mo_to_cancel:
                _debug.lifecycle(
                    "production_cancelled_by_moves",
                    moves=self,
                    productions=mo_to_cancel,
                )
                mo_to_cancel._action_cancel()
        return res

    def _log_cancel_activity(self):
        super()._log_cancel_activity()
        if not self:
            return None

        def _render_note_exception_cancel_dest(moves):
            values = {
                "origin_moves": moves,
                "origin_picking": moves.picking_id[:1],
                "moves_information": (
                    (move, (0.0, move.product_qty)) for move in moves
                ),
            }
            return self.env["ir.qweb"]._render("stock.exception_on_picking", values)

        cancelled_ids = set(self.ids)
        impacted_origins = self.move_orig_ids.filtered(
            lambda m: m.state not in ("done", "cancel")
        )
        documents = {}
        for move in impacted_origins:
            production = move.production_id
            if not production:
                continue
            cancelled_dests = move.move_dest_ids.filtered(
                lambda m: m.id in cancelled_ids
            )
            if not cancelled_dests.picking_id:
                continue
            key = (production, production.user_id or self.env.user)
            documents[key] = documents.get(key, self.browse()) | cancelled_dests
        return self.env["mixin.stock.activity"]._log_activity(
            _render_note_exception_cancel_dest, documents
        )

    def _prepare_move_split_vals(self, qty, force_uom_id=False):
        defaults = super()._prepare_move_split_vals(qty, force_uom_id=force_uom_id)
        defaults["workorder_id"] = False
        return defaults

    def _prepare_procurement_origin(self):
        self.check_singleton()
        if (
            self.raw_material_production_id
            and self.raw_material_production_id.orderpoint_id
        ):
            return self.origin
        return super()._prepare_procurement_origin()

    def _prepare_phantom_move_vals(self, bom_line, product_qty, quantity_done):
        self.check_singleton()
        return {
            "picking_id": self.picking_id.id if self.picking_id else False,
            "product_id": bom_line.product_id.id,
            "product_uom_id": bom_line.product_uom_id.id,
            "product_uom_qty": product_qty,
            "quantity": quantity_done,
            "picked": self.picked,
            "bom_line_id": bom_line.id,
            "description_picking": self.product_id.display_name,
        }

    def _prepare_phantom_moves_vals(self, exploded_lines_data):
        self.check_singleton()
        record_what_was_done = self.product_uom_id.is_zero(
            self.product_uom_qty
        ) or self.env.context.get("is_scrap")
        vals_list = []
        for bom_line, line_data in exploded_lines_data:
            if bom_line.product_id.type != "consu":
                continue
            if record_what_was_done:
                product_qty, quantity_done = 0, line_data["qty"]
            else:
                product_qty, quantity_done = line_data["qty"], 0
            vals = self.copy_data(
                default=self._prepare_phantom_move_vals(
                    bom_line, product_qty, quantity_done
                )
            )
            for val in vals:
                val["cost_share"] = line_data.get("line_cost_share", 0.0)
                if self.state == "assigned":
                    val["state"] = "assigned"
            vals_list += vals
        return vals_list

    def _is_consuming(self):
        return super()._is_consuming() or self.picking_type_id.code == "mrp_operation"

    def _prepare_backorder_move_vals(self):
        self.check_singleton()
        return {
            "state": "draft" if self.state == "draft" else "confirmed",
            "date_reservation": self.date_reservation,
            "date_deadline": self.date_deadline,
            "manual_consumption": self._is_manual_consumption(),
            "move_orig_ids": [Command.link(m.id) for m in self.mapped("move_orig_ids")],
            "move_dest_ids": [Command.link(m.id) for m in self.mapped("move_dest_ids")],
            "procure_method": self.procure_method,
        }

    def _get_source_document(self):
        res = super()._get_source_document()
        return res or self._get_production()

    def _get_upstream_documents_and_responsibles(self, visited):
        if self.production_id and self.production_id.state not in ("done", "cancel"):
            return [
                (
                    self.production_id,
                    self.production_id.user_id or self.env.user,
                    visited,
                )
            ]
        else:
            return super()._get_upstream_documents_and_responsibles(visited)

    def _get_delay_alert_documents(self):
        res = super()._get_delay_alert_documents()
        productions = self.raw_material_production_id | self.production_id
        return res + list(productions)

    def _is_assignment_required(self):
        res = super()._is_assignment_required()
        return bool(res and not self._get_production())

    def _is_qty_producing_bypass_required(self):
        if self.state in ("done", "cancel"):
            return True
        return self.product_uom_id.is_zero(self.product_uom_qty)

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super()._prepare_move_line_vals(quantity, reserved_quant)
        if self.raw_material_production_id:
            vals["production_id"] = self.raw_material_production_id.id
        if (
            self.production_id.product_tracking == "lot"
            and self.product_id == self.production_id.product_id
            and self.production_id.lot_producing_ids
        ):
            vals["lot_id"] = self.production_id.lot_producing_ids.ids[0]
        return vals

    def _get_picking_assignation_key(self):
        keys = super()._get_picking_assignation_key()
        return keys + (self.created_production_id,)

    def _prepare_merge_moves_distinct_fields(self):
        res = super()._prepare_merge_moves_distinct_fields()
        res += ["created_production_id", "cost_share", "production_group_id"]
        if self.bom_line_id and ("phantom" in self.bom_line_id.bom_id.mapped("type")):
            res.append("bom_line_id")
        return res

    def _prepare_merge_negative_moves_excluded_distinct_fields(self):
        return super()._prepare_merge_negative_moves_excluded_distinct_fields() + [
            "created_production_id"
        ]

    def _get_kit_quantity(self, product_id, kit_qty, kit_bom, filters):
        qty_ratios = []
        kit_qty /= kit_bom.product_qty
        _boms, bom_sub_lines = kit_bom._explode(product_id, kit_qty)

        def get_qty(move):
            if move.picked:
                return move.product_uom_id._get_quantity_in_unit(
                    move.quantity, move.product_id.uom_id, rounding_method="HALF-UP"
                )
            else:
                return move.product_qty

        for bom_line, bom_line_data in bom_sub_lines:
            if bom_line.product_id.type == "service":
                continue
            if bom_line.product_uom_id.is_zero(bom_line_data["qty"]):
                continue
            bom_line_moves = self.filtered(
                lambda m, bom_line=bom_line: m.bom_line_id == bom_line
            )
            if bom_line_moves:
                uom_qty_per_kit = bom_line_data["qty"] / (bom_line_data["original_qty"])
                qty_per_kit = bom_line.product_uom_id._get_quantity_in_unit(
                    uom_qty_per_kit / kit_bom.product_qty,
                    bom_line.product_id.uom_id,
                    round=False,
                )
                if not qty_per_kit:
                    continue
                incoming_moves = bom_line_moves.filtered(filters["incoming_moves"])
                final_incoming_moves = incoming_moves - incoming_moves.move_orig_ids
                qty_incoming = sum(final_incoming_moves.mapped(get_qty))
                outgoing_moves = bom_line_moves.filtered(filters["outgoing_moves"])
                final_outgoing_moves = outgoing_moves - outgoing_moves.move_orig_ids
                qty_outgoing = sum(final_outgoing_moves.mapped(get_qty))
                qty_processed = qty_incoming - qty_outgoing
                qty_ratios.append(
                    bom_line.product_id.uom_id.round(qty_processed / qty_per_kit)
                )
            else:
                return 0.0
        _debug.logic(
            "kit_quantity",
            kit_bom=kit_bom.id,
            product=product_id.id,
            lines=len(bom_sub_lines),
            ratios=len(qty_ratios),
            qty=min(qty_ratios) // 1 if qty_ratios else 0.0,
        )
        if qty_ratios:
            return min(qty_ratios) // 1
        else:
            return 0.0

    def _update_candidate_moves_list(self, candidate_moves_set):
        super()._update_candidate_moves_list(candidate_moves_set)
        products = self.product_id
        for production in self.raw_material_production_id:
            candidate_moves_set.add(
                production.move_raw_ids.filtered(lambda m: m.product_id in products)
            )
        for production in self.production_id:
            candidate_moves_set.add(
                production.move_finished_ids.filtered(
                    lambda m: m.product_id in products
                )
            )
        for picking in self.move_dest_ids.raw_material_production_id.picking_ids:
            candidate_moves_set.add(picking.move_ids)

    def _prepare_procurement_vals(self):
        res = super()._prepare_procurement_vals()
        res["production_group_id"] = self.production_group_id.id
        res["bom_line_id"] = self.bom_line_id.id
        return res

    def _get_domain_picking_for_assignation(self):
        return Domain(super()._get_domain_picking_for_assignation()) & Domain(
            self._get_domain_production_assignation()
        )

    def _get_domain_production_assignation(self):
        return [("move_ids.production_group_id", "=", self.production_group_id.id)]

    def action_view_reference(self):
        res = super().action_view_reference()
        source = self._get_production()
        if source and source.browse().has_access("read"):
            return {
                "res_model": source._name,
                "type": "ir.actions.act_window",
                "views": [[False, "form"]],
                "res_id": source.id,
            }
        return res

    def _is_manual_consumption(self):
        self.check_singleton()
        return self._is_manual_consumption_from_bom_line(self.bom_line_id)

    @api.model
    def _is_manual_consumption_from_bom_line(self, bom_line):
        return bool(bom_line and bom_line.operation_id)

    def _is_consumption_covered(self):
        self.check_singleton()
        uom = self.product_uom_id
        if (
            self.should_consume_qty
            and uom.compare(self.quantity, self.should_consume_qty) >= 0
        ):
            return True
        return uom.compare(self.quantity, self.product_uom_qty) >= 0 or (
            self.manual_consumption and self.picked
        )

    def _get_relevant_state_among_moves(self):
        res = super()._get_relevant_state_among_moves()
        if res != "partially_available":
            return res
        moves = self.filtered(lambda m: m.state not in ("cancel", "done"))
        if moves.raw_material_production_id and all(
            move._is_consumption_covered() for move in moves
        ):
            res = "assigned"
        return res
