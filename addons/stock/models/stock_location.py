import calendar
import itertools
import logging
from collections import defaultdict
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.api import MODULE_UNINSTALL_FLAG
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain

from ..const import (
    BLOCK_TYPE_SELECTION,
    BLOCKABLE_USAGES,
    CONTEXT_ACTIVE_CASCADE,
    INCOMING_BLOCK_TYPES,
    INTERNAL_CONTEXT_FLAG,
    OUTGOING_BLOCK_TYPES,
    is_internal_flag,
)
from ..tools import debug_log as dbg

_logger = logging.getLogger(__name__)

MAX_CYCLIC_INVENTORY_DAYS = 36500

STOCKED_USAGES = ("internal", "transit")

TREE_FIELDS = frozenset({"active", "location_id", "usage"})

GROUP_FORCE_BLOCK_IN = "stock.group_force_blocked_location_in"
GROUP_FORCE_BLOCK_OUT = "stock.group_force_blocked_location_out"
GROUP_OVERRIDE_HARD_BLOCK = "stock.group_override_hard_block"
GROUP_STOCK_USER = "stock.group_stock_user"


def merge_block_types(*block_types):
    given = {block_type or "none" for block_type in block_types}
    if "hard" in given:
        return "hard"
    blocks_in = bool(given.intersection(INCOMING_BLOCK_TYPES))
    blocks_out = bool(given.intersection(OUTGOING_BLOCK_TYPES))
    if blocks_in and blocks_out:
        return "soft_both"
    if blocks_in:
        return "soft_in"
    if blocks_out:
        return "soft_out"
    return "none"


