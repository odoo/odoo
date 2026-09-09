from collections import Counter, defaultdict
from typing import Any, NamedTuple

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import OrderedSet

from ..const import (
    CONTEXT_BLOCK_COMPLETING,
    DISPOSAL_DEST_USAGES,
    OUTGOING_BLOCK_TYPES,
    is_internal_flag,
)
from ..tools import debug_log as dbg

LOGGED_RELATIONS = [
    ("lot_id", "lot_name"),
    ("location_id", "location_name"),
    ("location_dest_id", "location_dest_name"),
    ("package_id", "package_name"),
    ("result_package_id", "result_package_dest_name"),
    ("owner_id", "owner_name"),
]


_KEEP = object()

RESERVATION_KEY_FIELDS = (
    "product_id",
    "location_id",
    "lot_id",
    "package_id",
    "owner_id",
)

RENDERED_KEYS = frozenset(
    {"quantity", *(rendered for _field, rendered in LOGGED_RELATIONS)}
)

SOURCE_QUANT_FIELDS = ("location_id", "package_id", "lot_id", "owner_id")

DEST_QUANT_FIELDS = ("location_dest_id", "result_package_id", "lot_id", "owner_id")

RESTOCK_TRIGGER_FIELDS = tuple(dict.fromkeys(SOURCE_QUANT_FIELDS + DEST_QUANT_FIELDS))


class WritePlan(NamedTuple):
    vals: dict[str, Any]
    watched: bool
    before: dict[int, tuple[int, float]] | None
    packages_to_check: models.BaseModel
    updates: dict[str, models.BaseModel]
    reservation_touched: bool
    moves_to_recompute_state: models.BaseModel
    to_restock: models.BaseModel
    to_adjust: models.BaseModel
    next_moves: models.BaseModel
    reverted_in_dates: dict[int, Any]
    deltas: dict[int, float]
    progressed: models.BaseModel


