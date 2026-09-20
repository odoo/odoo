import logging
from collections import defaultdict

from odoo import api, fields, models
from odoo.api import SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import SQL
from odoo.tools.misc import OrderedSet, clean_context
from odoo.tools.translate import _

from ..const import INVENTORY_REFERENCE_CONFIRMED, INVENTORY_REFERENCE_UPDATED
from ..tools import debug_log as dbg

_logger = logging.getLogger(__name__)

PROCUREMENT_PRIORITIES = [("0", "Normal"), ("1", "Urgent")]

GENERATED_LOT_VALS_MAX = 10000

FIELD_DATA_IGNORED = "ignore"


class StockMove(models.Model):
    _name = "stock.move"
    _description = "Stock Move"
    _order = "sequence, id"
    _rec_name = "reference"

    _MAX_PUSH_DEPTH = 50
    _MAX_UPSTREAM_DEPTH = 100

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
        required=True,
    )
    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Transfer",
        index=True,
        check_company=True,
    )
    picking_code = fields.Selection(
        related="picking_id.picking_type_id.code",
        readonly=True,
    )
    picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Operation Type",
        compute="_compute_picking_type_id",
        precompute=True,
        store=True,
        readonly=False,
        check_company=True,
    )
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        help="the warehouse to consider for the route selection on the next procurement (if any).",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Destination Address ",
        compute="_compute_partner_id",
        store=True,
        index="btree_not_null",
        readonly=False,
        help="Optional address where goods are to be delivered, specifically used for allotment",
    )
    origin_returned_move_id = fields.Many2one(
        comodel_name="stock.move",
        string="Origin return move",
        index=True,
        copy=False,
        check_company=True,
        help="Move that created the return move",
    )
    returned_move_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="origin_returned_move_id",
        string="All returned moves",
        help="Optional: all returned moves created from this move",
    )
    sequence = fields.Integer(default=10)
    priority = fields.Selection(
        selection=PROCUREMENT_PRIORITIES,
        compute="_compute_priority",
        default="0",
        store=True,
    )
    origin = fields.Char(string="Source Document")
    date = fields.Datetime(
        string="Date Scheduled",
        default=fields.Datetime.now,
        index=True,
        required=True,
        help="Scheduled date until move is done, then date of actual move processing",
    )
    date_deadline = fields.Datetime(
        string="Deadline",
        copy=False,
        readonly=True,
        help="In case of outgoing flow, validate the transfer before this date to allow to deliver at promised date to the customer.\n\
        In case of incoming flow, validate the transfer before this date in order to have these products in stock at the date promised by the supplier",
    )
    location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Source Location",
        compute="_compute_location_id",
        precompute=True,
        store=True,
        index=True,
        readonly=False,
        required=True,
        check_company=True,
        bypass_search_access=True,
        help="The operation takes and suggests products from this location.",
    )
    location_usage = fields.Selection(
        related="location_id.usage",
        string="Source Location Type",
    )
    location_dest_id = fields.Many2one(
        comodel_name="stock.location",
        string="Intermediate Location",
        compute="_compute_location_dest_id",
        inverse="_inverse_location_dest_id",
        precompute=True,
        store=True,
        index=True,
        readonly=False,
        required=True,
        help="The operations brings product to this location",
    )
    location_dest_usage = fields.Selection(
        related="location_dest_id.usage",
        string="Destination Location Type",
    )
    location_final_id = fields.Many2one(
        comodel_name="stock.location",
        string="Final Location",
        store=True,
        index=True,
        readonly=False,
        check_company=True,
        bypass_search_access=True,
        help="The operation brings the products to the intermediate location."
        "But this operation is part of a chain of operations targeting the final location.",
    )
    procure_method = fields.Selection(
        selection=[
            ("make_to_stock", "Default: Take From Stock"),
            ("make_to_order", "Advanced: Apply Procurement Rules"),
        ],
        string="Supply Method",
        default="make_to_stock",
        copy=False,
        required=True,
        help="By default, the system will take from the stock in the source location and passively wait for availability. "
        "The other possibility allows you to directly create a procurement on the source location (and thus ignore "
        "its current stock) to gather products. If we want to chain moves and have this one to wait for the previous, "
        "this second option should be chosen.",
    )
    state = fields.Selection(
        selection=[
            ("draft", "New"),
            ("waiting", "Waiting Another Move"),
            ("confirmed", "Waiting"),
            ("partially_available", "Partially Available"),
            ("assigned", "Available"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        index=True,
        copy=False,
        readonly=True,
        help="* New: The stock move is created but not confirmed.\n"
        "* Waiting Another Move: A linked stock move should be done before this one.\n"
        "* Waiting: The stock move is confirmed but the product can't be reserved.\n"
        "* Available: The product of the stock move is reserved.\n"
        "* Done: The product has been transferred and the transfer has been confirmed.",
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        index=True,
        required=True,
        domain="[('type', '=', 'consu')]",
        check_company=True,
    )
    has_tracking = fields.Selection(
        related="product_id.tracking",
        string="Product with Tracking",
    )
    is_storable = fields.Boolean(related="product_id.is_storable")
    product_category_id = fields.Many2one(
        comodel_name="product.category",
        related="product_id.categ_id",
        string="Product Category",
    )
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        related="product_id.product_tmpl_id",
        string="Product Template",
    )
    never_product_template_attribute_value_ids = fields.Many2many(
        comodel_name="product.template.attribute.value",
        relation="template_attribute_value_stock_move_rel",
        column1="move_id",
        column2="template_attribute_value_id",
        string="Never attribute Values",
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
    product_uom_qty = fields.Float(
        string="Demand",
        digits="Product Unit",
        default=0,
        required=True,
        help="This is the quantity of product that is planned to be moved."
        "Lowering this quantity does not generate a backorder."
        "Changing this quantity on assigned moves affects "
        "the product reservation, and should be done with care.",
    )
    product_qty = fields.Float(
        string="Real Quantity",
        digits=0,
        compute="_compute_product_qty",
        inverse="_inverse_product_qty",
        compute_sudo=True,
        store=True,
        help="Quantity in the default UoM of the product",
    )
    description_picking_manual = fields.Text(readonly=True)
    description_picking = fields.Text(
        string="Description Of Picking",
        compute="_compute_description_picking",
        inverse="_inverse_description_picking",
        compute_sudo=True,
    )
    move_orig_ids = fields.Many2many(
        comodel_name="stock.move",
        relation="stock_move_move_rel",
        column1="move_dest_id",
        column2="move_orig_id",
        string="Original Move",
        copy=False,
        help="Optional: previous stock move when chaining them",
    )
    move_dest_ids = fields.Many2many(
        comodel_name="stock.move",
        relation="stock_move_move_rel",
        column1="move_orig_id",
        column2="move_dest_id",
        string="Destination Moves",
        copy=False,
        help="Optional: next stock move when chaining them",
    )

    price_unit = fields.Float(
        string="Unit Price",
        copy=False,
    )
    scrap_id = fields.Many2one(
        comodel_name="stock.scrap",
        string="Scrap operation",
        index="btree_not_null",
        readonly=True,
        check_company=True,
    )
    reference_ids = fields.Many2many(
        comodel_name="stock.reference",
        relation="stock_reference_move_rel",
        column1="move_id",
        column2="reference_id",
        string="References",
    )
    rule_id = fields.Many2one(
        comodel_name="stock.rule",
        string="Stock Rule",
        ondelete="restrict",
        check_company=True,
        help="The stock rule that created this stock move",
    )
    propagate_cancel = fields.Boolean(
        string="Propagate cancel and split",
        default=True,
        help="If checked, when this move is cancelled, cancel the linked move too",
    )
    date_delay_alert = fields.Datetime(
        string="Delay Alert Date",
        compute="_compute_date_delay_alert",
        store=True,
        help="Process at this date to be on time",
    )
    is_inventory = fields.Boolean(string="Inventory")
    inventory_name = fields.Char(readonly=True)

    move_line_ids = fields.One2many(
        comodel_name="stock.move.line",
        inverse_name="move_id",
    )
    package_ids = fields.One2many(
        comodel_name="stock.package",
        string="Packages",
        compute="_compute_package_ids",
    )
    restrict_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Owner ",
        index="btree_not_null",
        check_company=True,
    )
    route_ids = fields.Many2many(
        comodel_name="stock.route",
        relation="stock_route_move",
        column1="move_id",
        column2="route_id",
        string="Destination route",
        help="Preferred route",
    )
    quantity = fields.Float(
        digits="Product Unit",
        compute="_compute_quantity",
        inverse="_inverse_quantity",
        store=True,
    )
    reference = fields.Char(
        compute="_compute_reference",
        store=True,
    )
    has_partial_result_packages = fields.Boolean(
        compute="_compute_has_partial_result_packages"
    )
    show_details_visible = fields.Boolean(
        string="Details Visible",
        compute="_compute_show_details_visible",
    )
    additional = fields.Boolean(
        string="Whether the move was added after the picking's confirmation",
        default=False,
    )
    picked = fields.Boolean(
        compute="_compute_picked",
        inverse="_inverse_picked",
        store=True,
        copy=False,
        readonly=False,
        help="This checkbox is just indicative, it doesn't validate or generate any product moves.",
    )
    is_locked = fields.Boolean(
        compute="_compute_is_locked",
        readonly=True,
    )
    is_initial_demand_editable = fields.Boolean(
        string="Is initial demand editable",
        compute="_compute_is_initial_demand_editable",
    )
    is_quantity_done_editable = fields.Boolean(
        string="Is quantity done editable",
        compute="_compute_is_quantity_done_editable",
    )
    move_lines_count = fields.Count(count_of="move_line_ids")
    show_lot_actions = fields.Boolean(
        string="Show Lot/Serial Actions",
        compute="_compute_show_info",
        help="Whether the Generate/Import Serials-Lots buttons apply to this move.",
    )
    next_serial = fields.Char(string="First SN/Lot")
    next_serial_count = fields.Integer(string="Number of SN/Lots")
    orderpoint_id = fields.Many2one(
        comodel_name="stock.warehouse.orderpoint",
        string="Original Reordering Rule",
        index=True,
    )
    forecast_availability = fields.Float(
        digits="Product Unit",
        compute="_compute_forecast_information",
        compute_sudo=True,
    )
    date_planned_forecast = fields.Datetime(
        string="Forecasted Expected date",
        compute="_compute_forecast_information",
        compute_sudo=True,
    )
    lot_ids = fields.Many2many(
        comodel_name="stock.lot",
        string="Serial Numbers",
        compute="_compute_lot_ids",
        inverse="_inverse_lot_ids",
        readonly=False,
    )
    date_reservation = fields.Date(
        string="Date to Reserve",
        compute="_compute_date_reservation",
        store=True,
        help="Computes when a move should be reserved",
    )
    packaging_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Packaging",
        compute="_compute_packaging_uom_id",
        precompute=True,
        store=True,
        help="Packaging unit from sale or purchase orders",
    )
    quantity_packaging_uom = fields.Float(
        string="Packaging Quantity",
        compute="_compute_quantity_packaging_uom",
        store=True,
        help="Quantity in the packaging unit",
    )
    show_quant = fields.Boolean(compute="_compute_show_info")
    show_lots_m2o = fields.Boolean(
        string="Show lot_id",
        compute="_compute_show_info",
    )
    show_lots_text = fields.Boolean(
        string="Show lot_name",
        compute="_compute_show_info",
    )

    completion_sequence = fields.Integer(
        string="Completion Order",
        index="btree_not_null",
        copy=False,
        readonly=True,
        help="Position of this move among all moves that reached 'Done'. `date` has"
        " one-second resolution and a move's id is its creation order, so neither"
        " tells two moves done in the same second apart; this does.",
    )

    _product_location_index = models.Index(
        "(product_id, location_id, location_dest_id, company_id, state)",
    )

    def init(self):
        super().init()
        self.env.cr.execute("CREATE SEQUENCE IF NOT EXISTS stock_move_completion_seq")

    def _update_completion_sequence(self):
        pending = self.filtered(
            lambda m: m.state == "done" and not m.completion_sequence
        )
        if not pending:
            return
        dbg.lifecycle.debug("completion sequence assigned to %s", dbg.rec(pending))
        self.env.execute_query(
            SQL(
                """
                UPDATE stock_move m
                   SET completion_sequence = numbered.seq
                  FROM (
                        SELECT u.id, nextval('stock_move_completion_seq') AS seq
                          FROM unnest(%s::int[]) AS u(id)
                       ) AS numbered
                 WHERE m.id = numbered.id
                   AND m.completion_sequence IS NULL
                """,
                list(pending.ids),
            )
        )
        pending.invalidate_recordset(["completion_sequence"])

    @dbg.timed
    @api.model_create_multi
    def create(self, vals_list):
        dbg.lifecycle.debug(
            "stock.move.create: %d vals, keys=%s",
            len(vals_list),
            dbg.vals_keys(vals_list),
        )
        vals_list = self._prepare_create_vals(vals_list)
        res = super().create(vals_list)
        res._update_completion_sequence()
        res._update_orderpoints()
        res._update_references()
        dbg.lifecycle.debug("stock.move.create: created %s", dbg.rec(res))
        return res

    def _prepare_create_vals(self, vals_list):
        picking_ids = {
            vals["picking_id"] for vals in vals_list if vals.get("picking_id")
        }
        picking_state_by_id = {
            picking.id: picking.state
            for picking in self.env["stock.picking"].browse(picking_ids).exists()
        }
        prepared = []
        for vals in vals_list:
            changes = {}
            if vals.get("move_line_ids") and "lot_ids" in vals:
                vals = {k: v for k, v in vals.items() if k != "lot_ids"}
            if (
                picking_state_by_id.get(vals.get("picking_id")) == "done"
                and vals.get("state") != "done"
            ):
                changes["state"] = "done"
            if changes.get("state", vals.get("state")) == "done":
                changes["picked"] = True
            if changes:
                dbg.logic.debug(
                    "_prepare_create_vals: picking %s forces %s on product %s",
                    vals.get("picking_id"),
                    changes,
                    vals.get("product_id"),
                )
            prepared.append({**vals, **changes} if changes else vals)
        return prepared

    @dbg.timed
    def write(self, vals):
        dbg.lifecycle.debug(
            "stock.move.write on %s: keys=%s state=%s",
            dbg.rec(self),
            dbg.keys(vals),
            vals.get("state"),
        )
        vals = self._check_write_vals(vals)
        receipt_moves_to_reassign = self.env["stock.move"]
        move_to_recompute_state = self.env["stock.move"]
        move_to_check_location = self.env["stock.move"]
        if "product_uom_qty" in vals:
            receipt_moves_to_reassign, move_to_recompute_state = self._on_demand_change(
                vals
            )
        if "date_deadline" in vals:
            self._update_date_deadline(vals.get("date_deadline"))
        if "move_orig_ids" in vals:
            move_to_recompute_state |= self.filtered(
                lambda m: m.state not in ["draft", "cancel", "done"],
            )
        if "location_id" in vals:
            move_to_check_location = self.filtered(
                lambda m: m.location_id.id != vals.get("location_id"),
            )
        moves_leaving_orderpoint_scope = self.filtered(
            lambda m: any(
                key in vals and m[key].id != vals[key]
                for key in ("product_id", "location_id", "location_dest_id")
            ),
        )
        if moves_leaving_orderpoint_scope:
            dbg.logic.debug(
                "write: %s leave orderpoint scope",
                dbg.rec(moves_leaving_orderpoint_scope),
            )
            moves_leaving_orderpoint_scope._update_orderpoints()
        if receipt_moves_to_reassign or move_to_recompute_state:
            dbg.logic.debug(
                "write: reassign=%s recompute_state=%s check_location=%s",
                dbg.rec(receipt_moves_to_reassign),
                dbg.rec(move_to_recompute_state),
                dbg.rec(move_to_check_location),
            )

        res = super().write(vals)

        if vals.get("state") == "done":
            self._update_completion_sequence()
        if "date" in vals:
            moves_done = self.filtered(lambda m: m.state == "done")
            moves_done.move_line_ids.date = vals["date"]
        if move_to_recompute_state:
            move_to_recompute_state._recompute_state()
        receipt_moves_to_reassign |= move_to_check_location._on_source_location_change()
        if "location_id" in vals or "location_dest_id" in vals:
            self._sync_warehouse_from_locations()
        if receipt_moves_to_reassign:
            dbg.pipeline.debug(
                "write -> _action_assign on receipts %s",
                dbg.rec(receipt_moves_to_reassign),
            )
            receipt_moves_to_reassign._action_assign()
        if (
            "product_id" in vals
            or "state" in vals
            or "date" in vals
            or "product_uom_qty" in vals
            or "location_id" in vals
            or "location_dest_id" in vals
        ):
            self._update_orderpoints()
        if "picking_id" in vals:
            self._update_references()
        return res

    @dbg.timed
    def unlink(self):
        dbg.lifecycle.debug("stock.move.unlink %s", dbg.rec(self))
        self._unlink_except_done_or_linked()
        self.with_context(prefetch_fields=False).mapped("move_line_ids").unlink()
        orderpoints = self._get_orderpoints_to_update()
        res = super().unlink()
        self._update_orderpoints(orderpoints)
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done_or_linked(self):
        for move in self:
            if move.state == "done":
                raise UserError(
                    _(
                        "You cannot delete a stock move that has been set to 'Done'."
                        " Create a return in order to reverse the moves which took place.",
                    ),
                )
            if move.state not in ("draft", "cancel") and (
                move.move_orig_ids or move.move_dest_ids
            ):
                raise UserError(
                    _("You can not delete moves linked to another operation"),
                )

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)
        if self.env.context.get("default_picking_id"):
            picking = self.env["stock.picking"].browse(
                self.env.context["default_picking_id"],
            )
            if picking.state == "done":
                defaults["state"] = "done"
                defaults["additional"] = True
            elif picking.state not in ("cancel", "draft"):
                defaults["additional"] = True
            dbg.logic.debug(
                "default_get: picking %s in state %s -> state=%s additional=%s",
                picking.id,
                picking.state,
                defaults.get("state"),
                defaults.get("additional"),
            )
        return defaults

    @api.depends(
        "product_id",
        "product_id.uom_id",
        "product_id.uom_ids",
        "product_id.seller_ids",
        "product_id.seller_ids.product_uom_id",
    )
    def _compute_allowed_uom_ids(self):
        for move in self:
            move.allowed_uom_ids = (
                move.product_id.uom_id
                | move.product_id.uom_ids
                | move.sudo().product_id.seller_ids.product_uom_id
            )

    @api.depends("product_id")
    def _compute_product_uom_id(self):
        for move in self:
            move.product_uom_id = move.product_id.uom_id.id

    @api.depends("picking_id.location_id", "picking_type_id.default_location_src_id")
    def _compute_location_id(self):
        for move in self:
            location = move.location_id
            if not location or (
                not move.picked and move.picking_id != move._origin.picking_id
            ):
                if move.picking_id:
                    location = move.picking_id.location_id
                elif move.picking_type_id:
                    location = move.picking_type_id.default_location_src_id
            move.location_id = location

    @api.depends(
        "picking_id.location_dest_id",
        "location_final_id",
        "picking_type_id.default_location_dest_id",
        "rule_id.location_dest_id",
        "rule_id.location_dest_from_rule",
    )
    def _compute_location_dest_id(self):
        customer_loc, __ = self.env["stock.warehouse"]._get_partner_locations()
        inter_comp_location = self.env.ref(
            "stock.stock_location_inter_company",
            raise_if_not_found=False,
        )
        for move in self:
            if move.state in ("done", "cancel") or (
                move.location_dest_id and move.location_dest_id.usage == "inventory"
            ):
                move.location_dest_id = move.location_dest_id
                continue
            if move.picking_id:
                location_dest = move.picking_id.location_dest_id
            elif move.rule_id.location_dest_from_rule:
                location_dest = move.rule_id.location_dest_id
            elif move.picking_type_id:
                location_dest = move.picking_type_id.default_location_dest_id
            else:
                location_dest = move.location_dest_id
            is_move_to_interco_transit = False
            if location_dest:
                is_move_to_interco_transit = (
                    location_dest._is_child_of(customer_loc)
                    and move.location_final_id == inter_comp_location
                )
            if (
                location_dest
                and move.location_final_id
                and (
                    move.location_final_id._is_child_of(location_dest)
                    or is_move_to_interco_transit
                )
            ):
                location_dest = move.location_final_id
            move.location_dest_id = location_dest

    @api.depends("move_line_ids.result_package_id")
    def _compute_has_partial_result_packages(self):
        for move in self:
            move.has_partial_result_packages = bool(
                move.move_line_ids.result_package_id
                and any(not line.result_package_id for line in move.move_line_ids)
            )

    @api.depends(
        "move_line_ids",
        "move_line_ids.package_history_id",
        "move_line_ids.result_package_id",
        "move_line_ids.result_package_id.outermost_package_id",
        "state",
    )
    def _compute_package_ids(self):
        for move in self:
            package_history = move.move_line_ids.package_history_id
            if move.state in ["done", "cancel"] and package_history:
                move.package_ids = package_history.outermost_dest_id
            else:
                move.package_ids = (
                    move.move_line_ids.result_package_id.outermost_package_id
                )

    @api.depends("move_line_ids.picked", "state")
    def _compute_picked(self):
        for move in self:
            if move.state == "done" or any(ml.picked for ml in move.move_line_ids):
                move.picked = True
            elif move.move_line_ids:
                move.picked = False
            else:
                move.picked = move.picked

    @api.depends("picking_id.priority")
    def _compute_priority(self):
        for move in self:
            move.priority = move.picking_id.priority or "0"

    @api.depends("picking_id.picking_type_id")
    def _compute_picking_type_id(self):
        for move in self:
            if move.picking_id:
                move.picking_type_id = move.picking_id.picking_type_id
            else:
                move.picking_type_id = move.picking_type_id

    @api.depends("picking_id.is_locked")
    def _compute_is_locked(self):
        for move in self:
            if move.picking_id:
                move.is_locked = move.picking_id.is_locked
            else:
                move.is_locked = False

    @api.depends("product_id", "has_tracking", "move_line_ids")
    @api.depends_context("uid")
    def _compute_show_details_visible(self):
        has_package = self.env.user.has_group("stock.group_tracking_lot")
        multi_locations_enabled = self.env.user.has_group(
            "stock.group_stock_multi_locations",
        )
        consignment_enabled = self.env.user.has_group("stock.group_tracking_owner")

        show_details_visible = (
            multi_locations_enabled or has_package or consignment_enabled
        )

        for move in self:
            if (
                not move.product_id
                or move.state == "draft"
                or (
                    not move.picking_type_id.use_create_lots
                    and not move.picking_type_id.use_existing_lots
                    and not has_package
                    and not multi_locations_enabled
                )
            ):
                move.show_details_visible = False
            elif len(move.move_line_ids) > 1:
                move.show_details_visible = True
            else:
                move.show_details_visible = (
                    show_details_visible or move.has_tracking != "none"
                )

    @api.depends("state", "picking_id.is_locked")
    def _compute_is_initial_demand_editable(self):
        for move in self:
            move.is_initial_demand_editable = (
                not move.picking_id.is_locked or move.state == "draft"
            )

    @api.depends("product_id")
    def _compute_is_quantity_done_editable(self):
        for move in self:
            move.is_quantity_done_editable = bool(move.product_id)

    @api.depends(
        "picking_id.name",
        "scrap_id.name",
        "is_inventory",
        "inventory_name",
        "create_uid",
        "quantity",
    )
    def _compute_reference(self):
        for move in self:
            if move.scrap_id:
                move.reference = move.scrap_id.name
            elif move.is_inventory:
                move.reference = move.inventory_name or move._get_inventory_reference()
            else:
                move.reference = move.picking_id.name

    def _get_inventory_reference(self):
        self.check_singleton()
        label = (
            INVENTORY_REFERENCE_CONFIRMED
            if self.product_uom_id.is_zero(self.quantity)
            else INVENTORY_REFERENCE_UPDATED
        )
        if self.create_uid and self.create_uid.id != SUPERUSER_ID:
            label += f" ({self.create_uid.display_name})"
        return label

    # `product_uom_id.factor` is read here, through `_get_quantity_stored`,
    # and is deliberately NOT declared. `uom.uom.write` refuses a ratio change
    # only while moves are OPEN (`state not in ("cancel", "done")`), so a unit
    # can be re-rated once its moves are done -- and a done move's `product_qty`
    # is what was actually moved, not a conversion to be replayed. Measured: a
    # done move of 2 boxes at 10 units records 20; after the box is re-rated to
    # 20 units the stored value stays 20, and a forced recompute writes 40.
    # Declaring the dependency would rewrite history on every historical move
    # whose unit was ever re-rated.
    @api.depends("product_id", "product_uom_id", "product_uom_qty")
    def _compute_product_qty(self):
        for move in self:
            move.product_qty = move.product_uom_id._get_quantity_stored(
                move.product_uom_qty,
                move.product_id.uom_id,
            )

    @api.depends("picking_id.partner_id")
    def _compute_partner_id(self):
        for move in self:
            if move.picking_id:
                move.partner_id = move.picking_id.partner_id
            else:
                move.partner_id = move.partner_id

    @api.depends("move_line_ids.quantity", "move_line_ids.product_uom_id")
    def _compute_quantity(self):
        new_moves = self._new_records
        for move in new_moves:
            move.quantity = move._get_move_line_quantity()

        saved_moves = self - new_moves
        if not saved_moves:
            return
        data = self.env["stock.move.line"]._read_group(
            [("move_id", "in", saved_moves.ids)],
            ["move_id", "product_uom_id"],
            ["quantity:sum"],
        )
        sum_qty = defaultdict(float)
        for move, product_uom_id, qty_sum in data:
            uom = move.product_uom_id
            sum_qty[move.id] += product_uom_id._get_quantity_in_unit(
                qty_sum,
                uom,
                round=False,
            )

        for move in saved_moves:
            move.quantity = sum_qty[move.id]

    @api.depends("product_uom_id")
    def _compute_packaging_uom_id(self):
        for move in self:
            move.packaging_uom_id = move.product_uom_id

    # `product_uom_id.factor` is deliberately absent for the same reason as on
    # `_compute_product_qty` above: a re-rated unit must not restate what a done
    # move recorded.
    @api.depends("product_uom_qty", "product_uom_id", "packaging_uom_id")
    def _compute_quantity_packaging_uom(self):
        for move in self:
            packaging_uom = move.packaging_uom_id
            if not packaging_uom:
                move.quantity_packaging_uom = 0.0
            elif move.product_uom_id._has_common_reference(packaging_uom):
                move.quantity_packaging_uom = move.product_uom_id._get_quantity_in_unit(
                    move.product_uom_qty,
                    packaging_uom,
                )
            else:
                move.quantity_packaging_uom = move.product_uom_qty

    @api.depends(
        "has_tracking",
        "product_id",
        "product_id.type",
        "picking_code",
        "picking_type_id.use_create_lots",
        "picking_type_id.use_existing_lots",
        "origin_returned_move_id",
        "state",
    )
    def _compute_show_info(self):
        for move in self:
            tracked = move.has_tracking != "none"
            creates_lots = move.picking_type_id.use_create_lots
            uses_existing_lots = move.picking_type_id.use_existing_lots
            is_return = bool(move.origin_returned_move_id.id)

            move.show_lot_actions = bool(
                tracked
                and move.product_id
                and creates_lots
                and not is_return
                and move.state not in ("done", "cancel")
            )
            move.show_quant = (
                move.picking_code != "incoming" and move.product_id.is_storable
            )
            move.show_lots_text = (
                tracked
                and creates_lots
                and not uses_existing_lots
                and move.state != "done"
                and not is_return
            )
            move.show_lots_m2o = (
                not move.show_quant
                and not move.show_lots_text
                and tracked
                and (uses_existing_lots or move.state == "done" or is_return)
            )

    @api.depends("picking_id", "product_id", "location_id", "location_dest_id")
    def _compute_display_name(self):
        for move in self:
            move.display_name = "%s%s%s>%s" % (
                (move.picking_id.origin and "%s/" % move.picking_id.origin) or "",
                (move.product_id.code and "%s: " % move.product_id.code) or "",
                move.location_id.name,
                move.location_dest_id.name,
            )

    @api.depends("product_id", "picking_type_id", "description_picking_manual")
    def _compute_description_picking(self):
        for move in self:
            if move.description_picking_manual:
                move.description_picking = move.description_picking_manual
            elif move.product_id:
                product = move.product_id.with_context(lang=move._get_lang())
                move.description_picking = (
                    product._get_picking_description(move.picking_type_id)
                    or move._get_description()
                )
            else:
                move.description_picking = ""

    def _inverse_location_dest_id(self):
        for ml in self.move_line_ids:
            if ml.location_dest_id._is_child_of(ml.move_id.location_dest_id):
                continue
            loc_dest = ml.move_id.location_dest_id._get_putaway_strategy(
                ml.product_id,
                ml.quantity_product_uom,
            )
            ml.location_dest_id = loc_dest

    def _inverse_picked(self):
        for move in self:
            move.move_line_ids.picked = move.picked

    def _inverse_quantity(self):
        def decrease_move_line_quantities(move, quantity):
            mls_to_unlink = set()
            for ml in reversed(move.move_line_ids.sorted("id")):
                if self.env.context.get("unreserve_unpicked_only") and ml.picked:
                    continue
                if move.product_uom_id.is_zero(quantity):
                    break
                qty_ml_dec = min(
                    ml.quantity,
                    move.product_uom_id._get_quantity_in_unit(
                        quantity,
                        ml.product_uom_id,
                        round=False,
                    ),
                )
                if ml.product_uom_id.is_zero(qty_ml_dec):
                    continue
                if ml.product_uom_id.compare(
                    ml.quantity,
                    qty_ml_dec,
                ) == 0 and ml.state not in ["done", "cancel"]:
                    mls_to_unlink.add(ml.id)
                else:
                    ml.quantity -= qty_ml_dec
                quantity -= ml.product_uom_id._get_quantity_in_unit(
                    qty_ml_dec,
                    move.product_uom_id,
                    round=False,
                )
            self.env["stock.move.line"].browse(mls_to_unlink).unlink()

        # the lines the increases add are created in one batch: a create per
        # move reserves, links and recomputes states one move at a time
        commands_by_move = {}
        for move in self:
            delta_qty = move.quantity - move._get_move_line_quantity()
            dbg.logic.debug(
                "[move:%s] _inverse_quantity: quantity=%s delta=%s",
                move.id,
                move.quantity,
                delta_qty,
            )
            if move.product_uom_id.compare(delta_qty, 0) > 0:
                commands_by_move[move] = move._prepare_quantity_done_vals(move.quantity)
            elif move.product_uom_id.compare(delta_qty, 0) < 0:
                decrease_move_line_quantities(move, abs(delta_qty))
        if commands_by_move:
            self._apply_quantity_done_vals(commands_by_move)

    def _inverse_product_qty(self):
        raise UserError(
            _(
                "The requested operation cannot be processed because of a programming error setting the `product_qty` field instead of the `product_uom_qty`.",
            ),
        )

    def _inverse_description_picking(self):
        for move in self:
            move.description_picking_manual = move.description_picking

    @dbg.timed
    def _action_confirm(self, merge=True, merge_into=False, create_proc=True):
        dbg.pipeline.debug(
            "_action_confirm start on %s merge=%s merge_into=%s create_proc=%s",
            dbg.rec(self),
            merge,
            dbg.rec(merge_into) if merge_into else False,
            create_proc,
        )
        consumed_from_stock_dict = self.env.context.get(
            "consumed_from_stock_dict",
            defaultdict(float),
        )
        move_create_proc, move_to_confirm, move_waiting = (
            OrderedSet(),
            OrderedSet(),
            OrderedSet(),
        )
        to_assign = OrderedSet()
        for move in self:
            if move.state != "draft":
                continue
            if move.move_orig_ids:
                move_waiting.add(move.id)
            elif move.procure_method == "make_to_order":
                move_waiting.add(move.id)
                if create_proc:
                    move_create_proc.add(move.id)
            elif move.rule_id and move.rule_id.procure_method == "mts_else_mto":
                move_to_confirm.add(move.id)
                if create_proc:
                    move_create_proc.add(move.id)
            else:
                move_to_confirm.add(move.id)
            if move._is_assignment_required():
                to_assign.add(move.id)

        dbg.logic.debug(
            "_action_confirm: create_proc=%s to_confirm=%s waiting=%s to_assign=%s",
            list(move_create_proc),
            list(move_to_confirm),
            list(move_waiting),
            list(to_assign),
        )
        if move_create_proc:
            dbg.pipeline.debug(
                "_action_confirm -> _run_procurements for %s", list(move_create_proc)
            )
        self.browse(move_create_proc)._run_procurements(consumed_from_stock_dict)

        move_to_confirm, move_waiting = (
            self.browse(move_to_confirm).filtered(lambda m: m.state != "cancel"),
            self.browse(move_waiting).filtered(lambda m: m.state != "cancel"),
        )
        dbg.lifecycle.debug(
            "_action_confirm: %s -> confirmed, %s -> waiting",
            dbg.rec(move_to_confirm),
            dbg.rec(move_waiting),
        )
        move_to_confirm.write({"state": "confirmed"})
        move_waiting.write({"state": "waiting"})
        (move_to_confirm | move_waiting).filtered(
            lambda m: m.picking_type_id.reservation_method == "at_confirm",
        ).write({"date_reservation": fields.Date.today()})

        if to_assign:
            dbg.pipeline.debug(
                "_action_confirm -> _update_picking for %s", list(to_assign)
            )
            self.browse(to_assign).with_context(
                clean_context(self.env.context),
            )._update_picking()

        self._check_company()
        moves = self
        if merge:
            moves = self._merge_moves(merge_into=merge_into)
            dbg.pipeline.debug(
                "_action_confirm: merged %d moves into %s", len(self), dbg.rec(moves)
            )

        new_push_moves = moves._reverse_negative_demand()

        to_assign_now = moves._filtered_to_assign_at_confirm()
        dbg.pipeline.debug(
            "_action_confirm -> _action_assign %s, push moves %s",
            dbg.rec(to_assign_now),
            dbg.rec(new_push_moves),
        )
        to_assign_now._action_assign()
        new_push_moves._confirm_pushed_moves()
        return moves

    def _action_synch_order(self):
        return True

    @dbg.timed
    def _action_cancel(self):
        dbg.pipeline.debug("_action_cancel start on %s", dbg.rec(self))
        if any(
            move.state == "done" and move.location_dest_usage != "inventory"
            for move in self
        ):
            raise UserError(
                _(
                    "You cannot cancel a stock move that has been set to 'Done'. Create a return in order to reverse the moves which took place.",
                ),
            )
        moves_to_cancel = self.filtered(
            lambda m: (
                m.state != "cancel"
                and not (m.state == "done" and m.location_dest_usage == "inventory")
            ),
        )
        moves_to_cancel._unreserve(force=True)
        moves_to_cancel.picked = False
        cancel_moves_origin = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("stock.cancel_moves_origin")
        )

        dbg.lifecycle.debug(
            "_action_cancel: %s -> cancel (cancel_moves_origin=%s)",
            dbg.rec(moves_to_cancel),
            cancel_moves_origin,
        )
        moves_to_cancel.state = "cancel"

        for move in moves_to_cancel:
            siblings_states = (
                move.move_dest_ids.mapped("move_orig_ids") - move
            ).mapped("state")
            dbg.logic.debug(
                "[move:%s] _action_cancel: propagate_cancel=%s siblings=%s dests=%s",
                move.id,
                move.propagate_cancel,
                siblings_states,
                dbg.rec(move.move_dest_ids),
            )
            if move.propagate_cancel:
                if all(state == "cancel" for state in siblings_states):
                    move_dest_to_cancel = move.move_dest_ids.filtered(
                        lambda m, move=move: (
                            m.state != "done" and move.location_dest_id == m.location_id
                        )
                    )
                    move_dest_to_cancel._action_cancel()
                    (move.move_dest_ids - move_dest_to_cancel).write(
                        {
                            "procure_method": "make_to_stock",
                            "move_orig_ids": [Command.unlink(move.id)],
                        },
                    )
                    if cancel_moves_origin:
                        move.move_orig_ids.sudo().filtered(
                            lambda m: m.state != "done",
                        )._action_cancel()
            elif all(state in ("done", "cancel") for state in siblings_states):
                move_dest_ids = move.move_dest_ids
                move_dest_ids.write(
                    {
                        "procure_method": "make_to_stock",
                        "move_orig_ids": [Command.unlink(move.id)],
                    },
                )
        if not self.env.context.get("skip_cancel_activity"):
            moves_to_cancel._log_cancel_activity()
        moves_to_cancel.write(
            {
                "move_orig_ids": [Command.clear()],
                "procure_method": "make_to_stock",
            },
        )
        return True

    def _get_relevant_state_among_moves(self):
        sort_map = {
            "assigned": 4,
            "waiting": 3,
            "partially_available": 2,
            "confirmed": 1,
        }
        moves_todo = self.filtered(
            lambda move: (
                move.state not in ["cancel", "done"]
                and not (move.state == "assigned" and not move.product_uom_qty)
            ),
        ).sorted(key=lambda move: (sort_map.get(move.state, 0), move.product_uom_qty))
        if not moves_todo:
            return "assigned"
        least_available = moves_todo[:1]
        most_available = moves_todo[-1:]
        if least_available.picking_id and least_available.picking_id.move_type == "one":
            if all(not m.product_uom_qty for m in moves_todo):
                return "assigned"
            if least_available.state in ("confirmed", "partially_available"):
                return "confirmed"
            return least_available.state or "draft"
        if least_available.state != "assigned" and any(
            move.state in ("assigned", "partially_available") for move in moves_todo
        ):
            return "partially_available"
        if (
            most_available.state == "confirmed"
            and most_available.product_uom_id.is_zero(
                most_available.product_uom_qty,
            )
        ):
            return "assigned"
        return most_available.state or "draft"

    def _get_picked_quantity(self):
        self.check_singleton()
        if self.picked and any(not ml.picked for ml in self.move_line_ids):
            picked_qty = 0
            for ml in self.move_line_ids:
                if not ml.picked:
                    continue
                picked_qty += ml.product_uom_id._get_quantity_in_unit(
                    ml.quantity,
                    self.product_uom_id,
                    round=False,
                )
            return picked_qty
        return self.quantity

    def _on_demand_change(self, vals):
        new_qty = vals["product_uom_qty"]
        for move in self.filtered(
            lambda m: m.state not in ("done", "draft") and m.picking_id,
        ):
            if move.product_uom_id.compare(new_qty, move.product_uom_qty):
                self.env["stock.move.line"]._log_message(
                    move.picking_id,
                    move,
                    "stock.track_move_template",
                    vals,
                )
        if self.env.context.get("do_not_unreserve"):
            dbg.logic.debug("_on_demand_change: do_not_unreserve, nothing to do")
            return self.browse(), self.browse()
        move_to_unreserve = self.filtered(
            lambda m: (
                m.state not in ["draft", "done", "cancel"]
                and m.product_uom_id.compare(m.quantity, new_qty) == 1
            ),
        )
        move_to_unreserve._unreserve()
        still_reserved = self - move_to_unreserve
        still_reserved.filtered(lambda m: m.state == "assigned").write(
            {"state": "partially_available"},
        )
        receipt_moves_to_reassign = move_to_unreserve.filtered(
            lambda m: m.location_id.usage == "supplier",
        )
        receipt_moves_to_reassign |= still_reserved.filtered(
            lambda m: (
                m.location_id.usage == "supplier"
                and m.state in ("partially_available", "assigned")
            ),
        )
        receipt_moves_to_reassign -= receipt_moves_to_reassign.filtered("picked")
        move_to_recompute_state = self - move_to_unreserve - receipt_moves_to_reassign
        dbg.logic.debug(
            "_on_demand_change to %s: unreserve=%s reassign=%s recompute=%s",
            new_qty,
            dbg.rec(move_to_unreserve),
            dbg.rec(receipt_moves_to_reassign),
            dbg.rec(move_to_recompute_state),
        )
        return receipt_moves_to_reassign, move_to_recompute_state

    def _on_source_location_change(self):
        mls_to_unlink = self.move_line_ids.filtered(
            lambda ml: not ml.location_id._is_child_of(ml.move_id.location_id),
        )
        if not mls_to_unlink:
            return self.browse()
        affected = mls_to_unlink.move_id
        dbg.logic.debug(
            "_on_source_location_change: unlink %s, %s -> make_to_stock",
            dbg.rec(mls_to_unlink),
            dbg.rec(affected),
        )
        affected.procure_method = "make_to_stock"
        affected.move_orig_ids = [Command.clear()]
        mls_to_unlink.unlink()
        return affected

    def _post_process_created_moves(self):
        pass

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        self.check_singleton()
        vals = {
            "move_id": self.id,
            "product_id": self.product_id.id,
            "product_uom_id": self.product_uom_id.id,
            "location_id": self.location_id.id,
            "location_dest_id": self.location_dest_id.id,
            "picking_id": self.picking_id.id,
            "company_id": self.company_id.id,
        }
        if quantity:
            uom_quantity = self._get_uom_quantity_if_faithful(
                quantity, self.product_uom_id
            )
            if uom_quantity is not None:
                vals = dict(vals, quantity=uom_quantity)
            else:
                vals = dict(
                    vals,
                    quantity=quantity,
                    product_uom_id=self.product_id.uom_id.id,
                )
        package = None
        if reserved_quant:
            package = reserved_quant.package_id
            vals = dict(
                vals,
                location_id=reserved_quant.location_id.id,
                lot_id=reserved_quant.lot_id.id or False,
                package_id=package.id or False,
                owner_id=reserved_quant.owner_id.id or False,
            )
        return vals

    def _get_move_line_quantity(self):
        self.check_singleton()
        quantity = 0
        for move_line in self.move_line_ids:
            quantity += move_line.product_uom_id._get_quantity_in_unit(
                move_line.quantity,
                self.product_uom_id,
                round=False,
            )
        return self.product_uom_id.round(quantity)

    def _recompute_state(self):
        if self.env.context.get("preserve_state"):
            dbg.logic.debug(
                "_recompute_state skipped (preserve_state) on %s", dbg.rec(self)
            )
            return
        moves_state_to_write = defaultdict(set)
        for move in self:
            uom = move.product_uom_id
            if move.state in ("cancel", "done") or (
                move.state == "draft" and not move.quantity
            ):
                continue
            if uom.compare(move.quantity, move.product_uom_qty) >= 0:
                moves_state_to_write["assigned"].add(move.id)
            elif not uom.is_zero(move.quantity):
                moves_state_to_write["partially_available"].add(move.id)
            elif (
                move.procure_method == "make_to_order" and not move.move_orig_ids
            ) or (
                move.move_orig_ids
                and any(
                    orig.product_uom_id.compare(orig.product_uom_qty, 0) > 0
                    and orig.state not in ("done", "cancel")
                    for orig in move.move_orig_ids
                )
            ):
                moves_state_to_write["waiting"].add(move.id)
            else:
                moves_state_to_write["confirmed"].add(move.id)
        for state, moves_ids in moves_state_to_write.items():
            changing = self.browse(moves_ids).filtered(
                lambda m, state=state: m.state != state
            )
            if changing:
                dbg.lifecycle.debug(
                    "_recompute_state: %s -> %s", dbg.rec(changing), state
                )
            changing.state = state

    def _prefetch_rollup_move_dests(self):
        self._prefetch_rollup_moves("move_dest_ids")

    def _prefetch_rollup_move_origs(self):
        self._prefetch_rollup_moves("move_orig_ids")

    def _prefetch_rollup_moves(self, target_field):
        seen = set(self.ids)
        self.fetch([target_field])
        next_ids = set(self[target_field].ids)
        depth = 0
        while not next_ids.issubset(seen):
            depth += 1
            seen |= next_ids
            to_visit = self.browse(next_ids)
            to_visit.fetch([target_field])
            next_ids = set(to_visit[target_field].ids)
        dbg.performance.debug(
            "_prefetch_rollup_moves(%s) from %d moves: %d seen in %d rounds",
            target_field,
            len(self),
            len(seen),
            depth,
        )

    def _rollup_move_dest_ids(self, seen=False) -> OrderedSet[int]:
        return self._rollup_move_ids(origin=False, seen=seen)

    def _rollup_move_orig_ids(self, seen=False) -> OrderedSet[int]:
        return self._rollup_move_ids(seen=seen)

    def _rollup_move_ids(self, origin=True, seen=False) -> OrderedSet[int]:
        target_field = "move_orig_ids" if origin else "move_dest_ids"
        if not seen:
            seen = OrderedSet()
        frontier = self
        depth = 0
        while frontier:
            unseen = OrderedSet(frontier.ids) - seen
            if not unseen:
                break
            depth += 1
            seen.update(unseen)
            frontier = frontier.browse(unseen)[target_field]
        dbg.performance.debug(
            "_rollup_move_ids(%s) from %d moves: %d seen, depth %d",
            target_field,
            len(self),
            len(seen),
            depth,
        )
        return seen

    def _sync_warehouse_from_locations(self):
        wh_by_moves = defaultdict(self.env["stock.move"].browse)
        for move in self:
            move_warehouse = (
                move.location_id.warehouse_id or move.location_dest_id.warehouse_id
            )
            if move_warehouse == move.warehouse_id:
                continue
            wh_by_moves[move_warehouse] |= move
        for warehouse, moves in wh_by_moves.items():
            dbg.logic.debug(
                "_sync_warehouse_from_locations: %s -> warehouse %s",
                dbg.rec(moves),
                warehouse.id,
            )
            moves.warehouse_id = warehouse.id

    def _get_visible_quantity(self):
        self.check_singleton()
        return self.quantity

    def _check_write_vals(self, vals):
        if "quantity" in vals:
            if any(move.state == "cancel" for move in self):
                raise UserError(
                    _(
                        "You cannot change a cancelled stock move, create a new line instead.",
                    ),
                )
            if "lot_ids" in vals:
                vals = {"lot_ids": vals["lot_ids"], **vals}
        if (
            "product_uom_id" in vals
            and any(move.state == "done" for move in self)
            and not self.env.context.get("skip_uom_conversion")
        ):
            raise UserError(
                _(
                    "You cannot change the UoM for a stock move that has been set to 'Done'.",
                ),
            )
        return vals

    def _is_consuming(self):
        self.check_singleton()
        from_wh = self.location_id.warehouse_id
        to_wh = self.location_dest_id.warehouse_id
        return self.picking_type_id.code in ("internal", "outgoing") or (
            from_wh and to_wh and from_wh != to_wh
        )

    def _is_incoming(self):
        self.check_singleton()
        return self.location_id.usage in ("customer", "supplier") or (
            self.location_id.usage == "transit" and not self.location_id.company_id
        )

    def _is_outgoing(self):
        self.check_singleton()
        return self.location_dest_id.usage in ("customer", "supplier") or (
            self.location_dest_id.usage == "transit"
            and not self.location_dest_id.company_id
        )

    def _is_assignment_required(self):
        self.check_singleton()
        return bool(not self.picking_id and self.picking_type_id)