class StockLocation(models.Model):
    _name = "stock.location"
    _inherit = ["mixin.mail.thread", "mixin.mail.activity"]
    _description = "Inventory Locations"
    _parent_name = "location_id"
    _parent_store = True
    _order = "complete_name, id"
    _rec_names_search = ["complete_name", "barcode"]
    _check_company_auto = True

    name = fields.Char(
        string="Location Name",
        required=True,
    )
    complete_name = fields.Char(
        string="Full Location Name",
        compute="_compute_complete_name",
        recursive=True,
        store=True,
    )
    active = fields.Boolean(
        default=True,
        help="By unchecking the active field, you may hide a location without deleting it.",
    )
    usage = fields.Selection(
        selection=[
            ("supplier", "Vendor"),
            ("view", "Virtual"),
            ("internal", "Internal"),
            ("customer", "Customer"),
            ("inventory", "Inventory Loss"),
            ("production", "Production"),
            ("transit", "Transit"),
        ],
        string="Location Type",
        default="internal",
        index=True,
        required=True,
        help="* Vendor: Virtual location representing the source location for products coming from your vendors"
        "\n* Virtual: Virtual location used to create a hierarchical structure for your warehouse by aggregating its child locations. Can't directly contain products"
        "\n* Internal: Physical locations inside your warehouses,"
        "\n* Customer: Virtual location representing the destination location for products sent to your customers"
        "\n* Inventory Loss: Virtual location serving as the counterpart for inventory operations done to correct stock levels (Physical inventories)"
        "\n* Production: Virtual counterpart location for production operations. I.e. This location consumes components and produces finished products"
        "\n* Transit: Counterpart location that should be used for inter-company or inter-warehouses operations",
    )
    location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Parent Location",
        index=True,
        check_company=True,
        help="The parent location that includes this location. Example : The 'Dispatch Zone' is the 'Gate 1' parent location.",
    )
    child_ids = fields.One2many(
        comodel_name="stock.location",
        inverse_name="location_id",
        string="Contains",
    )
    child_internal_location_ids = fields.Many2many(
        comodel_name="stock.location",
        string="Internal locations among descendants",
        compute="_compute_child_internal_location_ids",
        help="This location (if it's internal) and all its descendants filtered by type=Internal.",
    )
    parent_path = fields.Char(index=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
        help="Let this field empty if this location is shared between companies",
    )
    replenish_location = fields.Boolean(
        string="Replenishments",
        compute="_compute_replenish_location",
        store=True,
        copy=False,
        readonly=False,
        help="Trigger replenishment suggestions for this location when required",
    )
    removal_strategy_id = fields.Many2one(
        comodel_name="product.removal",
        help="Defines the default method used for suggesting the exact location (shelf) "
        "where to take the products from, which lot etc. for this location. "
        "This method can be enforced at the product category level, "
        "and a fallback is made on the parent locations if none is set here.\n\n"
        "FIFO: products/lots that were stocked first will be moved out first.\n"
        "LIFO: products/lots that were stocked last will be moved out first.\n"
        "Closest Location: products/lots closest to the target location will be moved out first.\n"
        "Least Packages: products/lots that were stocked in package with least amount of qty will be moved out first.\n"
        "FEFO: products/lots with the closest removal date will be moved out first "
        '(the availability of this method depends on the "Expiration Dates" setting).',
    )
    putaway_rule_ids = fields.One2many(
        comodel_name="stock.putaway.rule",
        inverse_name="location_in_id",
        string="Putaway Rules",
    )
    barcode = fields.Char(copy=False)
    quant_ids = fields.One2many(
        comodel_name="stock.quant",
        inverse_name="location_id",
    )
    cyclic_inventory_frequency = fields.Integer(
        string="Inventory Frequency",
        default=0,
        help=" When different than 0, inventory count date for products stored at this location will be automatically set at the defined frequency.",
    )
    last_inventory_date = fields.Date(
        string="Last Inventory",
        readonly=True,
        help="Date of the last inventory at this location.",
    )
    next_inventory_date = fields.Date(
        string="Next Expected",
        compute="_compute_next_inventory_date",
        store=True,
        help="Date for next planned inventory based on cyclic schedule.",
    )
    warehouse_view_ids = fields.One2many(
        comodel_name="stock.warehouse",
        inverse_name="view_location_id",
        readonly=True,
    )
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        compute="_compute_warehouse_id",
        recursive=True,
        store=True,
    )
    storage_category_id = fields.Many2one(
        comodel_name="stock.storage.category",
        index="btree_not_null",
        check_company=True,
    )
    outgoing_move_line_ids = fields.One2many(
        comodel_name="stock.move.line",
        inverse_name="location_id",
    )
    incoming_move_line_ids = fields.One2many(
        comodel_name="stock.move.line",
        inverse_name="location_dest_id",
    )
    net_weight = fields.Float(compute="_compute_weight")
    forecast_weight = fields.Float(
        string="Forecasted Weight",
        compute="_compute_weight",
    )
    is_empty = fields.Boolean(
        compute="_compute_is_empty",
        search="_search_is_empty",
    )
    block_type = fields.Selection(
        selection=BLOCK_TYPE_SELECTION,
        default="none",
        required=True,
        tracking=True,
        help="Blocking Mode:\n\n"
        "\u2022 No Blocking: Normal warehouse operations\n\n"
        "\u2022 Soft Block Incoming: Prevents NEW incoming stock but allows:\n"
        "  - Removing stock (outgoing operations)\n"
        "  - System operations (inventory adjustments, sudo)\n"
        "  Use for: Maintenance, location at capacity\n\n"
        "\u2022 Soft Block Outgoing: Prevents NEW outgoing reservations but allows:\n"
        "  - Completing already-reserved pickings\n"
        "  - Receiving new stock (incoming operations)\n"
        "  - System operations (inventory adjustments, sudo)\n"
        "  Use for: Quarantine, quality hold, reserved inventory\n\n"
        "\u2022 Soft Block Both: Combines incoming and outgoing soft blocks\n"
        "  Use for: Scheduled maintenance, location reorganization\n\n"
        "\u2022 Hard Block: Freezes ALL operations including:\n"
        "  - Prevents completing existing reservations\n"
        "  - Prevents all stock movements\n"
        "  - Requires the Hard Block override group to lift, to archive the\n"
        "    location, or to move it out from under the block\n"
        "  Use for: Inventory counts, audits, legal holds, emergency quarantine",
    )
    effective_block_type = fields.Selection(
        selection=BLOCK_TYPE_SELECTION,
        string="Effective Blocking",
        compute="_compute_effective_block_type",
        recursive=True,
        store=True,
        readonly=True,
        help="The blocking actually in force here: this location's own mode merged "
        "with every ancestor's. Stored so the reservation and visibility filters "
        "are a single indexed join instead of a subtree walk per query.",
    )
    block_reason = fields.Text(
        string="Blocking Reason",
        tracking=True,
        help="Detailed explanation for why this location is blocked",
    )
    blocked_date = fields.Datetime(
        string="Blocked Since",
        copy=False,
        readonly=True,
        help="Date and time when blocking was applied",
    )
    blocked_by_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Blocked By",
        copy=False,
        readonly=True,
        help="User who applied the block",
    )
    reserved_qty_when_blocked = fields.Float(
        digits="Product Unit",
        copy=False,
        readonly=True,
        help="Reserved quantity in this location and its children at the time "
        "blocking was applied, summed across products.\n"
        "Comparable only where the location holds a single unit of measure; the "
        "chatter entry posted at blocking time carries the per-unit breakdown.",
    )

    _barcode_company_unique_idx = models.UniqueIndex(
        "(barcode, COALESCE(company_id, 0)) WHERE barcode IS NOT NULL",
        "The barcode for a location must be unique per company!",
    )
    _parent_path_id_idx = models.Index("(parent_path, id)")
    _block_type_idx = models.Index("(block_type) WHERE block_type != 'none'")
    _effective_block_type_idx = models.Index(
        "(effective_block_type) WHERE effective_block_type != 'none'"
    )

    _inventory_freq_bounded = models.Constraint(
        f"check(cyclic_inventory_frequency between 0 and {MAX_CYCLIC_INVENTORY_DAYS})",
        "The inventory frequency (days) for a location must be between 0 and "
        f"{MAX_CYCLIC_INVENTORY_DAYS}.",
    )

    @api.constrains("replenish_location", "location_id", "usage")
    def _check_replenish_location(self):
        replenish_locations = self.filtered("replenish_location")
        if not replenish_locations:
            return
        ancestor_ids = replenish_locations._get_ancestor_ids(include_self=True)
        others = self.with_context(active_test=False).search(
            Domain("replenish_location", "=", True)
            & Domain("id", "not in", replenish_locations.ids)
            & (
                Domain("id", "in", list(ancestor_ids))
                | Domain("id", "child_of", replenish_locations.ids)
            ),
        )
        for location in replenish_locations:
            for other in others:
                if location._is_descendant_of(other) or other._is_descendant_of(
                    location
                ):
                    raise ValidationError(
                        _(
                            "Another parent/sub replenish location %s exists, if you wish to change it, uncheck it first",
                            other.display_name,
                        ),
                    )

    @api.constrains("block_type", "usage")
    def _check_block_type_usage(self):
        for location in self:
            if location.block_type != "none" and location.usage not in BLOCKABLE_USAGES:
                raise ValidationError(
                    self.env._(
                        "%(location)s is a %(usage)s location. Only internal "
                        "locations can be blocked.",
                        location=location.display_name,
                        usage=location._get_usage_label(),
                    ),
                )

    @api.constrains("usage")
    def _check_inventory_loss_location(self):
        inventory_locations = self.filtered(lambda l: l.usage == "inventory")
        if not inventory_locations:
            return
        if self.env["stock.picking.type"].search_count(
            [
                ("code", "=", "mrp_operation"),
                ("default_location_dest_id", "in", inventory_locations.ids),
            ],
            limit=1,
        ):
            raise ValidationError(
                _(
                    "You cannot set a location's type to Inventory Loss while it is the destination location of a manufacturing operation type."
                ),
            )

    def _check_company_not_changed(self, company_id):
        if any(location.company_id.id != company_id for location in self):
            raise UserError(
                _(
                    "Changing the company of this record is forbidden at this point, you should rather archive it and create a new one."
                ),
            )

    @api.model
    def _check_cyclic_inventory_frequency(self, frequency):
        if frequency is None or 0 <= frequency <= MAX_CYCLIC_INVENTORY_DAYS:
            return
        raise ValidationError(
            _(
                "The inventory frequency must be between 0 and %(maximum)s days.",
                maximum=MAX_CYCLIC_INVENTORY_DAYS,
            ),
        )

    def _check_usage_convertible(self, usage):
        modified_locations = self.filtered(lambda location: location.usage != usage)
        if not modified_locations:
            return
        domain = Domain("location_id", "in", modified_locations.ids)
        if usage != "view":
            # A bare `> 0` would false-positive on dust left by a raw SQL
            # writer bypassing the ORM's rounding (see the analogous epsilon
            # window in `_unlink_zero_quants`).
            precision_digits = max(
                6, self.env.ref("uom.decimal_product_uom").sudo().digits * 2
            )
            epsilon = 5 * 10 ** -(precision_digits + 1)
            domain &= Domain("quantity", ">", epsilon) | Domain(
                "quantity", "<", -epsilon
            )
        blocking = self.env["stock.quant"].search(domain, limit=1).location_id
        if not blocking:
            return
        if usage == "view":
            raise UserError(
                _(
                    "A view location groups its children and cannot hold "
                    "products; %s still does.",
                    blocking.display_name,
                ),
            )
        raise UserError(
            _(
                "%s still holds stock, so its type cannot be changed.",
                blocking.display_name,
            ),
        )

    @dbg.timed
    @api.model_create_multi
    def create(self, vals_list):
        dbg.lifecycle.debug(
            "stock.location.create: %d vals, keys=%s",
            len(vals_list),
            dbg.vals_keys(vals_list),
        )
        for vals in vals_list:
            self._check_cyclic_inventory_frequency(
                vals.get("cyclic_inventory_frequency")
            )
        locations = super().create(vals_list)
        dbg.lifecycle.debug("stock.location.create: created %s", dbg.rec(locations))
        locations._invalidate_location_tree()
        locations.filtered(
            lambda location: location.block_type != "none",
        )._update_block_metadata()
        return locations

    @dbg.timed
    def write(self, vals):
        dbg.lifecycle.debug(
            "stock.location.write on %s: keys=%s", dbg.rec(self), dbg.keys(vals)
        )
        self._check_block_governance_before_write(vals)
        transitioning = self._filtered_block_type_transitioning(vals)

        if "cyclic_inventory_frequency" in vals:
            self._check_cyclic_inventory_frequency(vals["cyclic_inventory_frequency"])
        if "company_id" in vals:
            self._check_company_not_changed(vals["company_id"])
        if "usage" in vals:
            self._check_usage_convertible(vals["usage"])
        if "active" in vals:
            self._propagate_active(vals["active"])

        res = super().write(vals)
        if not TREE_FIELDS.isdisjoint(vals):
            dbg.logic.debug("write: tree fields touched, invalidating location tree")
            self._invalidate_location_tree()
        if transitioning:
            dbg.lifecycle.debug(
                "write: block_type -> %s on %s",
                vals["block_type"],
                dbg.rec(transitioning),
            )
            if vals["block_type"] == "none":
                transitioning._remove_block_metadata()
            else:
                transitioning._update_block_metadata()
        return res

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if "name" not in default:
            for location, vals in zip(self, vals_list, strict=True):
                vals["name"] = _("%s (copy)", location.name)
        return vals_list

    @dbg.timed
    def unlink(self):
        subtree = self.with_context(active_test=False).search(
            [("id", "child_of", self.ids)],
        )
        dbg.lifecycle.debug(
            "stock.location.unlink %s (subtree %s)", dbg.rec(self), dbg.rec(subtree)
        )
        if not self.env.context.get(MODULE_UNINSTALL_FLAG):
            subtree._check_block_governance_before_unlink()
        descendants = subtree - self
        if (
            descendants
            and not self.env.context.get("stock_unlink_subtree")
            and not self.env.context.get(MODULE_UNINSTALL_FLAG)
        ):
            blocking, held = next(
                (
                    (location, children)
                    for location in self
                    if (
                        children := descendants.filtered(
                            lambda child, parent=location: child._is_child_of(parent),
                        )
                    )
                ),
                (self.browse(), self.browse()),
            )
            raise UserError(  # noqa: E8506 - uninstall already excluded above
                _(
                    "You cannot delete location %(location)s: it still contains "
                    "%(count)s sub-location(s) (archived ones included). Delete or "
                    "move them first.",
                    location=blocking.display_name,
                    count=len(held),
                ),
            )
        res = super(StockLocation, subtree).unlink()
        self._invalidate_location_tree()
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_data(self):
        inter_company_location = self.env.ref("stock.stock_location_inter_company")
        if inter_company_location in self:
            raise ValidationError(
                _(
                    "The %s location is required by the Inventory app and cannot be deleted, but you can archive it.",
                    inter_company_location.name,
                ),
            )

    @api.model
    def name_create(self, name):
        if name:
            name_split = name.split("/")
            parent_location = self.search(
                [
                    ("complete_name", "=", "/".join(name_split[:-1])),
                    ("company_id", "in", [False, self.env.company.id]),
                ],
                limit=1,
            )
            new_location = self.create(
                {
                    "name": name_split[-1],
                    "location_id": parent_location.id if parent_location else False,
                },
            )
            return new_location.id, new_location.display_name
        return super().name_create(name)

    @api.depends("complete_name", "name", "location_id.complete_name", "usage")
    @api.depends_context("formatted_display_name")
    def _compute_display_name(self):
        formatted = self.env.context.get("formatted_display_name")
        for location in self:
            if formatted and location._is_prefixed_by_parent():
                location.display_name = (
                    f"--{location.location_id.complete_name}/--{location.name}"
                )
            else:
                location.display_name = location.complete_name

    @api.depends("name", "location_id.complete_name", "usage")
    def _compute_complete_name(self):
        for location in self:
            if location._is_prefixed_by_parent():
                location.complete_name = (
                    f"{location.location_id.complete_name}/{location.name}"
                )
            else:
                location.complete_name = location.name

    @api.depends("quant_ids.quantity", "quant_ids.reserved_quantity")
    def _compute_is_empty(self):
        occupied_ids = self._get_occupied_location_ids(self)
        for location in self:
            location.is_empty = location.id not in occupied_ids

    @api.depends(
        "cyclic_inventory_frequency", "last_inventory_date", "usage", "company_id"
    )
    def _compute_next_inventory_date(self):
        today = fields.Date.today()
        for location in self:
            if not (
                location.company_id
                and location.usage in STOCKED_USAGES
                and location.cyclic_inventory_frequency > 0
            ):
                location.next_inventory_date = False
                continue
            frequency = timedelta(days=location.cyclic_inventory_frequency)
            if not location.last_inventory_date:
                location.next_inventory_date = today + frequency
            elif location.last_inventory_date + frequency <= today:
                location.next_inventory_date = today + timedelta(days=1)
            else:
                location.next_inventory_date = location.last_inventory_date + frequency

    @api.depends(
        "warehouse_view_ids", "warehouse_view_ids.active", "location_id.warehouse_id"
    )
    @dbg.timed
    def _compute_warehouse_id(self):
        chains = {
            location.id: list(location._get_ancestor_ids(include_self=True))
            for location in self
        }
        warehouses = (
            self.env["stock.warehouse"]
            .with_context(active_test=False)
            .search(
                [
                    (
                        "view_location_id",
                        "in",
                        list({*itertools.chain(*chains.values())}),
                    ),
                    ("active", "=", True),
                ],
            )
        )
        by_view_location = {
            warehouse.view_location_id.id: warehouse for warehouse in warehouses
        }
        for location in self:
            location.warehouse_id = next(
                (
                    by_view_location[node]
                    for node in reversed(chains[location.id])
                    if node in by_view_location
                ),
                False,
            )

    @dbg.timed
    def _compute_child_internal_location_ids(self):
        internal_locations = self.search_fetch(
            [("id", "child_of", self.ids), ("usage", "=", "internal")],
            ["parent_path"],
        )
        dbg.performance.debug(
            "_compute_child_internal_location_ids: %d roots, %d internal descendants",
            len(self),
            len(internal_locations),
        )
        descendant_ids = defaultdict(list)
        for location in internal_locations:
            for ancestor_id in location._get_ancestor_ids(include_self=True):
                descendant_ids[ancestor_id].append(location.id)
        for location in self:
            location.child_internal_location_ids = self.browse(
                descendant_ids.get(location.id, ()),
            )

    @api.depends("usage")
    def _compute_replenish_location(self):
        for loc in self:
            if loc.usage != "internal":
                loc.replenish_location = False

    def _search_is_empty(self, operator, value):
        if operator != "in" or set(value) != {True}:
            return NotImplemented
        return [("id", "not in", list(self._get_occupied_location_ids()))]

    @api.model
    def _get_domain_occupancy(self):
        return Domain("quantity", "!=", 0) | Domain("reserved_quantity", "!=", 0)

    @api.model
    def _get_occupied_location_ids(self, locations=None):
        domain = self._get_domain_occupancy() & Domain(
            "location_id.usage", "in", STOCKED_USAGES
        )
        if locations is not None:
            domain &= Domain("location_id", "in", locations.ids)
        return {
            location.id
            for (location,) in self.env["stock.quant"]._read_group(
                domain, ["location_id"]
            )
        }

    @api.model
    def _get_allocation_source_ids(self, view_location_ids):
        return self.search(
            [
                ("id", "child_of", view_location_ids),
                ("usage", "!=", "supplier"),
            ],
        ).ids

    def _is_child_of(self, other_location):
        return self._is_descendant_of(other_location)

    def _is_prefixed_by_parent(self):
        self.check_singleton()
        return bool(self.location_id) and self.usage != "view"

    def _is_outgoing(self):
        return self._is_partner_end("customer")

    def _is_incoming(self):
        return self._is_partner_end("supplier")

    def _is_partner_end(self, usage):
        self.check_singleton()
        if self.usage == usage:
            return True
        inter_company_location = (
            self.env.ref("stock.stock_location_inter_company", raise_if_not_found=False)
            or self.browse()
        )
        return self._is_child_of(inter_company_location)

    def is_reservation_bypass_required(self):
        self.check_singleton()
        return self.usage in ("supplier", "customer", "inventory", "production")

    def _propagate_active(self, active):
        changing = self.filtered(lambda location: location.active != bool(active))
        if not changing:
            return
        if is_internal_flag(self.env.context, CONTEXT_ACTIVE_CASCADE):
            return
        descendant_locations = (
            self.env["stock.location"]
            .with_context(active_test=False)
            .search([("id", "child_of", changing.ids)])
        )
        dbg.lifecycle.debug(
            "_propagate_active(%s): %s cascade to %s",
            active,
            dbg.rec(changing),
            dbg.rec(descendant_locations - changing),
        )
        if not active:
            changing._check_archivable(descendant_locations)
        (descendant_locations - changing).with_context(
            **{CONTEXT_ACTIVE_CASCADE: INTERNAL_CONTEXT_FLAG},
        ).write(
            {
                "active": active,
            },
        )

    def _check_archivable(self, descendant_locations):
        blocking_warehouse = self.env["stock.warehouse"].search(
            [
                ("active", "=", True),
                "|",
                ("lot_stock_id", "in", descendant_locations.ids),
                ("view_location_id", "in", descendant_locations.ids),
            ],
            limit=1,
        )
        if blocking_warehouse:
            location = (
                blocking_warehouse.lot_stock_id
                if blocking_warehouse.lot_stock_id in descendant_locations
                else blocking_warehouse.view_location_id
            )
            raise UserError(
                _(
                    "You cannot archive location %(location)s because it is used by warehouse %(warehouse)s",
                    location=location.display_name,
                    warehouse=blocking_warehouse.display_name,
                ),
            )
        occupied = self.browse(
            sorted(self._get_occupied_location_ids(descendant_locations)),
        )
        if occupied:
            raise UserError(
                _(
                    "You can't disable locations %s because they still contain products.",
                    ", ".join(occupied.mapped("display_name")),
                ),
            )

    @api.model
    def _invalidate_location_tree(self):
        self.invalidate_model(["child_internal_location_ids"])

    def _get_next_inventory_date(self):
        self.check_singleton()
        if self.usage not in STOCKED_USAGES:
            return False
        cyclic_date = self.next_inventory_date
        annual_date = self._get_company_annual_inventory_date()
        if cyclic_date and annual_date:
            return min(cyclic_date, annual_date)
        return cyclic_date or annual_date

    def _get_company_annual_inventory_date(self):
        self.check_singleton()
        if not self.company_id.annual_inventory_month:
            return False
        today = fields.Date.today()
        month = int(self.company_id.annual_inventory_month)
        day = max(self.company_id.annual_inventory_day, 1)
        day = min(day, calendar.monthrange(today.year, month)[1])
        annual_date = today.replace(month=month, day=day)
        if annual_date <= today:
            day = min(day, calendar.monthrange(today.year + 1, month)[1])
            annual_date = annual_date.replace(day=day, year=today.year + 1)
        return annual_date

    def _get_usage_label(self):
        self.check_singleton()
        return dict(
            self._fields["usage"]._description_selection(self.env),
        )[self.usage]