class StockMoveLine(models.Model):
    _name = "stock.move.line"
    _description = "Product Moves (Stock Move Line)"
    _order = "result_package_id desc, id"
    _rec_name = "product_id"

    company_id = fields.Many2one(
        comodel_name="res.company",
        index=True,
        readonly=True,
        required=True,
    )

    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Transfer",
        index=True,
        check_company=True,
        bypass_search_access=True,
        help="The stock operation where the packing has been made",
    )
    picking_partner_id = fields.Many2one(
        related="picking_id.partner_id",
        readonly=True,
    )
    picking_location_id = fields.Many2one(related="picking_id.location_id")
    picking_location_dest_id = fields.Many2one(related="picking_id.location_dest_id")
    picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Operation type",
        compute="_compute_picking_type_id",
        search="_search_picking_type_id",
    )
    picking_type_use_create_lots = fields.Boolean(
        related="picking_type_id.use_create_lots",
        readonly=True,
    )
    picking_type_use_existing_lots = fields.Boolean(
        related="picking_type_id.use_existing_lots",
        readonly=True,
    )
    picking_code = fields.Selection(
        related="picking_type_id.code",
        readonly=True,
    )

    move_id = fields.Many2one(
        comodel_name="stock.move",
        string="Stock Operation",
        index=True,
        check_company=True,
    )
    state = fields.Selection(
        related="move_id.state",
        store=True,
    )
    date_planned = fields.Datetime(
        related="move_id.date",
        string="Scheduled Date",
    )
    move_partner_id = fields.Many2one(
        related="move_id.partner_id",
        readonly=True,
    )
    scrap_id = fields.Many2one(related="move_id.scrap_id")
    is_inventory = fields.Boolean(related="move_id.is_inventory")
    is_locked = fields.Boolean(
        related="move_id.is_locked",
        readonly=True,
    )
    reference = fields.Char(related="move_id.reference")
    origin = fields.Char(
        related="move_id.origin",
        string="Source",
    )
    description_picking = fields.Text(related="move_id.description_picking")

    location_id = fields.Many2one(
        comodel_name="stock.location",
        string="From",
        compute="_compute_locations",
        precompute=True,
        store=True,
        index=True,
        readonly=False,
        required=True,
        domain="[('usage', '!=', 'view')]",
        check_company=True,
    )
    location_dest_id = fields.Many2one(
        comodel_name="stock.location",
        string="To",
        compute="_compute_locations",
        precompute=True,
        store=True,
        index=True,
        readonly=False,
        required=True,
        domain="[('usage', '!=', 'view')]",
        check_company=True,
    )
    location_usage = fields.Selection(
        related="location_id.usage",
        string="Source Location Type",
    )
    location_dest_usage = fields.Selection(
        related="location_dest_id.usage",
        string="Destination Location Type",
    )
    owner_id = fields.Many2one(
        comodel_name="res.partner",
        string="From Owner",
        index="btree_not_null",
        check_company=True,
        help="When validating the transfer, the products will be taken from this owner.",
    )
    date = fields.Datetime(
        default=fields.Datetime.now,
        required=True,
        help="Creation date of this move line until updated due to: quantity being increased, 'picked' status has updated, or move line is done.",
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        index=True,
        domain="[('type', '!=', 'service')]",
        ondelete="cascade",
        check_company=True,
    )
    product_category_name = fields.Char(
        related="product_id.categ_id.complete_name",
        string="Product Category",
    )
    tracking = fields.Selection(
        related="product_id.tracking",
        readonly=True,
    )
    allowed_uom_ids = fields.Many2many(
        comodel_name="uom.uom",
        compute="_compute_allowed_uom_ids",
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit",
        compute="_compute_product_uom_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        domain="[('id', 'in', allowed_uom_ids)]",
    )
    quantity = fields.Float(
        digits="Product Unit",
        compute="_compute_quantity",
        store=True,
        copy=False,
        readonly=False,
    )
    quantity_product_uom = fields.Float(
        string="Quantity in Product UoM",
        min_display_digits="Product Unit",
        compute="_compute_quantity_product_uom",
        store=True,
        copy=False,
    )
    picked = fields.Boolean(
        compute="_compute_picked",
        store=True,
        copy=False,
        readonly=False,
    )
    package_id = fields.Many2one(
        comodel_name="stock.package",
        string="Source Package",
        domain="[('location_id', '=', location_id)]",
        ondelete="restrict",
        check_company=True,
    )
    lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Lot/Serial Number",
        index=True,
        domain="[('product_id', '=', product_id)]",
        check_company=True,
    )
    lot_name = fields.Char(string="Lot/Serial Number Name")
    result_package_id = fields.Many2one(
        comodel_name="stock.package",
        string="Destination Package",
        required=False,
        domain="""[
        '|', '|',
        ('location_id', '=', location_dest_id),
        ('id', '=', package_id),
        '&', ('location_id', '=', False),
        '|', ('move_line_ids', '=', False),
        ('move_line_ids.location_dest_id', '=', location_dest_id)
        ]""",
        ondelete="restrict",
        check_company=True,
        help="If set, the operations are packed into this package",
    )
    result_package_dest_name = fields.Char(
        related="result_package_id.dest_complete_name",
        string="Destination Package Name",
    )
    package_history_id = fields.Many2one(
        comodel_name="stock.package.history",
        index="btree_not_null",
    )
    is_entire_pack = fields.Boolean(string="Is added through entire package")
    lots_visible = fields.Boolean(compute="_compute_lots_visible")
    consume_line_ids = fields.Many2many(
        comodel_name="stock.move.line",
        relation="stock_move_line_consume_rel",
        column1="consume_line_id",
        column2="produce_line_id",
    )
    produce_line_ids = fields.Many2many(
        comodel_name="stock.move.line",
        relation="stock_move_line_consume_rel",
        column1="produce_line_id",
        column2="consume_line_id",
    )
    quant_id = fields.Many2one(
        comodel_name="stock.quant",
        string="Pick From",
        store=False,
    )

    _free_reservation_index = models.Index(
        """(%s, company_id)
        WHERE (state IS NULL OR state NOT IN ('done', 'cancel')) AND quantity_product_uom > 0 AND picked IS NOT TRUE"""
        % ", ".join(RESERVATION_KEY_FIELDS)
    )

    @api.model
    def _get_negative_quantity_message(self):
        return _("You can not enter negative quantities.")

    @api.constrains("lot_id", "product_id")
    def _check_lot_product(self):
        for line in self:
            if line.lot_id and line.product_id != line.lot_id.sudo().product_id:
                raise ValidationError(
                    _(
                        "This lot %(lot_name)s is incompatible with this product %(product_name)s",
                        lot_name=line.lot_id.name,
                        product_name=line.product_id.display_name,
                    ),
                )

    @api.constrains("quantity", "product_uom_id")
    def _check_positive_quantity(self):
        if any(ml.product_uom_id.compare(ml.quantity, 0) < 0 for ml in self):
            raise ValidationError(self._get_negative_quantity_message())

    @dbg.timed
    @api.model_create_multi
    def create(self, vals_list):
        dbg.lifecycle.debug(
            "stock.move.line.create: %d vals, keys=%s",
            len(vals_list),
            dbg.vals_keys(vals_list),
        )
        vals_list = self._prepare_create_vals(vals_list)

        mls = super().create(vals_list)
        dbg.lifecycle.debug("stock.move.line.create: created %s", dbg.rec(mls))

        created_moves = mls._link_or_create_moves()
        if created_moves:
            dbg.pipeline.debug(
                "create: lines %s created moves %s",
                dbg.rec(mls),
                dbg.rec(created_moves),
            )
        mls._reserve_new_move_lines()
        created_moves._post_process_created_moves()
        done_lines = mls.filtered(lambda ml: ml.state == "done")
        if done_lines:
            dbg.pipeline.debug(
                "create: done lines %s update quants directly", dbg.rec(done_lines)
            )
        for ml in done_lines.with_context(quants_cache=done_lines._get_quants_cache()):
            ml._update_quants_and_reservations()

        if next_moves := done_lines._get_pending_dest_moves():
            dbg.pipeline.debug(
                "create: done lines -> unreserve + assign dest moves %s",
                dbg.rec(next_moves),
            )
            next_moves._unreserve()
            next_moves._action_assign()

        if done_lines.move_id:
            done_lines.move_id._check_quantity()

        mls._check_blocked_outgoing()
        return mls

    @dbg.timed
    def write(self, vals):
        dbg.lifecycle.debug(
            "stock.move.line.write on %s: keys=%s", dbg.rec(self), dbg.keys(vals)
        )
        plan = self._prepare_write(vals)
        res = super().write(plan.vals)
        self._apply_write_plan(plan)
        return res

    def _prepare_write(self, vals):
        self._check_write_allowed(vals)
        if vals.get("quant_id"):
            vals = {**vals, **self._prepare_quant_vals(vals)}
            self._check_write_allowed(vals)

        watched = "quantity" in vals or "location_id" in vals
        before = (
            {line.id: (line.location_id.id, line.quantity) for line in self}
            if watched
            else None
        )

        packages_to_check = self.env["stock.package"]
        if "result_package_id" in vals:
            packages_to_check = self._get_package_dests()

        updates = self._get_write_field_updates(vals)
        moves_to_recompute_state = self._sync_quant_reservation(vals, updates)
        reservation_touched = bool(updates) or "quantity" in vals

        to_restock, to_adjust = (
            self._get_lines_to_requant(vals, updates)
            if reservation_touched
            else (self.browse(), self.browse())
        )
        requanted = to_restock | to_adjust
        next_moves = requanted._get_pending_dest_moves()
        requanted._log_quant_corrections(vals)
        reverted_in_dates = to_restock._revert_quant_moves(
            to_restock._filtered_keeping_destination(vals, updates)
        )
        deltas = to_adjust._get_quantity_deltas(vals, updates)

        progressed = self._get_progressed_lines(vals, updates)
        if progressed == self:
            vals = {**vals, "date": fields.Datetime.now()}
            progressed = self.browse()

        if reservation_touched:
            dbg.logic.debug(
                "_prepare_write on %s: updates=%s restock=%s adjust=%s next_moves=%s "
                "recompute=%s progressed=%s",
                dbg.rec(self),
                dbg.keys(updates),
                dbg.rec(to_restock),
                dbg.rec(to_adjust),
                dbg.rec(next_moves),
                dbg.rec(moves_to_recompute_state),
                dbg.rec(progressed),
            )
        return WritePlan(
            vals=vals,
            watched=watched,
            before=before,
            packages_to_check=packages_to_check,
            updates=updates,
            reservation_touched=reservation_touched,
            moves_to_recompute_state=moves_to_recompute_state,
            to_restock=to_restock,
            to_adjust=to_adjust,
            next_moves=next_moves,
            reverted_in_dates=reverted_in_dates,
            deltas=deltas,
            progressed=progressed,
        )

    def _apply_write_plan(self, plan):
        if plan.progressed:
            plan.progressed.date = fields.Datetime.now()
        plan.to_restock._update_quants_again(plan.reverted_in_dates)
        plan.to_adjust._update_quants_by_delta(plan.deltas)

        survivors = self.exists() if plan.to_restock or plan.to_adjust else self

        plan.packages_to_check._update_orphaned_package_dests()
        if plan.reservation_touched:
            if mls_to_update := survivors._get_lines_not_entire_pack():
                dbg.logic.debug(
                    "_apply_write_plan: %s no longer entire pack",
                    dbg.rec(mls_to_update),
                )
                mls_to_update.write({"is_entire_pack": False})

            if plan.next_moves:
                dbg.pipeline.debug(
                    "_apply_write_plan -> unreserve + assign %s",
                    dbg.rec(plan.next_moves),
                )
            plan.next_moves._unreserve()
            plan.next_moves._action_assign()

        if plan.moves_to_recompute_state:
            plan.moves_to_recompute_state._recompute_state()

        if plan.watched:
            survivors.filtered(
                lambda line: (
                    line.product_uom_id.compare(line.quantity, plan.before[line.id][1])
                    > 0
                    or line.location_id.id != plan.before[line.id][0]
                ),
            )._check_blocked_outgoing()

    def _check_blocked_outgoing(self):
        if self.env.su or is_internal_flag(self.env.context, CONTEXT_BLOCK_COMPLETING):
            return
        blocked = self.filtered(
            lambda line: (
                line.quantity > 0
                and line.location_id.effective_block_type in OUTGOING_BLOCK_TYPES
                and line.location_dest_id.usage not in DISPOSAL_DEST_USAGES
            ),
        )
        if blocked:
            dbg.logic.debug(
                "_check_blocked_outgoing: %s leave blocked locations %s",
                dbg.rec(blocked),
                dbg.rec(blocked.location_id),
            )
        for location in blocked.location_id:
            location._check_operation_allowed("out")

    @dbg.timed
    def unlink(self):
        dbg.lifecycle.debug("stock.move.line.unlink %s", dbg.rec(self))
        self._unlink_except_done_or_cancel()
        self._release_quants()
        moves = self.mapped("move_id")
        packages = self._get_package_dests()
        res = super().unlink()
        if moves:
            moves.with_prefetch()._recompute_state()
        packages._update_orphaned_package_dests()
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done_or_cancel(self):
        for ml in self:
            if ml.state in ("done", "cancel"):
                raise UserError(
                    _(
                        "Deleting product moves after the transfer is done?\n\n"
                        "That would be like going back in time to revert all operations triggered after this move. Who knows what the end result would be, So let's not do it.\n\n"
                        "Try changing the “done” quantity to 0 instead."
                    ),
                )

    @api.depends(
        "product_id",
        "product_id.uom_id",
        "product_id.uom_ids",
        "product_id.seller_ids",
        "product_id.seller_ids.product_uom_id",
    )
    def _compute_allowed_uom_ids(self):
        sudo_lines = self.sudo()
        for line, sudo_line in zip(self, sudo_lines, strict=True):
            line.allowed_uom_ids = (
                line.product_id.uom_id
                | line.product_id.uom_ids
                | sudo_line.product_id.seller_ids.product_uom_id
            )

    @api.depends("move_id.product_uom_id", "product_id.uom_id")
    def _compute_product_uom_id(self):
        for line in self:
            if not line.product_uom_id:
                if line.move_id.product_uom_id:
                    line.product_uom_id = line.move_id.product_uom_id.id
                else:
                    line.product_uom_id = line.product_id.uom_id.id

    @api.depends("picking_id.picking_type_id", "product_id.tracking")
    def _compute_lots_visible(self):
        for line in self:
            tracked = line.product_id.tracking != "none"
            picking_type = line.picking_id.picking_type_id
            if tracked and picking_type:
                line.lots_visible = (
                    picking_type.use_existing_lots or picking_type.use_create_lots
                )
            else:
                line.lots_visible = tracked

    @api.depends("state")
    def _compute_picked(self):
        for line in self:
            if line.state == "done":
                line.picked = True

    @api.depends("picking_id.picking_type_id", "move_id.picking_type_id")
    def _compute_picking_type_id(self):
        for line in self:
            line.picking_type_id = (
                line.picking_id.picking_type_id or line.move_id.picking_type_id
            )

    @api.depends(
        "move_id", "move_id.location_id", "move_id.location_dest_id", "picking_id"
    )
    def _compute_locations(self):
        for line in self:
            if (
                not line.location_id
                or line._origin.picking_id.location_id != line.picking_id.location_id
            ):
                line.location_id = (
                    line.move_id.location_id or line.picking_id.location_id
                )
            if (
                not line.location_dest_id
                or line._origin.picking_id.location_dest_id
                != line.picking_id.location_dest_id
            ):
                line.location_dest_id = (
                    line.move_id.location_dest_id or line.picking_id.location_dest_id
                )

    @api.depends("quant_id")
    def _compute_quantity(self):
        for record in self:
            if not record.quant_id or record.quantity:
                continue
            product_uom = record.product_id.uom_id
            sml_uom = record.product_uom_id
            move_visible_quantity = (
                record.move_id._get_visible_quantity() if record.move_id else 0.0
            )

            move_demand = record.move_id.product_uom_id._get_quantity_in_unit(
                record.move_id.product_uom_qty, sml_uom, rounding_method="HALF-UP"
            )
            move_quantity = record.move_id.product_uom_id._get_quantity_in_unit(
                move_visible_quantity, sml_uom, rounding_method="HALF-UP"
            )
            quant_qty = product_uom._get_quantity_in_unit(
                record.quant_id.available_quantity, sml_uom, rounding_method="HALF-UP"
            )

            if sml_uom.compare(move_demand, move_quantity) > 0:
                record.quantity = max(0, min(quant_qty, move_demand - move_quantity))
            else:
                record.quantity = max(0, quant_qty)

    @api.depends("quantity", "product_uom_id", "product_id.uom_id")
    def _compute_quantity_product_uom(self):
        for line in self:
            line.quantity_product_uom = line.product_uom_id._get_quantity_stored(
                line.quantity, line.product_id.uom_id
            )

    def _search_picking_type_id(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        return Domain("picking_id.picking_type_id", operator, value) | (
            Domain("picking_id", "=", False)
            & Domain("move_id.picking_type_id", operator, value)
        )

    @api.onchange("product_id", "product_uom_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.lots_visible = self.product_id.tracking != "none"

    @api.onchange("lot_name", "lot_id")
    def _onchange_serial_number(self):
        res = {}
        if self.product_id.tracking != "serial":
            return res
        if not self.quantity:
            self.quantity = 1

        serial = self._get_serial_name()
        if not serial:
            return res

        message = None
        siblings = self._get_similar_move_lines()
        if any(line._get_serial_name() == serial for line in siblings):
            message = _(
                "You cannot use the same serial number twice. Please correct the serial numbers encoded."
            )
        elif self.lot_id:
            message, recommended_location = (
                self.env["stock.quant"]
                .sudo()
                ._get_serial_number_warning(
                    self.product_id,
                    self.lot_id,
                    self.company_id,
                    self.location_id,
                    self.picking_id.location_id,
                )
            )
            if recommended_location:
                dbg.logic.debug(
                    "_onchange_serial_number: lot %s recommends location %s",
                    self.lot_id.id,
                    recommended_location.id,
                )
                self.location_id = recommended_location
        else:
            quants = (
                self.env["stock.lot"]
                .search(
                    [
                        ("product_id", "=", self.product_id.id),
                        ("name", "=", serial),
                        "|",
                        ("company_id", "=", False),
                        ("company_id", "=", self.company_id.id),
                    ],
                )
                .quant_ids.filtered(
                    lambda q: (
                        not q.product_uom_id.is_zero(q.quantity)
                        and q.location_id.usage in ["customer", "internal", "transit"]
                    )
                )
            )
            if quants:
                message = _(
                    "Serial number (%(serial_number)s) already exists in location(s): %(location_list)s. Please correct the serial number encoded.",
                    serial_number=serial,
                    location_list=quants.location_id.mapped("display_name"),
                )
        if message:
            res["warning"] = {"title": _("Warning"), "message": message}
        return res

    def _get_serial_name(self):
        self.check_singleton()
        return self.lot_id.name or self.lot_name

    def _get_similar_move_lines(self):
        self.check_singleton()
        picking = self.move_id.picking_id or self.picking_id
        others = picking.move_line_ids - self - self._origin
        return others.filtered(
            lambda ml: ml.product_id == self.product_id and (ml.lot_id or ml.lot_name)
        )

    @api.onchange("quantity", "product_uom_id")
    def _onchange_quantity(self):
        if self.quantity and self.product_id.tracking == "serial":
            if self.product_id.uom_id.compare(
                self.quantity_product_uom, 1.0
            ) != 0 and not self.product_uom_id._is_zero_stored(
                self.quantity_product_uom, self.product_id.uom_id
            ):
                raise UserError(
                    _(
                        "You can only process 1.0 %s of products with unique serial number.",
                        self.product_id.uom_id.name,
                    ),
                )

    @dbg.timed
    def _action_done(self):
        dbg.pipeline.debug("stock.move.line._action_done start on %s", dbg.rec(self))
        mls_to_delete, mls_needing_lot_check, mls_without_lot = (
            self._classify_done_lines()
        )
        dbg.logic.debug(
            "_action_done: delete=%s lot_check=%s without_lot=%s",
            dbg.rec(mls_to_delete),
            dbg.rec(mls_needing_lot_check),
            dbg.rec(mls_without_lot),
        )
        (
            mls_without_lot | mls_needing_lot_check._update_done_lots()
        )._check_lots_supplied()

        mls_to_delete.unlink()

        mls_todo = self - mls_to_delete
        mls_todo._check_company()

        if not self.env.context.get("ignore_dest_packages"):
            package_history_vals = mls_todo._prepare_package_history_vals()
            if package_history_vals:
                dbg.lifecycle.debug(
                    "_action_done: %d package history rows", len(package_history_vals)
                )
                self.env["stock.package.history"].create(package_history_vals)

        dbg.pipeline.debug("_action_done -> _update_quants_done %s", dbg.rec(mls_todo))
        mls_todo._update_quants_done()

        if not self.env.context.get("ignore_dest_packages"):
            mls_todo.result_package_id._update_parent_packages_from_dest()

        affected_pickings = mls_todo.picking_id
        if affected_pickings:
            affected_pickings._check_entire_pack()
        mls_todo.write(
            {
                "date": fields.Datetime.now(),
            }
        )

    def _classify_done_lines(self):
        ml_ids_tracked_without_lot = OrderedSet()
        ml_ids_to_delete = OrderedSet()
        ml_ids_needing_lot_check = OrderedSet()

        for ml in self:
            qty_done_float_compared = ml.product_uom_id.compare(ml.quantity, 0)
            if qty_done_float_compared < 0:
                raise UserError(self._get_negative_quantity_message())
            if qty_done_float_compared == 0:
                if not ml.is_inventory:
                    ml_ids_to_delete.add(ml.id)
                continue
            if ml.product_id.tracking == "none":
                continue
            picking_type = ml.picking_type_id
            if not ml._has_lot_context():
                ml_ids_tracked_without_lot.add(ml.id)
                continue
            if (
                not picking_type
                or ml.lot_id
                or (
                    not picking_type.use_create_lots
                    and not picking_type.use_existing_lots
                )
            ):
                continue
            if picking_type.use_create_lots:
                ml_ids_needing_lot_check.add(ml.id)
            else:
                ml_ids_tracked_without_lot.add(ml.id)

        return (
            self.browse(ml_ids_to_delete),
            self.browse(ml_ids_needing_lot_check),
            self.browse(ml_ids_tracked_without_lot),
        )

    def _update_done_lots(self):
        if not self:
            return self
        ml_ids_tracked_without_lot = OrderedSet()
        ml_ids_to_create_lot = OrderedSet()
        groups = self.grouped(lambda ml: (ml.product_id, ml.company_id))
        lots_per_group = defaultdict(dict)
        archived_per_group = defaultdict(dict)
        for lot in (
            self.env["stock.lot"]
            .with_context(active_test=False)
            .search(
                [
                    ("company_id", "in", [False, *self.company_id.ids]),
                    ("product_id", "in", self.product_id.ids),
                    ("name", "in", self.mapped("lot_name")),
                ]
            )
        ):
            for product, company in groups:
                if lot.product_id == product and (
                    not lot.company_id or lot.company_id == company
                ):
                    bucket = lots_per_group if lot.active else archived_per_group
                    bucket[product, company][lot.name] = lot

        blocked_by_archived = []
        for (product, company), mls in groups.items():
            lots = lots_per_group[product, company]
            archived = archived_per_group[product, company]
            for ml in mls:
                lot = lots.get(ml.lot_name)
                if lot:
                    ml.lot_id = lot.id
                elif ml.lot_name and ml.lot_name in archived:
                    blocked_by_archived.append((product, archived[ml.lot_name]))
                elif ml.lot_name:
                    ml_ids_to_create_lot.add(ml.id)
                else:
                    ml_ids_tracked_without_lot.add(ml.id)

        if blocked_by_archived:
            raise self._prepare_archived_lots_error(blocked_by_archived)
        dbg.logic.debug(
            "_update_done_lots: %d existing lots matched, create lots for %s, "
            "still without lot %s",
            sum(len(lots) for lots in lots_per_group.values()),
            list(ml_ids_to_create_lot),
            list(ml_ids_tracked_without_lot),
        )
        self.browse(ml_ids_to_create_lot)._create_production_lots()
        return self.browse(ml_ids_tracked_without_lot)

    @api.model
    def _prepare_archived_lots_error(self, product_lot_pairs):
        listed = "\n".join(
            sorted(
                _(
                    " - %(lot)s, on %(product)s",
                    lot=lot.name,
                    product=product.display_name,
                )
                for product, lot in product_lot_pairs
            )
        )
        return UserError(
            _(
                "These Lot/Serial Numbers exist but are archived, so they cannot "
                "receive stock:\n%(lots)s\n\n"
                "Un-archive one to use it again, or enter a different number.",
                lots=listed,
            ),
        )

    def _check_lots_supplied(self):
        if not self:
            return
        products_list = "\n".join(
            f"- {product_name}"
            for product_name in self.mapped("product_id.display_name")
        )
        raise UserError(
            _(
                "You need to supply a Lot/Serial Number for product:\n%(products)s",
                products=products_list,
            ),
        )

    def action_view_reference(self):
        self.check_singleton()
        if self.move_id:
            action = self.move_id.action_view_reference()
            if action.get("res_model") != "stock.move":
                return action
        return {
            "res_model": self._name,
            "type": "ir.actions.act_window",
            "views": [[False, "form"]],
            "res_id": self.id,
        }

    def _get_progressed_lines(self, vals, updates):
        if "date" in vals or not (
            "product_uom_id" in vals or "quantity" in vals or vals.get("picked", False)
        ):
            return self.browse()
        progressed_ids = set()
        for ml in self:
            if ml.state in ("draft", "cancel", "done"):
                continue
            if vals.get("picked", False) and not ml.picked:
                progressed_ids.add(ml.id)
                continue
            if ("quantity" in vals or "product_uom_id" in vals) and ml.picked:
                new_qty = ml._get_new_quantity_product_uom(vals, updates)
                if ml.product_uom_id.compare(ml.quantity_product_uom, new_qty) < 0:
                    progressed_ids.add(ml.id)
        if progressed_ids:
            dbg.logic.debug("_get_progressed_lines: %s", sorted(progressed_ids))
        return self.browse(progressed_ids)

    def _create_production_lots(self):
        self._check_serials_unique()
        key_to_mls = defaultdict(lambda: self.env["stock.move.line"])
        for ml in self:
            key_to_mls[ml.product_id.id, ml.lot_name] |= ml

        lots = self.env["stock.lot"].create(
            [mls[0]._prepare_new_lot_vals() for mls in key_to_mls.values()]
        )
        dbg.lifecycle.debug(
            "_create_production_lots: %s for %d line groups",
            dbg.rec(lots),
            len(key_to_mls),
        )
        for lot, mls in zip(lots, key_to_mls.values(), strict=True):
            mls.with_prefetch(self._prefetch_ids).write(
                {"lot_id": lot.with_prefetch(lots._ids).id}
            )

    def _check_serials_unique(self):
        serials = Counter(
            ml.lot_name for ml in self if ml.tracking == "serial" and ml.lot_name
        )
        duplicated = sorted(name for name, count in serials.items() if count > 1)
        if duplicated:
            raise ValidationError(
                _(
                    "A serial number identifies one unit, so it can appear on one move line "
                    "only. These are used more than once:\n%(serials)s",
                    serials="\n".join(f"- {name}" for name in duplicated),
                ),
            )

    def _prepare_quant_vals(self, vals):
        quant = self.env["stock.quant"].browse(vals.get("quant_id", 0))
        return {name: quant[name].id for name in RESERVATION_KEY_FIELDS}

    def _has_lot_context(self):
        self.check_singleton()
        return (
            self.move_id.picking_type_id
            or self.is_inventory
            or self.lot_id
            or self.move_id.scrap_id
        )

    def _get_pending_dest_moves(self):
        return self.move_id.move_dest_ids.filtered(
            lambda move: move.state not in ("done", "cancel")
        )

    def _get_linkable_moves(self):
        self.check_singleton()
        moves = self.picking_id.move_ids.filtered(
            lambda x: x.product_id == self.product_id
        )
        return moves.sorted(
            key=lambda m: m.product_uom_id.compare(m.quantity, m.product_uom_qty) < 0,
            reverse=True,
        )

    def _get_write_field_updates(self, vals):
        updates = {}
        if not self.env.context.get("skip_uom_conversion"):
            for key in (*RESTOCK_TRIGGER_FIELDS, "product_uom_id"):
                if key in vals:
                    updates[key] = (
                        vals[key]
                        if isinstance(vals[key], models.BaseModel)
                        else self.env[self._fields[key].comodel_name].browse(vals[key])
                    )
        return updates

    def _get_changed_write_fields(self, vals, updates):
        self.check_singleton()
        changed = {name for name, value in updates.items() if self[name] != value}
        if "quantity" in vals and self.product_uom_id.compare(
            vals["quantity"], self.quantity
        ):
            changed.add("quantity")
        return changed

    def _get_new_quantity_product_uom(self, vals, updates):
        self.check_singleton()
        return updates.get("product_uom_id", self.product_uom_id)._get_quantity_in_unit(
            vals.get("quantity", self.quantity),
            self.product_id.uom_id,
            rounding_method="HALF-UP",
        )

    def _link_or_create_moves(self):
        needing_a_move = self.filtered(
            lambda ml: not ml.move_id and ml.picking_id
        )._link_to_existing_moves()
        return needing_a_move._create_moves()

    def _link_to_existing_moves(self):
        unlinked = self.browse()
        lines_per_vals = defaultdict(self.browse)
        for move_line in self:
            linkable_moves = (
                move_line._get_linkable_moves()
                if move_line.picking_id.state != "done"
                else False
            )
            if not linkable_moves:
                unlinked |= move_line
                continue
            key = (
                linkable_moves[0].id,
                linkable_moves[0].picking_id.id,
                linkable_moves[0].picked,
            )
            lines_per_vals[key] |= move_line
        for (move_id, picking_id, picked), lines in lines_per_vals.items():
            vals = {"move_id": move_id, "picking_id": picking_id}
            if picked:
                vals["picked"] = True
            dbg.pipeline.debug(
                "_link_to_existing_moves: %s -> move %s", dbg.rec(lines), move_id
            )
            lines.write(vals)
        if unlinked:
            dbg.logic.debug(
                "_link_to_existing_moves: no linkable move for %s", dbg.rec(unlinked)
            )
        return unlinked

    def _create_moves(self):
        new_move_vals = []
        lines_per_new_move = []
        move_idx_by_key = {}
        for move_line in self:
            key = (
                (move_line.picking_id.id, move_line.product_id.id)
                if move_line.picking_id.state != "done"
                else None
            )
            idx = move_idx_by_key.get(key) if key else None
            if idx is not None:
                lines_per_new_move[idx] |= move_line
                continue
            if key:
                move_idx_by_key[key] = len(new_move_vals)
            new_move_vals.append(move_line._prepare_stock_move_vals())
            lines_per_new_move.append(move_line)

        if not new_move_vals:
            return self.env["stock.move"]
        dbg.pipeline.debug(
            "_create_moves: %d moves for %d lines", len(new_move_vals), len(self)
        )
        created_moves = self.env["stock.move"].create(new_move_vals)
        for new_move, lines in zip(created_moves, lines_per_new_move, strict=True):
            lines.move_id = new_move.id
            if new_move.picked:
                lines.picked = True
        return created_moves

    @api.model
    def _log_message(self, thread, tracked_record, template, vals):
        data = self._get_logged_relations(tracked_record, vals)
        thread.message_post_with_source(
            template,
            render_values={"move": tracked_record, "vals": data},
            subtype_xmlid="mail.mt_note",
        )

    @api.model
    def _get_logged_relations(self, tracked_record, vals):
        data = dict(vals)
        for field, render_key in LOGGED_RELATIONS:
            if field not in data:
                continue
            value = data[field]
            record = (
                value
                if isinstance(value, models.BaseModel)
                else self.env[self._fields[field].comodel_name].browse(value)
            )
            if record == tracked_record[field]:
                del data[field]
                continue
            data[render_key] = record.name
        return data

    @api.model
    def _prepare_create_vals(self, vals_list):
        moves = self.env["stock.move"].browse(
            OrderedSet(vals["move_id"] for vals in vals_list if vals.get("move_id"))
        )
        pickings = self.env["stock.picking"].browse(
            OrderedSet(
                vals["picking_id"]
                for vals in vals_list
                if not vals.get("move_id") and vals.get("picking_id")
            )
        )
        moves.fetch(["company_id", "picked"])
        pickings.fetch(["company_id"])
        prepared = []
        for vals in vals_list:
            changes = {}
            if vals.get("move_id"):
                move = moves.browse(vals["move_id"])
                changes["company_id"] = move.company_id.id
                if "picked" not in vals:
                    changes["picked"] = move.picked
            elif vals.get("picking_id"):
                changes["company_id"] = pickings.browse(
                    vals["picking_id"]
                ).company_id.id
            if vals.get("quant_id"):
                changes.update(self._prepare_quant_vals(vals))
            prepared.append({**vals, **changes} if changes else vals)
        return prepared

    def _prepare_new_lot_vals(self):
        self.check_singleton()
        vals = {
            "name": self.lot_name,
            "product_id": self.product_id.id,
        }
        if self.product_id.company_id and self.company_id in (
            self.product_id.company_id.all_child_ids | self.product_id.company_id
        ):
            vals["company_id"] = self.company_id.id
        return vals

    def _prepare_stock_move_vals(self):
        self.check_singleton()
        return {
            "product_id": self.product_id.id,
            "product_uom_qty": (
                0
                if self.picking_id and self.picking_id.state != "done"
                else self.quantity
            ),
            "product_uom_id": self.product_uom_id.id,
            "location_id": self.location_id.id,
            "location_dest_id": self.location_dest_id.id,
            "picked": self.picked,
            "picking_id": self.picking_id.id,
            "state": self.picking_id.state,
            "picking_type_id": self.picking_type_id.id,
            "restrict_partner_id": self.picking_id.owner_id.id,
            "company_id": self.company_id.id,
            "partner_id": self.picking_id.partner_id.id,
        }

    def _check_write_allowed(self, vals):
        if "product_id" in vals and any(
            ml.product_id
            and vals["product_id"] != ml.product_id.id
            and (ml.move_id or ml.state != "draft")
            for ml in self
        ):
            raise UserError(
                _(
                    "A move line's product is its operation's. Change it there, or"
                    " replace the line."
                )
            )

        if ("lot_id" in vals or "quant_id" in vals) and len(self.product_id) > 1:
            raise UserError(
                _(
                    "Changing the Lot/Serial number for move lines with different products is not allowed."
                ),
            )
