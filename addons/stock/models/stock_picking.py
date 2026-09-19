from collections import defaultdict

from odoo import api, fields, models
from odoo.db.schema import column_exists
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools.translate import _

from ..tools import debug_log as dbg
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES

DONE_CANCEL_STATES = frozenset(("done", "cancel"))
DRAFT_DONE_CANCEL_STATES = DONE_CANCEL_STATES | {"draft"}
OPEN_PICKING_STATES = frozenset(("waiting", "confirmed", "assigned"))
UNRESERVED_MOVE_STATES = frozenset(("waiting", "confirmed", "partially_available"))
FORECAST_PICKING_CODES = frozenset(("outgoing", "internal"))
INBOUND_PICKING_CODES = frozenset(("incoming", "internal"))


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = [
        "mixin.mail.thread",
        "mixin.mail.activity",
        "mixin.stock.activity",
        "mixin.stock.consignment",
        "mixin.date.category",
    ]
    _description = "Transfer"
    _order = "priority desc, date_planned asc, id desc"
    _date_category_field = "date_planned"

    name = fields.Char(
        string="Reference",
        default="/",
        index="trigram",
        copy=False,
        readonly=True,
    )
    origin = fields.Char(
        string="Source Document",
        index="trigram",
        help="Reference of the document",
    )
    note = fields.Html(string="Notes")
    backorder_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Back Order of",
        index="btree_not_null",
        copy=False,
        readonly=True,
        check_company=True,
        help="If this shipment was split, then this field links to the shipment which contains the already processed part.",
    )
    backorder_ids = fields.One2many(
        comodel_name="stock.picking",
        inverse_name="backorder_id",
        string="Back Orders",
    )
    return_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Return of",
        index="btree_not_null",
        copy=False,
        readonly=True,
        check_company=True,
        help="If this picking was created as a return of another picking, this field links to the original picking.",
    )
    return_ids = fields.One2many(
        comodel_name="stock.picking",
        inverse_name="return_id",
        string="Returns",
    )
    return_count = fields.Count(
        count_of="return_ids",
        string="# Returns",
        compute_sudo=False,
    )

    move_type = fields.Selection(
        selection=[
            ("direct", "As soon as possible"),
            ("one", "When all products are ready"),
        ],
        string="Shipping Policy",
        compute="_compute_move_type",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        help="It specifies goods to be deliver partially or all at once",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("waiting", "Waiting Another Operation"),
            ("confirmed", "Waiting"),
            ("assigned", "Ready"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        compute="_compute_state",
        store=True,
        index=True,
        copy=False,
        readonly=True,
        tracking=True,
        help=" * Draft: The transfer is not confirmed yet. Reservation doesn't apply.\n"
        " * Waiting another operation: This transfer is waiting for another operation before being ready.\n"
        ' * Waiting: The transfer is waiting for the availability of some products.\n(a) The shipping policy is "As soon as possible": no product could be reserved.\n(b) The shipping policy is "When all products are ready": not all the products could be reserved.\n'
        ' * Ready: The transfer is ready to be processed.\n(a) The shipping policy is "As soon as possible": at least one product has been reserved.\n(b) The shipping policy is "When all products are ready": all product have been reserved.\n'
        " * Done: The transfer has been processed.\n"
        " * Cancelled: The transfer has been cancelled.",
    )
    reference_ids = fields.Many2many(
        comodel_name="stock.reference",
        related="move_ids.reference_ids",
        string="References",
        readonly=True,
    )
    priority = fields.Selection(
        selection=PROCUREMENT_PRIORITIES,
        default="0",
        help="Products will be reserved first for the transfers with the highest priorities.",
    )
    date_planned = fields.Datetime(
        string="Scheduled Date",
        compute="_compute_date_planned",
        inverse="_inverse_date_planned",
        store=True,
        index=True,
        tracking=True,
        help="Scheduled time for the first part of the shipment to be processed. Setting manually a value here would set it as expected date for all the stock moves.",
    )
    date_deadline = fields.Datetime(
        string="Deadline",
        compute="_compute_date_deadline",
        store=True,
        help="In case of outgoing flow, validate the transfer before this date to allow to deliver at promised date to the customer.\n\
        In case of incoming flow, validate the transfer before this date in order to have these products in stock at the date promised by the supplier",
    )
    has_deadline_issue = fields.Boolean(
        string="Is late",
        compute="_compute_has_deadline_issue",
        store=True,
        help="Is late or will be late depending on the deadline and scheduled date",
    )
    date_done = fields.Datetime(
        string="Date of Transfer",
        copy=False,
        help="Date at which the transfer was processed. Cancelling never sets it.",
    )
    date_delay_alert = fields.Datetime(
        string="Delay Alert Date",
        compute="_compute_date_delay_alert",
        store=True,
    )
    json_popover = fields.Char(
        string="JSON data for the popover widget",
        compute="_compute_json_popover",
    )
    location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Source Location",
        compute="_compute_location_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        check_company=True,
    )
    location_dest_id = fields.Many2one(
        comodel_name="stock.location",
        string="Destination Location",
        compute="_compute_location_dest_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        check_company=True,
    )
    move_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="picking_id",
        string="Stock Moves",
        copy=True,
    )
    has_scrap_move = fields.Boolean(
        string="Has Scrap Moves",
        compute="_compute_has_scrap_move",
    )
    picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Operation Type",
        default=lambda self: self._default_picking_type_id(),
        index=True,
        required=True,
        tracking=True,
    )
    warehouse_address_id = fields.Many2one(
        comodel_name="res.partner",
        related="picking_type_id.warehouse_id.partner_id",
    )
    picking_type_code = fields.Selection(
        related="picking_type_id.code",
        readonly=True,
    )

    batch_id = fields.Many2one(
        comodel_name="stock.picking.batch",
        string="Batch Transfer",
        index=True,
        copy=False,
        check_company=True,
        help="Batch associated to this transfer",
    )
    batch_sequence = fields.Integer(string="Sequence")
    picking_type_entire_packs = fields.Boolean(
        related="picking_type_id.show_entire_packs"
    )
    use_create_lots = fields.Boolean(related="picking_type_id.use_create_lots")
    use_existing_lots = fields.Boolean(related="picking_type_id.use_existing_lots")
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contact",
        index="btree_not_null",
        check_company=True,
    )
    company_id = fields.Many2one(  # noqa: E8529  UNIQUE (name, company_id) partial
        comodel_name="res.company",
        related="picking_type_id.company_id",
        string="Company",
        store=True,
        index=True,
        readonly=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        default=lambda self: self.env.user,
        copy=False,
        domain=lambda self: [
            ("all_group_ids", "in", self.env.ref("stock.group_stock_user").id),
        ],
        tracking=True,
    )
    move_line_ids = fields.One2many(
        comodel_name="stock.move.line",
        inverse_name="picking_id",
        string="Operations",
    )
    count_packages = fields.Integer(
        string="Packages Count",
        compute="_compute_count_packages",
    )
    package_history_ids = fields.Many2many(
        comodel_name="stock.package.history",
        string="Transferred Packages",
        copy=False,
    )
    show_check_availability = fields.Boolean(
        compute="_compute_show_check_availability",
        help='Technical field used to compute whether the button "Check Availability" should be displayed.',
    )
    show_allocation = fields.Boolean(
        compute="_compute_show_allocation",
        help='Technical Field used to decide whether the button "Allocation" should be displayed.',
    )
    owner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Assign Owner",
        index="btree_not_null",
        check_company=True,
        help="When validating the transfer, the products will be assigned to this owner.",
    )
    printed = fields.Boolean(copy=False)
    signature = fields.Image(
        attachment=True,
        copy=False,
    )
    is_signed = fields.Boolean(compute="_compute_is_signed")
    is_cancelled = fields.Boolean(
        string="Cancelled",
        copy=False,
        readonly=True,
        help="Records that this transfer was cancelled. Its moves express that "
        "while they exist; this is what answers once they are gone.",
    )
    is_locked = fields.Boolean(
        default=True,
        copy=False,
        help="When the picking is not done this allows changing the "
        "initial demand. When the picking is done this allows "
        "changing the done quantities.",
    )
    is_date_editable = fields.Boolean(
        string="Is Scheduled Date Editable",
        compute="_compute_is_date_editable",
    )

    weight_bulk = fields.Float(
        string="Bulk Weight",
        compute="_compute_weight_bulk",
        help="Total weight of products which are not in a package.",
    )
    shipping_weight = fields.Float(
        string="Weight for Shipping",
        digits="Stock Weight",
        compute="_compute_shipping_weight",
        store=True,
        readonly=False,
        help="Total weight of packages and products not in a package. "
        "Packages with no shipping weight specified will default to their products' total weight. "
        "This is the weight used to compute the cost of the shipping.",
    )
    shipping_volume = fields.Float(
        string="Volume for Shipping",
        compute="_compute_shipping_volume",
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        related="move_ids.product_id",
        string="Product",
        readonly=True,
    )
    lot_id = fields.Many2one(
        comodel_name="stock.lot",
        related="move_line_ids.lot_id",
        string="Lot/Serial Number",
        readonly=True,
    )
    show_lots_text = fields.Boolean(compute="_compute_show_lots_text")
    has_tracking = fields.Boolean(compute="_compute_has_tracking")
    products_availability = fields.Char(
        string="Product Availability",
        compute="_compute_availability_status",
        help="Latest product availability status of the picking",
    )
    products_availability_state = fields.Selection(
        selection=[
            ("available", "Available"),
            ("expected", "Expected"),
            ("late", "Late"),
        ],
        compute="_compute_availability_status",
        search="_search_products_availability_state",
    )

    picking_properties = fields.Properties(
        definition="picking_type_id.picking_properties_definition",
        string="Properties",
        copy=True,
    )
    show_next_pickings = fields.Boolean(compute="_compute_show_next_pickings")
    partner_country_id = fields.Many2one(
        comodel_name="res.country",
        related="partner_id.country_id",
    )
    picking_warning_text = fields.Text(
        string="Picking Instructions",
        compute="_compute_picking_warning_text",
        help="Internal instructions for the partner or its parent company as set by the user.",
    )

    _name_uniq = models.UniqueIndex(
        "(name, company_id) WHERE name IS NOT NULL AND company_id IS NOT NULL",
        "Reference must be unique per company!",
    )

    def _auto_init(self):
        fresh_column = not column_exists(self.env.cr, "stock_picking", "is_cancelled")
        res = super()._auto_init()
        if fresh_column:
            self.env.cr.execute(
                "UPDATE stock_picking SET is_cancelled = true WHERE state = 'cancel'"
            )
        return res

    @dbg.timed
    @api.model_create_multi
    def create(self, vals_list):
        dbg.lifecycle.debug(
            "stock.picking.create: %d vals, keys=%s",
            len(vals_list),
            dbg.vals_keys(vals_list),
        )
        defaults = self.default_get(["name", "picking_type_id"])
        default_name = defaults.get("name", "/")
        default_picking_type_id = defaults.get("picking_type_id")
        vals_list = [dict(vals) for vals in vals_list]
        type_ids = {
            vals.get("picking_type_id", default_picking_type_id) for vals in vals_list
        }
        type_ids.discard(False)
        self.env["stock.picking.type"].browse(type_ids).fetch(["sequence_id"])
        for vals in vals_list:
            picking_type_id = vals.get("picking_type_id", default_picking_type_id)
            if not picking_type_id or vals.get("name", "/") != "/":
                continue
            if len(vals_list) == 1 and default_name != "/":
                continue
            picking_type = self.env["stock.picking.type"].browse(picking_type_id)
            if picking_type.sequence_id:
                vals["name"] = picking_type.sequence_id.next_by_id()
                dbg.logic.debug(
                    "create: sequence %s of type %s named picking %s",
                    picking_type.sequence_id.id,
                    picking_type_id,
                    vals["name"],
                )

        date_planneds = [vals.pop("date_planned", False) for vals in vals_list]

        pickings = super().create(vals_list)
        dbg.lifecycle.debug("stock.picking.create: created %s", dbg.rec(pickings))

        ids_by_date_planned = defaultdict(list)
        for picking, date_planned in zip(pickings, date_planneds, strict=True):
            if date_planned:
                ids_by_date_planned[date_planned].append(picking.id)
        for date_planned, picking_ids in ids_by_date_planned.items():
            self.browse(picking_ids).with_context(mail_notrack=True).write(
                {"date_planned": date_planned},
            )
        pickings._autoconfirm_picking()

        return pickings

    @dbg.timed
    def write(self, vals):
        dbg.lifecycle.debug(
            "stock.picking.write on %s: keys=%s", dbg.rec(self), dbg.keys(vals)
        )
        pickings_changing_type = self.browse()
        if vals.get("picking_type_id"):
            picking_type = self.env["stock.picking.type"].browse(
                vals["picking_type_id"],
            )
            pickings_changing_type = self.filtered(
                lambda picking: picking.picking_type_id != picking_type,
            )
            if any(
                picking.state in DONE_CANCEL_STATES
                for picking in pickings_changing_type
            ):
                raise UserError(
                    _(
                        "Changing the operation type of this record is forbidden at this point.",
                    ),
                )
            if pickings_changing_type and picking_type.sequence_id:
                dbg.logic.debug(
                    "write: %s change type to %s, renaming from its sequence",
                    dbg.rec(pickings_changing_type),
                    picking_type.id,
                )
                for picking in pickings_changing_type:
                    picking.name = picking_type.sequence_id.next_by_id()

        locations_before = {}
        if not self._get_location_trigger_fields().isdisjoint(vals):
            locations_before = {
                picking.id: (picking.location_id, picking.location_dest_id)
                for picking in self
            }

        res = super().write(vals)

        self._propagate_locations_to_moves(locations_before)

        if vals.get("date_done"):
            self.filtered(lambda p: p.state == "done").move_ids.filtered(
                lambda move: (
                    move.state == "done" and move.location_dest_usage != "inventory"
                ),
            ).date = vals["date_done"]
        if vals.get("signature"):
            for picking in self:
                picking._attach_signed_delivery_slip()
        if vals.get("move_ids"):
            self._update_is_cancelled()
            self._autoconfirm_picking()

        return res

    def _get_location_trigger_fields(self):
        field_depends = self.env.registry.field_depends
        return frozenset(
            {"location_id", "location_dest_id"}
            | {
                dependency.split(".")[0]
                for name in ("location_id", "location_dest_id")
                for dependency in field_depends[self._fields[name]]
            },
        )

    def _propagate_locations_to_moves(self, locations_before):
        moves_by_location_vals = defaultdict(lambda: self.env["stock.move"])
        for picking in self:
            before = locations_before.get(picking.id)
            if before is None:
                continue
            location_vals = {}
            if picking.location_id != before[0]:
                location_vals["location_id"] = picking.location_id.id
            if picking.location_dest_id != before[1]:
                location_vals["location_dest_id"] = picking.location_dest_id.id
            if not location_vals:
                continue
            moves_by_location_vals[tuple(location_vals.items())] |= (
                picking.move_ids.filtered(
                    lambda move: (
                        move.state not in DONE_CANCEL_STATES
                        and move.location_dest_usage != "inventory"
                    ),
                )
            )
        for location_vals, moves in moves_by_location_vals.items():
            if moves:
                dbg.pipeline.debug(
                    "_propagate_locations_to_moves: %s <- %s",
                    dbg.rec(moves),
                    dict(location_vals),
                )
                moves.write(dict(location_vals))

    @dbg.timed
    def unlink(self):
        dbg.lifecycle.debug("stock.picking.unlink %s", dbg.rec(self))
        self.move_ids._action_cancel()
        self.with_context(
            prefetch_fields=False,
        ).move_ids.unlink()
        return super().unlink()

    def _default_picking_type_id(self):
        picking_type_code = self.env.context.get("restricted_picking_type_code")
        if not picking_type_code:
            return False
        picking_type = self.env["stock.picking.type"].search(
            [
                ("code", "=", picking_type_code),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )
        return picking_type.id

    @api.depends("move_ids.has_tracking")
    def _compute_has_tracking(self):
        for picking in self:
            picking.has_tracking = any(
                m.has_tracking != "none" for m in picking.move_ids
            )

    @api.depends("state", "is_locked")
    def _compute_is_date_editable(self):
        for picking in self:
            if picking.state in DONE_CANCEL_STATES:
                picking.is_date_editable = not picking.is_locked
            else:
                picking.is_date_editable = True

    @api.depends("picking_type_id")
    def _compute_move_type(self):
        # An editable default: `precompute` places it and the user owns it
        # afterwards. Every value is valid for every operation type, so there
        # is nothing for a later trigger to invalidate -- and `modified()`
        # fires on the key written, not on a change, so re-deriving here reset
        # a deliberately chosen shipping policy on a write of `picking_type_id`
        # that changed nothing. Measured: a picking set to "When all products
        # are ready" came back "As soon as possible" after
        # `write({"picking_type_id": <its own type>})`.
        for record in self:
            if not record.move_type:
                record.move_type = record.picking_type_id.move_type

    @api.depends("signature")
    def _compute_is_signed(self):
        for picking in self:
            picking.is_signed = bool(picking.signature)

    @api.depends(
        "picking_type_id.use_create_lots",
        "picking_type_id.use_existing_lots",
        "state",
    )
    @api.depends_context("uid")
    def _compute_show_lots_text(self):
        group_production_lot_enabled = self.env.user.has_group(
            "stock.group_production_lot",
        )
        for picking in self:
            picking.show_lots_text = bool(
                group_production_lot_enabled
                and picking.picking_type_id.use_create_lots
                and not picking.picking_type_id.use_existing_lots
                and picking.state != "done"
            )

    @api.depends(
        "move_type",
        "move_ids.state",
        "move_ids.picking_id",
        "move_ids.procure_method",
        "location_id",
        "location_id.usage",
        "is_cancelled",
    )
    @dbg.timed
    def _compute_state(self):
        real_pickings = self.filtered("id")
        move_ids_by_picking = defaultdict(list)
        if real_pickings:
            for move in self.env["stock.move"].search(
                [("picking_id", "in", real_pickings.ids)]
            ):
                move_ids_by_picking[move.picking_id.id].append(move.id)

        for picking in self:
            if picking.id:
                moves = self.env["stock.move"].browse(
                    move_ids_by_picking.get(picking.id, ()),
                )
            else:
                moves = picking.move_ids
            move_states = set(moves.mapped("state"))

            if not moves:
                picking.state = "cancel" if picking.is_cancelled else "draft"
            elif "draft" in move_states:
                picking.state = "draft"
            elif move_states == {"cancel"}:
                picking.state = "cancel"
            elif move_states <= DONE_CANCEL_STATES:
                done_moves = moves.filtered(lambda m: m.state == "done")
                cancel_moves = moves.filtered(lambda m: m.state == "cancel")
                all_done_are_scrapped = all(
                    m.location_dest_usage == "inventory" for m in done_moves
                )
                any_cancel_and_not_scrapped = any(
                    m.location_dest_usage != "inventory" for m in cancel_moves
                )
                if all_done_are_scrapped and any_cancel_and_not_scrapped:
                    picking.state = "cancel"
                else:
                    picking.state = "done"
            elif picking.location_id.is_reservation_bypass_required() and all(
                m.procure_method == "make_to_stock" for m in moves
            ):
                picking.state = "assigned"
            else:
                relevant_move_state = moves._get_relevant_state_among_moves()
                if relevant_move_state == "partially_available":
                    picking.state = "assigned"
                else:
                    picking.state = relevant_move_state
            dbg.logic.debug(
                "[picking:%s] _compute_state: move states %s -> %s",
                picking.id,
                move_states,
                picking.state,
            )

    @api.depends("move_ids.state", "move_ids.date", "move_type")
    def _compute_date_planned(self):
        for picking in self:
            picking.date_planned = picking._get_date_planned_from_moves()

    def _get_date_planned_from_moves(self):
        self.check_singleton()
        moves_dates = self.move_ids.filtered(
            lambda move: move.state not in DONE_CANCEL_STATES,
        ).mapped("date")
        fallback = self.date_planned or fields.Datetime.now()
        if self.move_type == "direct":
            return min(moves_dates, default=fallback)
        return max(moves_dates, default=fallback)

    @api.depends("move_ids.date_deadline", "move_ids.state", "move_type")
    def _compute_date_deadline(self):
        for picking in self:
            moves = picking.move_ids.filtered(
                lambda m: m.state != "cancel" and m.date_deadline
            )
            if picking.move_type == "direct":
                picking.date_deadline = min(
                    moves.mapped("date_deadline"),
                    default=False,
                )
            else:
                picking.date_deadline = max(
                    moves.mapped("date_deadline"),
                    default=False,
                )

    @api.depends(
        "picking_type_id",
        "picking_type_id.default_location_src_id",
        "partner_id",
        "partner_id.property_stock_supplier",
    )
    def _compute_location_id(self):
        for picking in self:
            if picking.location_id and (
                picking.state in DONE_CANCEL_STATES or picking.return_id
            ):
                continue
            if picking.picking_type_id:
                picking.location_id = picking._get_type_default_location_id()

    @api.depends(
        "picking_type_id",
        "picking_type_id.default_location_dest_id",
        "partner_id",
        "partner_id.property_stock_customer",
    )
    def _compute_location_dest_id(self):
        for picking in self:
            if picking.location_dest_id and (
                picking.state in DONE_CANCEL_STATES or picking.return_id
            ):
                continue
            if picking.picking_type_id:
                picking.location_dest_id = picking._get_type_default_location_dest_id()

    def _get_type_default_location_id(self):
        self.check_singleton()
        picking = self.with_company(self.company_id)
        location = picking.picking_type_id.default_location_src_id
        if location.usage == "supplier" and picking.partner_id:
            location = picking.partner_id.property_stock_supplier
        return location.id

    def _get_type_default_location_dest_id(self):
        self.check_singleton()
        picking = self.with_company(self.company_id)
        location = picking.picking_type_id.default_location_dest_id
        if location.usage == "customer" and picking.partner_id:
            location = picking.partner_id.property_stock_customer
        return location.id

    @api.depends(
        "partner_id.picking_warn_msg",
        "partner_id.parent_id.picking_warn_msg",
    )
    @api.depends_context("uid")
    def _compute_picking_warning_text(self):
        if not self.env.user.has_group("stock.group_warning_stock"):
            self.picking_warning_text = ""
            return
        for picking in self:
            text = ""
            if partner_msg := picking.partner_id.picking_warn_msg:
                text += partner_msg + "\n"
            if parent_msg := picking.partner_id.parent_id.picking_warn_msg:
                text += parent_msg + "\n"
            picking.picking_warning_text = text

    @api.depends("move_ids.location_dest_usage")
    def _compute_has_scrap_move(self):
        result = {
            picking
            for [picking] in self.env["stock.move"]._read_group(
                [
                    ("picking_id", "in", self.ids),
                    ("location_dest_usage", "=", "inventory"),
                ],
                ["picking_id"],
            )
        }
        for picking in self:
            picking.has_scrap_move = picking._origin in result

    def _inverse_date_planned(self):
        for picking in self:
            if picking.state == "cancel":
                raise UserError(
                    _("You cannot change the Scheduled Date on a cancelled transfer."),
                )
            if picking.state == "done":
                continue
            if picking.date_planned == picking._get_date_planned_from_moves():
                continue
            picking.move_ids.filtered(
                lambda move: move.state not in DONE_CANCEL_STATES,
            ).write({"date": picking.date_planned})

    @api.onchange("picking_type_id", "partner_id")
    def _onchange_picking_type(self):
        if self.picking_type_id and self.state == "draft":
            self = self.with_company(self.company_id)
            self.move_ids.filtered(
                lambda m: m.picking_type_id != self.picking_type_id,
            ).picking_type_id = self.picking_type_id
            self.move_ids.company_id = self.company_id

    @api.onchange("location_id")
    def _onchange_location_id(self):
        self.move_ids.location_id = self.location_id
        for move in self.move_ids.filtered(lambda m: m.move_orig_ids):
            for ml in move.move_line_ids:
                if not ml.location_id._is_descendant_of(self.location_id):
                    return {
                        "warning": {
                            "title": _("Warning: change source location"),
                            "message": _(
                                "Updating the location of this transfer will result in unreservation of the currently assigned items. "
                                "An attempt to reserve items at the new location will be made and the link with preceding transfers will be discarded.\n\n"
                                "To avoid this, please discard the source location change before saving.",
                            ),
                        },
                    }
        return None

    @dbg.timed
    def action_confirm(self):
        dbg.pipeline.debug("[picking:%s] action_confirm", dbg.names(self, "name"))
        self._check_company()
        self._update_is_cancelled()
        self.move_ids.filtered(lambda move: move.state == "draft")._action_confirm()

        to_schedule = self.move_ids.filtered(
            lambda move: move.state not in DRAFT_DONE_CANCEL_STATES,
        )
        dbg.pipeline.debug(
            "action_confirm -> _trigger_scheduler for %s", dbg.rec(to_schedule)
        )
        to_schedule._trigger_scheduler()
        return True

    @dbg.timed
    def action_assign(self):
        dbg.pipeline.debug("[picking:%s] action_assign", dbg.names(self, "name"))
        self.filtered(lambda picking: picking.state == "draft").action_confirm()
        moves = self.move_ids.filtered(
            lambda move: move.state not in DRAFT_DONE_CANCEL_STATES,
        ).sorted(
            key=lambda move: (
                -int(move.priority),
                not bool(move.date_deadline),
                move.date_deadline,
                move.date,
                move.id,
            ),
        )
        if not moves:
            raise UserError(_("Nothing to check the availability for."))
        dbg.pipeline.debug("action_assign -> _action_assign %s", dbg.rec(moves))
        moves._action_assign()
        return True

    @dbg.timed
    def action_cancel(self):
        dbg.pipeline.debug("[picking:%s] action_cancel", dbg.names(self, "name"))
        self.move_ids._action_cancel()
        self.write({"is_locked": True})
        moveless = self.filtered(lambda picking: not picking.move_ids)
        cancelled = (self - moveless).filtered(
            lambda picking: picking.state == "cancel",
        )
        dbg.lifecycle.debug(
            "action_cancel: is_cancelled on moveless %s, cancelled %s",
            dbg.rec(moveless),
            dbg.rec(cancelled),
        )
        (moveless | cancelled).is_cancelled = True
        return True

    @dbg.timed
    def _action_done(self):
        dbg.pipeline.debug(
            "[picking:%s] _action_done cancel_backorder=%s",
            dbg.names(self, "name"),
            self.env.context.get("cancel_backorder"),
        )
        self._check_company()

        todo_moves = self.move_ids.filtered(
            lambda move: move.state not in DONE_CANCEL_STATES,
        )
        dbg.pipeline.debug(
            "_action_done -> stock.move._action_done %s", dbg.rec(todo_moves)
        )
        for owner, pickings in self.filtered("owner_id").grouped("owner_id").items():
            owner_moves = todo_moves.filtered(
                lambda move, pickings=pickings: move.picking_id in pickings,
            )
            owner_moves.write({"restrict_partner_id": owner.id})
            owner_moves.move_line_ids.write({"owner_id": owner.id})
        todo_moves._action_done(
            cancel_backorder=self.env.context.get("cancel_backorder"),
        )
        self.filtered(lambda picking: picking.state == "done").write(
            {"date_done": fields.Datetime.now(), "priority": "0"},
        )

        done_incoming_moves = self.filtered(
            lambda p: p.picking_type_id.code in INBOUND_PICKING_CODES,
        ).move_ids.filtered(lambda m: m.state == "done")
        dbg.pipeline.debug(
            "_action_done -> _trigger_assign on incoming %s",
            dbg.rec(done_incoming_moves),
        )
        done_incoming_moves._trigger_assign()

        self._send_confirmation_email()
        return True

    def _send_confirmation_email(self):
        pickings_to_notify = self.filtered(
            lambda p: (
                p.company_id.stock_move_email_validation
                and p.company_id.stock_mail_confirmation_template_id
                and p.picking_type_id.code == "outgoing"
            ),
        )
        if not pickings_to_notify:
            return
        dbg.logic.debug("_send_confirmation_email to %s", dbg.rec(pickings_to_notify))
        subtype_id = self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_comment")
        for stock_pick in pickings_to_notify:
            delivery_template = (
                stock_pick.company_id.stock_mail_confirmation_template_id
            )
            stock_pick.with_context(force_send=True).message_post_with_source(
                delivery_template,
                email_layout_xmlid="mail.mail_notification_light",
                subtype_id=subtype_id,
            )

    def action_unreserve(self):
        dbg.pipeline.debug("[picking:%s] action_unreserve", dbg.names(self, "name"))
        self.move_ids._unreserve()
        return True

    @dbg.timed
    def button_validate(self):
        dbg.pipeline.debug(
            "[picking:%s] button_validate start, states %s",
            dbg.names(self, "name"),
            dbg.names(self, "state"),
        )
        self = self.filtered(lambda p: p.state not in DONE_CANCEL_STATES)
        draft_picking = self.filtered(lambda p: p.state == "draft")
        draft_picking.action_confirm()
        moves_by_quantity = defaultdict(lambda: self.env["stock.move"])
        for move in draft_picking.move_ids:
            if move.product_uom_id.is_zero(
                move.quantity
            ) and not move.product_uom_id.is_zero(
                move.product_uom_qty,
            ):
                moves_by_quantity[move.product_uom_qty] |= move
        for quantity, moves in moves_by_quantity.items():
            dbg.logic.debug(
                "button_validate: draft %s get quantity %s from demand",
                dbg.rec(moves),
                quantity,
            )
            moves.write({"quantity": quantity})

        if not self.env.context.get("skip_validation_check", False):
            self._check_before_validation()

        requested_ids = self.env.context.get("button_validate_picking_ids")
        validating = self.browse(requested_ids) & self if requested_ids else self
        self = self.with_context(
            button_validate_picking_ids=(validating or self).ids,
        )
        res = self._pre_action_done_hook()
        if res is not True:
            dbg.pipeline.debug(
                "button_validate: _pre_action_done_hook returned an action %s",
                res.get("res_model") if isinstance(res, dict) else res,
            )
            return res

        pickings_to_backorder, pickings_not_to_backorder = (
            self._split_backorder_pickings()
        )
        dbg.pipeline.debug(
            "button_validate: backorder %s, no backorder %s",
            dbg.rec(pickings_to_backorder),
            dbg.rec(pickings_not_to_backorder),
        )
        if pickings_not_to_backorder:
            pickings_not_to_backorder.with_context(cancel_backorder=True)._action_done()
        if pickings_to_backorder:
            pickings_to_backorder.with_context(cancel_backorder=False)._action_done()
        report_actions = self._prepare_actions_autoprint()
        another_action = self._get_reception_report_action()
        dbg.logic.debug(
            "button_validate: %d autoprint reports, reception action %s",
            len(report_actions or ()),
            bool(another_action),
        )
        if another_action and not report_actions:
            return another_action
        if report_actions:
            return {
                "type": "ir.actions.client",
                "tag": "do_multi_print",
                "params": {
                    "reports": report_actions,
                    "anotherAction": another_action,
                },
            }
        return True

    def action_split_transfer(self):
        self.check_singleton()
        if all(m.product_uom_id.is_zero(m.quantity) for m in self.move_ids):
            raise UserError(
                _(
                    "%s: Nothing to split. Fill the quantities you want in a new transfer in the done quantities",
                    self.display_name,
                ),
            )
        demand_comparisons = [
            m.product_uom_id.compare(m.quantity, m.product_uom_qty)
            for m in self.move_ids
        ]
        if all(comparison == 0 for comparison in demand_comparisons):
            raise UserError(
                _(
                    "%s: Nothing to split, all demand is done. For split you need at least one line not fully fulfilled",
                    self.display_name,
                ),
            )
        if any(comparison > 0 for comparison in demand_comparisons):
            raise UserError(
                _(
                    "%s: Can't split: quantities done can't be above demand",
                    self.display_name,
                ),
            )

        open_moves = self.move_ids.filtered(
            lambda m: m.state not in DONE_CANCEL_STATES,
        )
        moves = open_moves.filtered(
            lambda m: not m.product_uom_id.is_zero(m.quantity),
        )
        dbg.pipeline.debug(
            "[picking:%s] action_split_transfer: splitting %s of open %s",
            self.name,
            dbg.rec(moves),
            dbg.rec(open_moves),
        )
        backorder_moves = moves._create_backorder()
        backorder_moves += open_moves.filtered(
            lambda m: m.product_uom_id.is_zero(m.quantity),
        )
        self._create_backorder(backorder_moves=backorder_moves)

    def _get_pickings_to_autopick(self):
        to_autopick = self.browse()
        for picking in self:
            has_quantity = False
            has_pick = False
            for move in picking.move_ids:
                if move.quantity:
                    has_quantity = True
                if move.location_dest_usage == "inventory":
                    continue
                if move.picked:
                    has_pick = True
                if has_quantity and has_pick:
                    break
            if has_quantity and not has_pick:
                to_autopick |= picking
        dbg.logic.debug("_get_pickings_to_autopick: %s", dbg.rec(to_autopick))
        return to_autopick

    def _pre_action_done_hook(self):
        self._get_pickings_to_autopick().move_ids.picked = True
        if not self.env.context.get("skip_backorder"):
            pickings_to_backorder = self._get_pickings_to_backorder()
            if pickings_to_backorder:
                dbg.pipeline.debug(
                    "_pre_action_done_hook: backorder confirmation for %s",
                    dbg.rec(pickings_to_backorder),
                )
                return pickings_to_backorder._prepare_action_backorder_confirmation(
                    show_transfers=self._is_transfer_display_required(),
                )
        return True

    def action_toggle_is_locked(self):
        self.check_singleton()
        self.is_locked = not self.is_locked
        return True

    def button_scrap(self):
        self.check_singleton()
        view = self.env.ref("stock.view_stock_scrap_form2")
        products = self.env["product.product"]
        for move in self.move_ids:
            if (
                move.state not in ("draft", "cancel")
                and move.product_id.type == "consu"
            ):
                products |= move.product_id
        return {
            "name": _("Scrap Products"),
            "view_mode": "form",
            "res_model": "stock.scrap",
            "view_id": view.id,
            "views": [(view.id, "form")],
            "type": "ir.actions.act_window",
            "context": {
                "default_picking_id": self.id,
                "product_ids": products.ids,
                "default_company_id": self.company_id.id,
            },
            "target": "new",
        }

    def _add_reference(self, reference):
        self.check_singleton()
        self.move_ids.reference_ids = [
            Command.link(stock_reference.id) for stock_reference in reference
        ]

    def _autoconfirm_picking(self):
        open_pickings = self.filtered(
            lambda picking: picking.state not in DONE_CANCEL_STATES,
        )
        pickings_with_additional_moves = open_pickings.filtered(
            lambda picking: any(move.additional for move in picking.move_ids),
        )
        if pickings_with_additional_moves:
            dbg.pipeline.debug(
                "_autoconfirm_picking: additional moves on %s",
                dbg.rec(pickings_with_additional_moves),
            )
            pickings_with_additional_moves.action_confirm()
        to_confirm = open_pickings.move_ids.filtered(
            lambda m: m.state == "draft" and m.quantity,
        )
        if to_confirm:
            dbg.pipeline.debug(
                "_autoconfirm_picking: draft moves with quantity %s",
                dbg.rec(to_confirm),
            )
        to_confirm._action_confirm()

    def _update_is_cancelled(self):
        self.filtered(
            lambda picking: (
                picking.is_cancelled
                and any(move.state != "cancel" for move in picking.move_ids)
            ),
        ).is_cancelled = False

    def _get_lot_move_lines_to_check(self):
        autopicked = self._get_pickings_to_autopick()
        return self.move_line_ids.filtered(
            lambda ml: (
                ml.product_id
                and ml.product_id.tracking != "none"
                and (ml.picked or ml.picking_id in autopicked)
                and ml.product_uom_id.compare(ml.quantity, 0)
            ),
        )

    @api.model
    def _get_impacted_pickings(self, moves):
        impacted_pickings = self.env["stock.picking"]
        explored_moves = self.env["stock.move"]
        frontier = moves
        while frontier:
            new_moves = frontier - explored_moves
            impacted_pickings |= new_moves.picking_id
            explored_moves |= new_moves
            frontier = new_moves.move_dest_ids - explored_moves
        dbg.performance.debug(
            "_get_impacted_pickings: %d moves explored from %d, %d pickings",
            len(explored_moves),
            len(moves),
            len(impacted_pickings),
        )
        return impacted_pickings

    def _get_consignment_pickings(self):
        return self

    def _remove_reference(self, reference):
        self.check_singleton()
        self.move_ids.reference_ids = [
            Command.unlink(stock_reference.id) for stock_reference in reference
        ]

    def _can_return(self):
        self.check_singleton()
        return self.state == "done"

    def _is_to_external_location(self):
        self.check_singleton()
        return self.picking_type_code == "outgoing"

    def _check_before_validation(self):
        pickings_without_lots = self.browse()
        products_without_lots = self.env["product.product"]
        pickings_without_moves = self.filtered(
            lambda p: not p.move_ids and not p.move_line_ids,
        )

        pickings_without_quantities = self.env["stock.picking"]
        for picking in self:
            has_pick = any(
                move.picked and move.state not in DONE_CANCEL_STATES
                for move in picking.move_ids
            )
            if all(
                move.product_uom_id.is_zero(move.quantity)
                for move in picking.move_ids.filtered(
                    lambda m, has_pick=has_pick: (
                        m.state not in DONE_CANCEL_STATES and (not has_pick or m.picked)
                    ),
                )
            ):
                pickings_without_quantities |= picking

        pickings_using_lots = self.filtered(
            lambda p: (
                p.picking_type_id.use_create_lots or p.picking_type_id.use_existing_lots
            ),
        )
        if pickings_using_lots:
            lines_to_check = pickings_using_lots._get_lot_move_lines_to_check()
            for line in lines_to_check:
                if not line.lot_name and not line.lot_id:
                    pickings_without_lots |= line.picking_id
                    products_without_lots |= line.product_id

        if not self._is_transfer_display_required():
            if pickings_without_moves:
                raise UserError(
                    _(
                        "You can’t validate an empty transfer. Please add some products to move before proceeding.",
                    ),
                )
            if pickings_without_quantities:
                raise UserError(self._get_without_quantities_error_message())
            if pickings_without_lots:
                raise UserError(
                    _(
                        "You need to supply a Lot/Serial number for products %s.",
                        ", ".join(products_without_lots.mapped("display_name")),
                    ),
                )
        else:
            message = ""
            if pickings_without_moves:
                message += _(
                    "Transfers %s: Please add some items to move.",
                    ", ".join(pickings_without_moves.mapped("name")),
                )
            if zero_quantity_pickings := pickings_without_quantities.filtered(
                lambda p: p.state != "draft",
            ):
                message += _(
                    "\n\nTransfers %s: You cannot validate a transfer without any quantities set. Set some quantities before proceeding.",
                    ", ".join(zero_quantity_pickings.mapped("name")),
                )
            if pickings_without_lots:
                message += _(
                    "\n\nTransfers %(transfer_list)s: You need to supply a Lot/Serial number for products %(product_list)s.",
                    transfer_list=", ".join(pickings_without_lots.mapped("name")),
                    product_list=", ".join(
                        products_without_lots.mapped("display_name"),
                    ),
                )
            if message:
                raise UserError(message.lstrip())
