from typing import NamedTuple

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain

from ..const import PARTNER_LOCATION_USAGES, PARTNER_USAGE_BY_PICKING_CODE
from ..tools import debug_log as dbg


class GroupingCriterion(NamedTuple):
    line_path: str
    label_field: str
    picking_path: str = ""
    wave_field: str = ""

    @property
    def batch_path(self):
        if self.picking_path:
            return f"picking_ids.{self.picking_path}"
        return f"move_line_ids.{self.line_path}"


class StockPickingType(models.Model):
    _name = "stock.picking.type"
    _inherit = ["mixin.date.category", "mixin.user.favorite"]
    _description = "Picking Type"
    _order = "is_user_favorite desc, sequence, id"
    _rec_names_search = ["name", "warehouse_id.name"]
    _check_company_auto = True

    name = fields.Char(
        string="Operation Type",
        translate=True,
        required=True,
    )
    code = fields.Selection(
        selection=[
            ("incoming", "Receipt"),
            ("outgoing", "Delivery"),
            ("internal", "Internal Transfer"),
        ],
        string="Type of Operation",
        default="incoming",
        required=True,
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(help="Used to order the 'All Operations' kanban view")
    color = fields.Integer()
    barcode = fields.Char(copy=False)

    sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Reference Sequence",
        copy=False,
        check_company=True,
    )
    sequence_code = fields.Char(
        string="Sequence Prefix",
        required=True,
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda s: s.env.company.id,
        index=True,
        required=True,
    )
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        compute="_compute_warehouse_id",
        store=True,
        readonly=False,
        ondelete="cascade",
        check_company=True,
    )

    default_location_src_id = fields.Many2one(
        comodel_name="stock.location",
        string="Source Location",
        compute="_compute_default_location_src_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        check_company=True,
        help="This is the default source location when this operation is manually created. However, it is possible to change it afterwards or that the routes use another one by default.",
    )
    default_location_dest_id = fields.Many2one(
        comodel_name="stock.location",
        string="Destination Location",
        compute="_compute_default_location_dest_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        check_company=True,
        help="This is the default destination location when this operation is manually created. However, it is possible to change it afterwards or that the routes use another one by default.",
    )

    return_picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Operation Type for Returns",
        index="btree_not_null",
        check_company=True,
    )
    move_type = fields.Selection(
        selection=[
            ("direct", "As soon as possible"),
            ("one", "When all products are ready"),
        ],
        string="Shipping Policy",
        default="direct",
        required=True,
        help="It specifies goods to be transferred partially or all at once",
    )
    create_backorder = fields.Selection(
        selection=[("ask", "Ask"), ("always", "Always"), ("never", "Never")],
        default="ask",
        required=True,
        help="When validating a transfer:\n"
        " * Ask: users are asked to choose if they want to make a backorder for remaining products\n"
        " * Always: a backorder is automatically created for the remaining products\n"
        " * Never: remaining products are cancelled",
    )

    reservation_method = fields.Selection(
        selection=[
            ("at_confirm", "At Confirmation"),
            ("manual", "Manually"),
            ("by_date", "Before scheduled date"),
        ],
        default="at_confirm",
        required=True,
        help="How products in transfers of this operation type should be reserved.",
    )
    reservation_days_before = fields.Integer(
        string="Days",
        help="Maximum number of days before scheduled date that products should be reserved.",
    )
    reservation_days_before_priority = fields.Integer(
        string="Days when starred",
        help="Maximum number of days before scheduled date that priority picking products should be reserved.",
    )

    use_create_lots = fields.Boolean(
        string="Create New Lots/Serial Numbers",
        compute="_compute_use_create_lots",
        default=True,
        store=True,
        readonly=False,
        help="If this is checked only, it will suppose you want to create new Lots/Serial Numbers, so you can provide them in a text field. ",
    )
    use_existing_lots = fields.Boolean(
        string="Use Existing Lots/Serial Numbers",
        compute="_compute_use_existing_lots",
        default=True,
        store=True,
        readonly=False,
        help="If this is checked, you will be able to choose the Lots/Serial Numbers. You can also decide to not put lots in this operation type.  This means it will create stock with no lot or not put a restriction on the lot taken. ",
    )
    show_entire_packs = fields.Boolean(
        string="Move Entire Packages",
        default=False,
        help="If ticked, packages to move will be directly displayed in Barcode instead of the products they contain",
    )
    set_package_type = fields.Boolean(
        default=False,
        help="If ticked, you will be able to select which package or package type to use in a put in pack",
    )

    print_label = fields.Boolean(
        string="Generate Shipping Labels",
        compute="_compute_print_label",
        store=True,
        readonly=False,
        help="Check this box if you want to generate shipping label in this operation.",
    )
    auto_print_delivery_slip = fields.Boolean(
        help="If this checkbox is ticked, Odoo will automatically print the delivery slip of a picking when it is validated."
    )
    auto_print_return_slip = fields.Boolean(
        help="If this checkbox is ticked, Odoo will automatically print the return slip of a picking when it is validated."
    )
    auto_print_product_labels = fields.Boolean(
        help="If this checkbox is ticked, Odoo will automatically print the product labels of a picking when it is validated."
    )
    product_label_format = fields.Selection(
        selection=[
            ("dymo", "Dymo"),
            ("2x7xprice", "2 x 7 with price"),
            ("4x7xprice", "4 x 7 with price"),
            ("4x12", "4 x 12"),
            ("4x12xprice", "4 x 12 with price"),
            ("zpl", "ZPL Labels"),
            ("zplxprice", "ZPL Labels with price"),
        ],
        string="Product Label Format to auto-print",
        default="2x7xprice",
    )
    auto_print_lot_labels = fields.Boolean(
        string="Auto Print Lot/SN Labels",
        help="If this checkbox is ticked, Odoo will automatically print the lot/SN labels of a picking when it is validated.",
    )
    lot_label_format = fields.Selection(
        selection=[
            ("4x12_lots", "4 x 12 - One per lot/SN"),
            ("4x12_units", "4 x 12 - One per unit"),
            ("zpl_lots", "ZPL Labels - One per lot/SN"),
            ("zpl_units", "ZPL Labels - One per unit"),
        ],
        string="Lot Label Format to auto-print",
        default="4x12_lots",
    )
    auto_print_packages = fields.Boolean(
        help="If this checkbox is ticked, Odoo will automatically print the packages and their contents of a picking when it is validated."
    )
    auto_print_package_label = fields.Boolean(
        help='If this checkbox is ticked, Odoo will automatically print the package label when "Put in Pack" button is used.'
    )
    package_label_to_print = fields.Selection(
        selection=[("pdf", "PDF"), ("zpl", "ZPL")],
        string="Package Label to Print",
        default="pdf",
    )

    auto_show_reception_report = fields.Boolean(
        string="Show Reception Report at Validation",
        help="If this checkbox is ticked, Odoo will automatically show the reception report (if there are moves to allocate to) when validating.",
    )
    auto_print_reception_report = fields.Boolean(
        help="If this checkbox is ticked, Odoo will automatically print the reception report of a picking when it is validated and has assigned moves."
    )
    auto_print_reception_report_labels = fields.Boolean(
        help="If this checkbox is ticked, Odoo will automatically print the reception report labels of a picking when it is validated."
    )

    picking_properties_definition = fields.PropertiesDefinition(
        string="Picking Properties"
    )

    is_user_favorite = fields.Boolean(string="Show Operation in Overview")

    show_operations = fields.Boolean(
        string="Show Detailed Operations",
        default=False,
        help="If this checkbox is ticked, the pickings lines will represent detailed stock operations. If not, the picking lines will represent an aggregate of detailed stock operations.",
    )
    hide_reservation_method = fields.Boolean(compute="_compute_hide_reservation_method")
    show_picking_type = fields.Boolean(compute="_compute_show_picking_type")

    count_picking_ready = fields.Integer(compute="_compute_picking_count")
    count_picking_waiting = fields.Integer(compute="_compute_picking_count")
    count_picking_late = fields.Integer(compute="_compute_picking_count")
    count_picking_backorders = fields.Integer(compute="_compute_picking_count")
    count_move_ready = fields.Integer(compute="_compute_count_move_ready")
    kanban_dashboard_graph = fields.Text(compute="_compute_kanban_dashboard_graph")

    _barcode_uniq = models.UniqueIndex(
        "(company_id, barcode) WHERE barcode IS NOT NULL",
        "Two operation types of the same company cannot share a barcode: a scan "
        "would have to guess which one it opens.",
    )
    _sequence_code_not_blank = models.Constraint(
        "CHECK (btrim(sequence_code) <> '')",
        "An operation type needs a sequence prefix: without one it gets no "
        "reference sequence, and its transfers cannot be numbered.",
    )

    @dbg.timed
    @api.model_create_multi
    def create(self, vals_list):
        dbg.lifecycle.debug(
            "stock.picking.type.create: %d vals, keys=%s",
            len(vals_list),
            dbg.vals_keys(vals_list),
        )
        picking_types = super().create(vals_list)
        dbg.lifecycle.debug(
            "stock.picking.type.create: created %s", dbg.rec(picking_types)
        )
        picking_types._update_reference_sequences()
        return picking_types

    @dbg.timed
    def unlink(self):
        dbg.lifecycle.debug("stock.picking.type.unlink %s", dbg.rec(self))
        sequences = self.sequence_id
        result = super().unlink()
        self._remove_orphaned_sequences(sequences)
        return result

    @dbg.timed
    def write(self, vals):
        dbg.lifecycle.debug(
            "stock.picking.type.write on %s: keys=%s", dbg.rec(self), dbg.keys(vals)
        )
        self._check_company_change(vals)
        types_changing_warehouse = (
            self.filtered(
                lambda picking_type: (
                    picking_type.warehouse_id.id != vals["warehouse_id"]
                ),
            )
            if vals.get("warehouse_id")
            else self.browse()
        )
        self._update_move_reservation_dates(vals)
        warehouse_before = {
            picking_type.id: picking_type.warehouse_id.id for picking_type in self
        }

        res = super().write(vals)

        moved = self.filtered(
            lambda picking_type: (
                picking_type.warehouse_id.id != warehouse_before[picking_type.id]
            )
        )
        if moved or types_changing_warehouse:
            dbg.logic.debug(
                "write: moved to another warehouse %s, changing warehouse %s",
                dbg.rec(moved),
                dbg.rec(types_changing_warehouse),
            )
        if "sequence_code" in vals:
            self._update_reference_sequences()
        elif moved:
            moved._update_reference_sequences()
        if types_changing_warehouse:
            types_changing_warehouse._update_default_locations_for_warehouse(vals)
        return res

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for picking, vals in zip(self, vals_list, strict=True):
            if "name" not in default:
                vals["name"] = _("%s (copy)", picking.name)
            if "sequence_code" not in default:
                vals["sequence_code"] = picking._get_unique_sequence_code()
        return vals_list

    def copy_translations(self, new, excluded=()):
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new, "name", lambda record, term: record.env._("%s (copy)", term)
        )

    def _check_company_change(self, vals):
        if "company_id" not in vals:
            return
        if self.filtered(lambda pt: pt.company_id.id != vals["company_id"]):
            raise UserError(
                _(
                    "Changing the company of this record is forbidden at this point, you should rather archive it and create a new one."
                )
            )

    def _update_move_reservation_dates(self, vals):
        days_changed = (
            "reservation_days_before" in vals
            or "reservation_days_before_priority" in vals
        )
        new_method = vals.get("reservation_method")
        if new_method and new_method != "by_date":
            leaving_by_date = self.filtered(
                lambda pt: pt.reservation_method == "by_date"
            )
            if leaving_by_date:
                dbg.logic.debug(
                    "_update_move_reservation_dates: %s leave by_date, clearing dates",
                    dbg.rec(leaving_by_date),
                )
                self.env["stock.move"].search(
                    [
                        ("picking_type_id", "in", leaving_by_date.ids),
                        ("state", "not in", ("assigned", "done", "cancel")),
                    ]
                ).date_reservation = False
            return
        if not (new_method == "by_date" or days_changed):
            return

        if new_method == "by_date" and not days_changed:
            picking_types = self.filtered(lambda pt: pt.reservation_method != "by_date")
        elif new_method == "by_date":
            picking_types = self
        else:
            picking_types = self.filtered(lambda pt: pt.reservation_method == "by_date")
        if not picking_types:
            return

        for picking_type, moves in self.env["stock.move"]._read_group(
            [
                ("picking_type_id", "in", picking_types.ids),
                (
                    "state",
                    "in",
                    ("draft", "confirmed", "waiting", "partially_available"),
                ),
            ],
            ["picking_type_id"],
            ["id:recordset"],
        ):
            common_days = vals.get(
                "reservation_days_before", picking_type.reservation_days_before
            )
            priority_days = vals.get(
                "reservation_days_before_priority",
                picking_type.reservation_days_before_priority,
            )
            dbg.lifecycle.debug(
                "[picking_type:%s] reservation dates on %s: %s/%s days",
                picking_type.id,
                dbg.rec(moves),
                common_days,
                priority_days,
            )
            moves._update_date_reservation_from_days(common_days, priority_days)

    def _update_default_locations_for_warehouse(self, vals):
        new_warehouse = self.warehouse_id
        stock_location = new_warehouse.lot_stock_id
        to_update = {}
        for picking_type in self:
            if (
                "default_location_src_id" not in vals
                and picking_type.code != "incoming"
            ):
                source = picking_type.default_location_src_id
                if not source or (
                    source.warehouse_id and source.warehouse_id != new_warehouse
                ):
                    to_update.setdefault("default_location_src_id", self.browse())
                    to_update["default_location_src_id"] |= picking_type
            if (
                "default_location_dest_id" not in vals
                and picking_type.code != "outgoing"
            ):
                destination = picking_type.default_location_dest_id
                if not destination or (
                    destination.warehouse_id
                    and destination.warehouse_id != new_warehouse
                ):
                    to_update.setdefault("default_location_dest_id", self.browse())
                    to_update["default_location_dest_id"] |= picking_type
        for field_name, picking_types in to_update.items():
            dbg.logic.debug(
                "_update_default_locations_for_warehouse: %s.%s -> %s",
                dbg.rec(picking_types),
                field_name,
                stock_location.id,
            )
            picking_types.write({field_name: stock_location.id})

    @api.depends("code")
    def _compute_hide_reservation_method(self):
        for picking_type in self:
            picking_type.hide_reservation_method = picking_type.code == "incoming"

    @api.model
    def _get_transfer_codes(self):
        return {"incoming", "outgoing", "internal"}

    @api.depends("code")
    def _compute_show_picking_type(self):
        transfer_codes = self._get_transfer_codes()
        for picking_type in self:
            picking_type.show_picking_type = picking_type.code in transfer_codes

    @api.depends("code")
    def _compute_use_create_lots(self):
        for picking_type in self:
            if picking_type.code == "incoming":
                picking_type.use_create_lots = True

    @api.depends("code")
    def _compute_use_existing_lots(self):
        for picking_type in self:
            if picking_type.code == "outgoing":
                picking_type.use_existing_lots = True

    @api.depends("code")
    def _compute_print_label(self):
        for picking_type in self:
            if picking_type.code in ("incoming", "internal"):
                picking_type.print_label = False
            elif picking_type.code == "outgoing":
                picking_type.print_label = True

    def _update_derived_default_location(self, field_name, derive, partner_usage):
        undecidable = self.browse()
        for picking_type in self:
            current = picking_type[field_name]
            if current and picking_type._is_default_location_suitable(
                current, partner_usage
            ):
                # the silent half of this gate used to be the one people ask
                # about: "why did my operation type NOT pick up the new
                # default?" produced nothing in any trace
                dbg.logic.debug(
                    "[picking_type:%s] %s: kept %s, still suitable for code=%s",
                    picking_type.id,
                    field_name,
                    current.id,
                    picking_type.code,
                )
                continue
            location = derive(picking_type)
            if location:
                dbg.logic.debug(
                    "[picking_type:%s] %s: %s -> %s (code=%s)",
                    picking_type.id,
                    field_name,
                    current.id,
                    location.id,
                    picking_type.code,
                )
                picking_type[field_name] = location.id
            elif not current:
                undecidable |= picking_type
        if undecidable:
            undecidable._raise_undecidable_default_locations()

    def _is_default_location_suitable(self, location, partner_usage):
        # `code` is the derivation's only trigger, so assigning unconditionally
        # reset Pack's (Packing Zone -> Output), Receipts' Input and Delivery's
        # Output on any write of `code`, including one that changed nothing.
        # The derivation is a default, not a definition: it applies when the
        # field is empty, and when what it holds contradicts the new code.
        self.check_singleton()
        if PARTNER_USAGE_BY_PICKING_CODE.get(self.code) == partner_usage:
            # a transit location is the inter-warehouse and inter-company
            # stand-in for the partner one: an incoming type resupplied from
            # another warehouse receives from transit, not from Vendors, and
            # re-deriving it would undo that configuration
            return location.usage in (partner_usage, "transit")
        return location.usage not in PARTNER_LOCATION_USAGES

    def _raise_undecidable_default_locations(self):
        companies = self.company_id or self.env.company
        if not self.env["stock.warehouse"].search_count(
            [("company_id", "in", companies.ids)], limit=1
        ):
            self.env["stock.warehouse"]._raise_missing_warehouse()
        raise UserError(
            _(
                "Operation type %(name)s has no warehouse, so its default "
                "locations cannot be derived. Set a warehouse on it, or give it "
                "explicit source and destination locations.",
                name=self[0].display_name or _("(new)"),
            )
        )

    @api.depends("code")
    def _compute_default_location_src_id(self):
        supplier_location = (
            self.env["stock.warehouse"]._get_partner_location("supplier")
            if any(picking_type.code == "incoming" for picking_type in self)
            else self.env["stock.location"]
        )
        self._update_derived_default_location(
            "default_location_src_id",
            lambda picking_type: (
                supplier_location
                if picking_type.code == "incoming"
                else picking_type.warehouse_id.lot_stock_id
            ),
            "supplier",
        )

    @api.depends("code")
    def _compute_default_location_dest_id(self):
        customer_location = (
            self.env["stock.warehouse"]._get_partner_location("customer")
            if any(picking_type.code == "outgoing" for picking_type in self)
            else self.env["stock.location"]
        )
        self._update_derived_default_location(
            "default_location_dest_id",
            lambda picking_type: (
                customer_location
                if picking_type.code == "outgoing"
                else picking_type.warehouse_id.lot_stock_id
            ),
            "customer",
        )

    @api.depends("company_id")
    def _compute_warehouse_id(self):
        needing_warehouse = self.filtered(
            lambda picking_type: (
                not picking_type.warehouse_id and picking_type.company_id
            )
        )
        if not needing_warehouse:
            return
        first_by_company = {
            company.id: warehouse_id
            for company, warehouse_id in self.env["stock.warehouse"]._read_group(
                [("company_id", "in", needing_warehouse.company_id.ids)],
                ["company_id"],
                ["id:min"],
            )
        }
        for picking_type in needing_warehouse:
            picking_type.warehouse_id = first_by_company.get(
                picking_type.company_id.id, False
            )

    @api.depends("warehouse_id", "warehouse_id.name")
    def _compute_display_name(self):
        for picking_type in self:
            if picking_type.warehouse_id:
                picking_type.display_name = (
                    f"{picking_type.warehouse_id.name}: {picking_type.name}"
                )
            else:
                picking_type.display_name = picking_type.name

    _OPEN_PICKING_STATES = ("assigned", "waiting", "confirmed")

    @api.model
    def _search_display_name(self, operator, value):
        if operator in ("in", "not in"):
            return NotImplemented
        warehouse_name, _sep, picking_type_name = (
            value.partition(": ") if isinstance(value, str) else ("", "", "")
        )
        if not (warehouse_name and picking_type_name):
            return super()._search_display_name(operator, value)
        positive = Domain.NEGATIVE_OPERATORS.get(operator, operator)
        matched = (
            Domain("warehouse_id.name", positive, warehouse_name)
            & Domain("name", positive, picking_type_name)
        ) | Domain("name", positive, value)
        return matched if positive == operator else ~matched

    @api.onchange("code")
    def _onchange_code(self):
        if self.code == "internal" and not self.env.user.has_group(
            "stock.group_stock_multi_locations"
        ):
            return {
                "warning": {
                    "message": _(
                        "You need to activate storage locations to be able to do internal operation types."
                    )
                }
            }
        return None

    @api.onchange("sequence_code", "warehouse_id")
    def _onchange_sequence_code(self):
        if not self.sequence_code:
            return None
        clashing = self._get_clashing_picking_type()
        if clashing and clashing.sequence_id != self.sequence_id:
            return {
                "warning": {
                    "message": _(
                        "This sequence prefix is already used by %(name)s%(archived)s. "
                        "Pick a unique prefix.",
                        name=clashing.display_name,
                        archived="" if clashing.active else _(" (archived)"),
                    )
                }
            }
        return None

    @api.constrains(
        "warehouse_id", "default_location_src_id", "default_location_dest_id"
    )
    def _check_default_locations_are_derivable(self):
        undecidable = self.filtered(
            lambda picking_type: (
                not picking_type.warehouse_id
                and not (
                    picking_type.default_location_src_id
                    and picking_type.default_location_dest_id
                )
            )
        )
        if undecidable:
            undecidable._raise_undecidable_default_locations()

    def _check_single_or_empty(self):
        if len(self) > 1:
            raise ValueError(
                f"an operation type action opens one type at a time, got {self!r}"
            )

    @api.model
    def _get_grouping_criteria(self):
        return {
            **self._get_batch_grouping_criteria(),
            **self._get_wave_grouping_criteria(),
        }

    def _get_active_grouping_criteria(self, criteria):
        self.check_singleton()
        return {key: criterion for key, criterion in criteria.items() if self[key]}

    def _get_active_batch_criteria(self):
        return self._get_active_grouping_criteria(self._get_batch_grouping_criteria())

    def _get_active_wave_criteria(self):
        return self._get_active_grouping_criteria(self._get_grouping_criteria())

    auto_batch = fields.Boolean(
        string="Automatic Batches",
        help="Automatically put pickings into batches as they are confirmed when possible.",
    )

    batch_group_by_partner = fields.Boolean(
        string="Contact",
        help="Automatically group batches by contacts.",
    )

    batch_group_by_destination = fields.Boolean(
        string="Destination Country",
        help="Automatically group batches by destination country.",
    )

    batch_group_by_src_loc = fields.Boolean(
        string="Group by Source Location",
        help="Automatically group batches by their source location.",
    )

    batch_group_by_dest_loc = fields.Boolean(
        string="Group by Destination Location",
        help="Automatically group batches by their destination location.",
    )

    wave_group_by_product = fields.Boolean(
        string="Product",
        help="Split transfers by product then group transfers that have the same product.",
    )

    wave_group_by_category = fields.Boolean(
        string="Product Category",
        help="Split transfers by product category, then group transfers that have the same product category.",
    )

    wave_category_ids = fields.Many2many(
        comodel_name="product.category",
        string="Wave Product Categories",
        help="Categories to consider when grouping waves.",
    )

    wave_group_by_location = fields.Boolean(
        string="Location",
        help="Split transfers by defined locations, then group transfers with the same location.",
    )

    wave_location_ids = fields.Many2many(
        comodel_name="stock.location",
        string="Wave Locations",
        domain="[('usage', '=', 'internal')]",
        help="Locations to consider when grouping waves.",
    )

    batch_max_lines = fields.Integer(
        string="Maximum lines",
        help="A transfer will not be automatically added to batches that will exceed this number of lines if the transfer is added to it.\n"
        "Leave this value as '0' if no line limit.",
    )

    batch_max_pickings = fields.Integer(
        string="Maximum transfers",
        help="A transfer will not be automatically added to batches that will exceed this number of transfers.\n"
        "Leave this value as '0' if no transfer limit.",
    )

    batch_auto_confirm = fields.Boolean(
        string="Auto-confirm",
        default=True,
    )

    batch_properties_definition = fields.PropertiesDefinition(string="Batch Properties")

    @api.model
    def _get_batch_grouping_criteria(self):
        return {
            "batch_group_by_partner": GroupingCriterion(
                "move_id.partner_id", "name", "partner_id", "wave_partner_id"
            ),
            "batch_group_by_destination": GroupingCriterion(
                "move_id.partner_id.country_id",
                "name",
                "partner_id.country_id",
                "wave_country_id",
            ),
            "batch_group_by_src_loc": GroupingCriterion(
                "location_id", "display_name", "location_id", "wave_source_location_id"
            ),
            "batch_group_by_dest_loc": GroupingCriterion(
                "location_dest_id",
                "display_name",
                "location_dest_id",
                "wave_dest_location_id",
            ),
        }

    @api.model
    def _get_wave_grouping_criteria(self):
        return {
            "wave_group_by_product": GroupingCriterion(
                "product_id", "display_name", wave_field="wave_product_id"
            ),
            "wave_group_by_category": GroupingCriterion(
                "product_id.categ_id", "complete_name", wave_field="wave_category_id"
            ),
        }

    def _get_nearest_wave_location(self, location):
        self.check_singleton()
        wave_location_ids = set(self.wave_location_ids.ids)
        while location and location.id not in wave_location_ids:
            location = location.location_id
        return location

    @api.model
    def _get_batch_group_by_keys(self):
        return list(self._get_batch_grouping_criteria())

    @api.model
    def _get_wave_group_by_keys(self):
        return [*self._get_wave_grouping_criteria(), "wave_group_by_location"]

    @api.model
    def _get_batch_and_wave_group_by_keys(self):
        return self._get_batch_group_by_keys() + self._get_wave_group_by_keys()

    @api.constrains(
        lambda self: self._get_batch_and_wave_group_by_keys() + ["auto_batch"]
    )
    def _check_auto_batch_group_by(self):
        group_by_keys = self._get_batch_and_wave_group_by_keys()
        for picking_type in self:
            if not picking_type.auto_batch:
                continue
            if not any(picking_type[key] for key in group_by_keys):
                raise ValidationError(
                    _(
                        "If the Automatic Batches feature is enabled, at least one 'Group by' option must be selected."
                    )
                )

    @api.constrains("batch_max_lines", "batch_max_pickings")
    def _check_batch_limits(self):
        for picking_type in self:
            if picking_type.batch_max_lines < 0 or picking_type.batch_max_pickings < 0:
                raise ValidationError(
                    _(
                        "Batch limits cannot be negative. Leave a limit at '0' to disable it."
                    )
                )
