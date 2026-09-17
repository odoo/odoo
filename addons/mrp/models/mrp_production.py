import datetime
import json
import math
import re
from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, format_datetime
from odoo.tools.misc import (
    OrderedSet,
    format_date,
    topological_sort,
)
from odoo.tools.misc import (
    groupby as tools_groupby,
)

from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from odoo.addons.web.controllers.utils import clean_action

_debug = DebugLog(__name__)

SIZE_BACK_ORDER_NUMBERING = 3
_NON_INVENTORY_MOVE_DOMAIN = [("location_dest_usage", "!=", "inventory")]


class MrpProduction(models.Model):
    _name = "mrp.production"
    _description = "Manufacturing Order"
    _date_name = "date_start"
    _inherit = [
        "mixin.mail.thread",
        "mixin.mail.activity",
        "mixin.catalog.child.lines",
        "mixin.product.catalog",
        "mixin.date.category",
    ]
    _order = "priority desc, date_start asc,id"
    _date_category_field = "date_start"

    @api.model
    def default_get(self, fields):
        context = dict(self.env.context)
        product_qty = context.pop("bom_overview_product_qty", False)
        picking_type_id = context.pop("bom_overview_picking_type_id", False)
        defaults = super(MrpProduction, self.with_context(context)).default_get(fields)

        if product_qty:
            defaults["product_qty"] = product_qty
        if picking_type_id:
            defaults["picking_type_id"] = picking_type_id

        return defaults

    @api.model
    def _default_date_start(self):
        if self.env.context.get("default_date_deadline"):
            date_end = fields.Datetime.to_datetime(
                self.env.context.get("default_date_deadline")
            )
            return date_end - relativedelta(hours=1)
        return fields.Datetime.now()

    @api.model
    def _default_date_end(self):
        if self.env.context.get("default_date_deadline"):
            return fields.Datetime.to_datetime(
                self.env.context.get("default_date_deadline")
            )
        date_start = fields.Datetime.now()
        return date_start + relativedelta(hours=1)

    @api.model
    def _default_is_locked(self):
        return not self.env.user.has_group("mrp.group_unlocked_by_default")

    name = fields.Char(
        string="Reference",
        default=lambda self: _("New"),
        copy=False,
        readonly=True,
    )
    priority = fields.Selection(
        selection=PROCUREMENT_PRIORITIES,
        default="0",
        help="Components will be reserved first for the MO with the highest priorities.",
    )
    backorder_sequence = fields.Integer(
        default=0,
        copy=False,
        help="Backorder sequence, if equals to 0 means there is not related backorder",
    )
    origin = fields.Char(
        string="Source",
        copy=False,
        help="Reference of the document that generated this production order request.",
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        compute="_compute_product_id",
        precompute=True,
        store=True,
        copy=True,
        readonly=False,
        required=True,
        domain="[('type', '=', 'consu')]",
        check_company=True,
    )
    production_group_id = fields.Many2one(
        comodel_name="mrp.production.group",
        index=True,
        copy=False,
    )

    product_variant_attributes = fields.Many2many(
        comodel_name="product.template.attribute.value",
        related="product_id.product_template_attribute_value_ids",
    )
    valid_product_template_attribute_line_ids = fields.Many2many(
        related="product_tmpl_id.valid_product_template_attribute_line_ids"
    )
    never_product_template_attribute_value_ids = fields.Many2many(
        comodel_name="product.template.attribute.value",
        relation="template_attribute_value_mrp_production_rel",
        column1="production_id",
        column2="template_attribute_value_id",
        string="Never attribute values",
        domain="""[
            '&',
                ('attribute_line_id', 'in', valid_product_template_attribute_line_ids),
                ('attribute_id.create_variant', '=', 'no_variant')]""",
    )

    workcenter_id = fields.Many2one(
        comodel_name="mrp.workcenter",
        store=False,
    )
    product_tracking = fields.Selection(related="product_id.tracking")
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        related="product_id.product_tmpl_id",
        string="Product Template",
    )
    product_qty = fields.Float(
        string="Quantity To Produce",
        digits="Product Unit",
        compute="_compute_product_qty",
        precompute=True,
        store=True,
        copy=True,
        readonly=False,
        required=True,
        tracking=True,
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
        copy=True,
        readonly=False,
        required=True,
        domain="[('id', 'in', allowed_uom_ids)]",
    )
    lot_producing_ids = fields.Many2many(
        comodel_name="stock.lot",
        string="Lot/Serial Number",
        copy=False,
        domain="[('product_id', '=', product_id)]",
        check_company=True,
    )
    qty_producing = fields.Float(
        string="Quantity Producing",
        digits="Product Unit",
        copy=False,
    )
    product_uom_qty = fields.Float(
        string="Total Quantity",
        compute="_compute_product_uom_qty",
        store=True,
    )
    picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Operation Type",
        compute="_compute_picking_type_id",
        precompute=True,
        store=True,
        index=True,
        copy=True,
        readonly=False,
        required=True,
        domain="[('code', '=', 'mrp_operation')]",
        check_company=True,
    )
    use_create_components_lots = fields.Boolean(
        related="picking_type_id.use_create_components_lots"
    )
    location_src_id = fields.Many2one(
        comodel_name="stock.location",
        string="Components Location",
        compute="_compute_locations",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        domain="[('usage','=','internal')]",
        check_company=True,
        help="Location where the system will look for components.",
    )
    warehouse_id = fields.Many2one(related="location_src_id.warehouse_id")
    location_dest_id = fields.Many2one(
        comodel_name="stock.location",
        string="Finished Products Location",
        compute="_compute_locations",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        domain="[('usage','=','internal')]",
        check_company=True,
        help="Location where the system will stock the finished products.",
    )
    location_final_id = fields.Many2one(
        comodel_name="stock.location",
        string="Final Location from procurement",
    )
    date_deadline = fields.Datetime(
        string="Deadline",
        compute="_compute_date_deadline",
        store=True,
        copy=False,
        readonly=False,
        help="Informative date allowing to define when the manufacturing order should be processed at the latest to fulfill delivery on time.",
    )
    date_start = fields.Datetime(
        string="Start",
        default=_default_date_start,
        index=True,
        copy=False,
        required=True,
        help="Date you plan to start production or date you actually started production.",
    )
    date_end = fields.Datetime(
        string="End",
        compute="_compute_date_end",
        default=_default_date_end,
        store=True,
        copy=False,
        help="Date you expect to finish production or actual date you finished production.",
    )
    duration_expected = fields.Float(
        string="Expected Duration",
        compute="_compute_duration_expected",
        help="Total expected duration (in minutes)",
    )
    duration = fields.Float(
        string="Real Duration",
        compute="_compute_duration",
        help="Total real duration (in minutes)",
    )

    bom_id = fields.Many2one(
        comodel_name="mrp.bom",
        string="Bill of Material",
        compute="_compute_bom_id",
        precompute=True,
        store=True,
        readonly=False,
        domain="""[
        '&',
            '|',
                ('company_id', '=', False),
                ('company_id', '=', company_id),
            '&',
                '|',
                    ('product_id','=',product_id),
                    '&',
                        ('product_tmpl_id.product_variant_ids','=',product_id),
                        ('product_id','=',False),
        ('type', '=', 'normal')]""",
        check_company=True,
        help="Bills of Materials, also called recipes, are used to autocomplete components and work order instructions.",
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("progress", "In Progress"),
            ("to_close", "To Close"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        compute="_compute_state",
        store=True,
        index=True,
        copy=False,
        readonly=True,
        tracking=True,
        help=" * Draft: The MO is not confirmed yet.\n"
        " * Confirmed: The MO is confirmed, the stock rules and the reordering of the components are trigerred.\n"
        " * In Progress: The production has started (on the MO or on the WO).\n"
        " * To Close: The production is done, the MO has to be closed.\n"
        " * Done: The MO is closed, the stock moves are posted. \n"
        " * Cancelled: The MO has been cancelled, can't be confirmed anymore.",
    )
    reservation_state = fields.Selection(
        selection=[
            ("confirmed", "Waiting"),
            ("assigned", "Ready"),
            ("waiting", "Waiting Another Operation"),
        ],
        string="MO Readiness",
        compute="_compute_reservation_state",
        store=True,
        index=True,
        copy=False,
        readonly=True,
        tracking=True,
        help="Manufacturing readiness for this MO, as per bill of material configuration:\n\
            * Ready: The material is available to start the production.\n\
            * Waiting: The material is not available to start the production.\n",
    )

    move_raw_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="raw_material_production_id",
        string="Components",
        compute="_compute_move_raw_ids",
        store=True,
        copy=False,
        readonly=False,
        domain=_NON_INVENTORY_MOVE_DOMAIN,
    )
    move_finished_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="production_id",
        string="Finished Products",
        compute="_compute_move_finished_ids",
        store=True,
        copy=False,
        readonly=False,
        domain=_NON_INVENTORY_MOVE_DOMAIN,
    )
    # Undomained siblings of `move_raw_ids` and `move_finished_ids`, and the
    # reason they are declared is not that anything reads them. `modified()`
    # navigates from a written `stock.move` back to the productions whose
    # dependent fields need recomputing, and it does that through an inverse
    # One2many; the domained pair cannot serve, so without these two the ORM
    # falls back to one query per production on every move written. Measured on
    # a fresh database, `mrp.production.create()` of 20 orders: 4 queries per
    # order with them, 6 without.
    all_move_raw_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="raw_material_production_id",
    )
    all_move_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="production_id",
    )
    move_byproduct_ids = fields.One2many(
        comodel_name="stock.move",
        compute="_compute_move_byproduct_ids",
        inverse="_inverse_move_byproduct_ids",
    )
    finished_move_line_ids = fields.One2many(
        comodel_name="stock.move.line",
        string="Finished Product",
        compute="_compute_finished_move_line_ids",
        inverse="_inverse_finished_move_line_ids",
    )
    workorder_ids = fields.One2many(
        comodel_name="mrp.workorder",
        inverse_name="production_id",
        string="Work Orders",
        compute="_compute_workorder_ids",
        store=True,
        copy=True,
        readonly=False,
    )
    move_dest_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="created_production_id",
        string="Stock Movements of Produced Goods",
    )

    unreserve_visible = fields.Boolean(
        string="Allowed to Unreserve Production",
        compute="_compute_reservation_visibility",
        help="Technical field to check when we can unreserve",
    )
    reserve_visible = fields.Boolean(
        string="Allowed to Reserve Production",
        compute="_compute_reservation_visibility",
        help="Technical field to check when we can reserve quantities",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        default=lambda self: self.env.user,
        domain=lambda self: [
            ("all_group_ids", "in", self.env.ref("mrp.group_mrp_user").id)
        ],
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
        required=True,
    )

    qty_produced = fields.Float(
        string="Quantity Produced",
        compute="_compute_qty_produced",
    )
    reference_ids = fields.Many2many(
        comodel_name="stock.reference",
        relation="stock_reference_production_rel",
        column1="production_id",
        column2="reference_id",
        string="References",
        copy=False,
    )
    product_description_variants = fields.Char(string="Custom Description")
    orderpoint_id = fields.Many2one(
        comodel_name="stock.warehouse.orderpoint",
        index="btree_not_null",
        copy=False,
    )
    propagate_cancel = fields.Boolean(
        string="Propagate cancel and split",
        help="If checked, when the previous move of the move (which was generated by a next procurement) is cancelled or split, the move generated by this move will too",
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
    scrap_ids = fields.One2many(
        comodel_name="stock.scrap",
        inverse_name="production_id",
        string="Scraps",
    )
    scrap_count = fields.Integer(
        string="Scrap Move",
        compute="_compute_scrap_count",
    )
    unbuild_ids = fields.One2many(
        comodel_name="mrp.unbuild",
        inverse_name="mo_id",
        string="Unbuilds",
    )
    unbuild_count = fields.Count(
        count_of="unbuild_ids",
        string="Number of Unbuilds",
    )
    is_locked = fields.Boolean(
        default=_default_is_locked,
        copy=False,
    )
    is_planned = fields.Boolean(
        string="Its Operations are Planned",
        compute="_compute_is_planned",
        store=True,
    )

    show_final_lots = fields.Boolean(compute="_compute_show_final_lots")
    production_location_id = fields.Many2one(
        comodel_name="stock.location",
        compute="_compute_production_location_id",
        store=True,
    )
    picking_ids = fields.Many2many(
        comodel_name="stock.picking",
        string="Picking associated to this manufacturing order",
        compute="_compute_picking_ids",
    )
    count_transfer_outgoing = fields.Count(
        count_of="picking_ids",
        string="Delivery Orders",
    )
    consumption = fields.Selection(
        selection=[
            ("flexible", "Allowed"),
            ("warning", "Allowed with warning"),
            ("strict", "Blocked"),
        ],
        default="flexible",
        readonly=True,
        required=True,
    )

    mrp_production_child_count = fields.Integer(
        string="Number of generated MO",
        compute="_compute_mrp_production_child_count",
    )
    mrp_production_source_count = fields.Integer(
        string="Number of source MO",
        compute="_compute_mrp_production_source_count",
    )
    mrp_production_backorder_count = fields.Integer(
        string="Count of linked backorder",
        compute="_compute_mrp_production_backorder_count",
    )
    show_lock = fields.Boolean(
        string="Show Lock/unlock buttons",
        compute="_compute_show_lock",
    )
    components_availability = fields.Char(
        string="Component Status",
        compute="_compute_component_availability",
        help="Latest component availability status for this MO. If green, then the MO's readiness status is ready, as per BOM configuration.",
    )
    components_availability_state = fields.Selection(
        selection=[
            ("available", "Available"),
            ("expected", "Expected"),
            ("late", "Late"),
            ("unavailable", "Not Available"),
        ],
        compute="_compute_component_availability",
        search="_search_components_availability_state",
    )
    production_capacity = fields.Float(
        compute="_compute_production_capacity",
        help="Quantity that can be produced with the current stock of components",
    )
    show_lot_ids = fields.Boolean(
        string="Display the serial number shortcut on the moves",
        compute="_compute_show_lot_ids",
    )
    forecasted_issue = fields.Boolean(compute="_compute_forecasted_issue")
    show_allocation = fields.Boolean(
        compute="_compute_show_allocation",
        help='Technical Field used to decide whether the button "Allocation" should be displayed.',
    )
    allow_workorder_dependencies = fields.Boolean(
        string="Allow Work Order Dependencies"
    )
    show_produce = fields.Boolean(
        compute="_compute_produce_visibility",
        help="Technical field to check if produce button can be shown",
    )
    show_generate_bom = fields.Boolean(
        string="Show Generate BOM",
        compute="_compute_show_generate_bom",
    )
    show_produce_all = fields.Boolean(
        compute="_compute_produce_visibility",
        help="Technical field to check if produce all button can be shown",
    )
    is_outdated_bom = fields.Boolean(
        string="Outdated BoM",
        help="The BoM has been updated since creation of the MO",
    )
    is_delayed = fields.Boolean(
        compute="_compute_is_delayed",
        search="_search_is_delayed",
    )
    serial_numbers_count = fields.Integer(
        string="Count of serial numbers",
        compute="_compute_serial_numbers_count",
    )

    _name_uniq = models.UniqueIndex(
        "(name, company_id) WHERE name IS NOT NULL",
        "Reference must be unique per Company!",
    )
    _qty_positive = models.Constraint(
        "check (product_qty > 0)",
        "The quantity to produce must be positive!",
    )

    @api.depends("production_group_id.child_ids.production_ids")
    def _compute_mrp_production_child_count(self):
        for production in self:
            production.mrp_production_child_count = len(production._get_children())

    @api.depends("production_group_id.parent_ids.production_ids")
    def _compute_mrp_production_source_count(self):
        for production in self:
            production.mrp_production_source_count = len(production._get_sources())

    @api.depends("production_group_id.production_ids")
    def _compute_mrp_production_backorder_count(self):
        for production in self:
            production.mrp_production_backorder_count = len(
                production.production_group_id.production_ids
            )

    @api.depends("company_id", "bom_id")
    def _compute_picking_type_id(self):
        picking_types = self.env["stock.picking.type"].search_read(
            [
                ("code", "=", "mrp_operation"),
                ("warehouse_id.company_id", "in", self.company_id.ids),
            ],
            ["company_id"],
            load=False,
        )
        picking_type_by_company = {}
        for picking_type in picking_types:
            picking_type_by_company.setdefault(
                picking_type["company_id"], picking_type["id"]
            )
        default_picking_type_id = self.env.context.get("default_picking_type_id")
        default_picking_type = default_picking_type_id and self.env[
            "stock.picking.type"
        ].browse(default_picking_type_id)
        if not default_picking_type:
            default_warehouse_id = self.env.context.get("force_warehouse_id")
            default_picking_type = (
                default_warehouse_id
                and self.env["stock.warehouse"]
                .browse(default_warehouse_id)
                .manu_type_id
            )
        companies_with_warehouse = None
        for mo in self:
            if (
                default_picking_type
                and default_picking_type.company_id == mo.company_id
            ):
                mo.picking_type_id = default_picking_type
                continue
            if mo.bom_id and mo.bom_id.picking_type_id:
                mo.picking_type_id = mo.bom_id.picking_type_id
                continue
            if mo.picking_type_id and mo.picking_type_id.company_id == mo.company_id:
                continue
            mo.picking_type_id = picking_type_by_company.get(mo.company_id.id, False)
            if companies_with_warehouse is None:
                companies_with_warehouse = {
                    company.id
                    for [company] in self.env["stock.warehouse"]._read_group(  # noqa: E8507 - computed once, on first need, over every company of the batch
                        [("company_id", "in", self.company_id.ids)], ["company_id"]
                    )
                }
            if mo.company_id.id not in companies_with_warehouse:
                self.env["stock.warehouse"]._raise_missing_warehouse()

    @api.depends("bom_id", "product_id")
    def _compute_product_uom_id(self):
        for production in self:
            if production.state != "draft":
                continue
            if production.bom_id and production._origin.bom_id != production.bom_id:
                production.product_uom_id = production.bom_id.product_uom_id
            elif production.product_id:
                production.product_uom_id = production.product_id.uom_id
            else:
                production.product_uom_id = False

    @api.depends("picking_type_id")
    def _compute_locations(self):
        fallback_location_by_company = {}

        def get_fallback_location(production):
            company = (
                production.company_id
                if production.company_id and production.company_id in self.env.companies
                else self.env.company
            )
            if company.id not in fallback_location_by_company:
                fallback_location_by_company[company.id] = (
                    self.env["stock.warehouse"]
                    .search([("company_id", "=", company.id)], limit=1)
                    .lot_stock_id
                )
            return fallback_location_by_company[company.id]

        for production in self:
            picking_type = production.picking_type_id
            production.location_src_id = (
                picking_type.default_location_src_id.id
                or get_fallback_location(production).id
            )
            production.location_dest_id = (
                picking_type.default_location_dest_id.id
                or get_fallback_location(production).id
            )

    @api.model
    def _get_domain_components_availability_open(self):
        return Domain("state", "in", ("confirmed", "progress", "to_close"))

    @api.model
    def _get_domain_components_availability_unsettled_move(self):
        return Domain("location_dest_usage", "!=", "inventory") & (
            Domain("state", "!=", "assigned")
            | Domain.custom(
                to_sql=lambda model, alias, query: SQL(
                    "%s < %s",
                    SQL.identifier(alias, "quantity"),
                    SQL.identifier(alias, "product_uom_qty"),
                )
            )
        )

    @api.model
    def _search_components_availability_state(self, operator, value):
        if operator != "in":
            return NotImplemented

        open_orders = self._get_domain_components_availability_open()
        unsettled = Domain(
            "move_raw_ids",
            "any",
            self._get_domain_components_availability_unsettled_move(),
        )
        candidates = self.search(open_orders & unsettled)
        matching = candidates.filtered(
            lambda production: production.components_availability_state in value
        )
        matched = Domain("id", "in", matching.ids)

        if "available" not in value:
            return matched
        return matched | (
            open_orders
            & Domain(
                "move_raw_ids",
                "not any",
                self._get_domain_components_availability_unsettled_move(),
            )
        )

    @api.depends(
        "state",
        "date_start",
        "move_raw_ids",
        "move_raw_ids.product_id",
        "move_raw_ids.state",
        "move_raw_ids.product_qty",
        "move_raw_ids.forecast_availability",
        "move_raw_ids.date_planned_forecast",
    )
    @api.depends_context("lang")
    def _compute_component_availability(self):
        productions = self.filtered(
            lambda mo: mo.state not in ("cancel", "done", "draft")
        )
        productions.components_availability_state = "available"
        productions.components_availability = _("Available")

        other_productions = self - productions
        other_productions.components_availability = False
        other_productions.components_availability_state = False

        all_raw_moves = productions.move_raw_ids
        all_raw_moves._fields["forecast_availability"].compute_value(all_raw_moves)
        for production in productions:
            if any(
                move.product_id
                and move.product_id.uom_id.compare(
                    move.forecast_availability,
                    0 if move.state == "draft" else move.product_qty,
                )
                == -1
                for move in production.move_raw_ids
            ):
                production.components_availability = _("Not Available")
                production.components_availability_state = "unavailable"
            else:
                forecast_date = max(
                    production.move_raw_ids.filtered("date_planned_forecast").mapped(
                        "date_planned_forecast"
                    ),
                    default=False,
                )
                if forecast_date:
                    production.components_availability = _(
                        "Exp %s", format_date(self.env, forecast_date)
                    )
                    if production.date_start:
                        production.components_availability_state = (
                            "late"
                            if forecast_date > production.date_start
                            else "expected"
                        )

    @api.depends("bom_id")
    def _compute_product_id(self):
        for production in self:
            bom = production.bom_id
            if bom and (
                not production.product_id
                or bom.product_tmpl_id != production.product_id.product_tmpl_id
                or (bom.product_id and bom.product_id != production.product_id)
            ):
                production.product_id = (
                    bom.product_id or bom.product_tmpl_id.product_variant_id
                )

    @api.depends(
        "product_id",
        "product_id.uom_id",
        "product_id.uom_ids",
        "product_id.bom_ids",
        "product_id.bom_ids.product_uom_id",
    )
    def _compute_allowed_uom_ids(self):
        for production in self:
            production.allowed_uom_ids = (
                production.product_id.uom_id
                | production.product_id.uom_ids
                | production.product_id.bom_ids.product_uom_id
            )

    @api.depends("product_id", "never_product_template_attribute_value_ids")
    def _compute_bom_id(self):
        mo_by_company_id = defaultdict(lambda: self.env["mrp.production"])
        for mo in self:
            if not mo.product_id and not mo.bom_id:
                mo.bom_id = False
                continue
            mo_by_company_id[mo.company_id.id] |= mo

        for company_id, productions in mo_by_company_id.items():
            picking_type_id = self.env.context.get("default_picking_type_id")
            picking_type = picking_type_id and self.env["stock.picking.type"].browse(
                picking_type_id
            )
            boms_by_product = (
                self.env["mrp.bom"]
                .with_context(active_test=True)
                ._get_bom_by_product(
                    productions.product_id,
                    picking_type=picking_type,
                    company_id=company_id,
                    bom_type="normal",
                )
            )
            for production in productions:
                if (
                    not production.bom_id
                    or production.bom_id.product_tmpl_id != production.product_tmpl_id
                    or (
                        production.bom_id.product_id
                        and production.bom_id.product_id != production.product_id
                    )
                ):
                    bom = boms_by_product[production.product_id]
                    _debug.logic(
                        "production_bom_resolved",
                        production=production.id,
                        product=production.product_id.id,
                        bom=bom.id or False,
                    )
                    production.bom_id = bom.id or False
                    self.env.add_to_compute(
                        production._fields["picking_type_id"], production
                    )

    @api.depends("bom_id")
    def _compute_product_qty(self):
        for production in self:
            if production.state != "draft":
                continue
            if production.bom_id and production._origin.bom_id != production.bom_id:
                production.product_qty = production.bom_id.product_qty
            elif not production.bom_id:
                production.product_qty = 1.0

    @api.depends(
        "product_id",
        "product_qty",
        "move_raw_ids",
        "move_raw_ids.product_id",
        "move_raw_ids.product_uom_id",
        "move_raw_ids.unit_factor",
    )
    def _compute_production_capacity(self):
        for production in self:
            production.production_capacity = production.product_qty
            moves = production.move_raw_ids.filtered(
                lambda move: move.unit_factor and move.product_id.is_storable
            )
            if moves:
                production_capacity = min(
                    moves.mapped(
                        lambda move: (
                            move.product_id.uom_id._get_quantity_estimate(
                                move.product_id.qty_available, move.product_uom_id
                            )
                            / move.unit_factor
                        )
                    )
                )
                production.production_capacity = min(
                    production.product_qty,
                    production.product_id.uom_id.round(production_capacity),
                )

    @api.depends("move_finished_ids.date_deadline")
    def _compute_date_deadline(self):
        for production in self:
            deadline = min(
                production.move_finished_ids.filtered("date_deadline").mapped(
                    "date_deadline"
                ),
                default=False,
            )
            if deadline:
                production.date_deadline = deadline

    @api.depends("workorder_ids.duration_expected")
    def _compute_duration_expected(self):
        for production in self:
            production.duration_expected = sum(
                production.workorder_ids.mapped("duration_expected")
            )

    @api.depends("workorder_ids.duration")
    def _compute_duration(self):
        for production in self:
            production.duration = sum(production.workorder_ids.mapped("duration"))

    @api.depends("workorder_ids.date_start", "workorder_ids.date_end", "date_start")
    def _compute_is_planned(self):
        for production in self:
            if production.workorder_ids:
                production.is_planned = any(
                    wo.date_start and wo.date_end for wo in production.workorder_ids
                )
            else:
                production.is_planned = False

    @api.depends("move_raw_ids.date_delay_alert")
    def _compute_date_delay_alert(self):
        saved = self.filtered("id")
        date_delay_alert_data = {}
        if saved:
            date_delay_alert_data = {
                production.id: date_delay_alert_max
                for production, date_delay_alert_max in self.env[
                    "stock.move"
                ]._read_group(
                    [
                        ("raw_material_production_id", "in", saved.ids),
                        ("date_delay_alert", "!=", False),
                        *_NON_INVENTORY_MOVE_DOMAIN,
                    ],
                    ["raw_material_production_id"],
                    ["date_delay_alert:max"],
                )
            }
        for production in self:
            if production.id:
                production.date_delay_alert = date_delay_alert_data.get(
                    production.id,
                    False,
                )
            else:
                production.date_delay_alert = max(
                    production.move_raw_ids.filtered("date_delay_alert").mapped(
                        "date_delay_alert"
                    ),
                    default=False,
                )

    @api.depends("state", "date_delay_alert", "move_raw_ids.date_delay_alert")
    @api.depends_context("lang")
    def _compute_json_popover(self):
        production_no_alert = self.filtered(
            lambda m: m.state in ("done", "cancel") or not m.date_delay_alert
        )
        production_no_alert.json_popover = False
        for production in self - production_no_alert:
            production.json_popover = json.dumps(
                {
                    "popoverTemplate": "stock.PopoverStockRescheduling",
                    "date_delay_alert": format_datetime(
                        self.env, production.date_delay_alert, dt_format=False
                    ),
                    "late_elements": [
                        {
                            "id": late_document.id,
                            "name": late_document.display_name,
                            "model": late_document._name,
                        }
                        for late_document in production.move_raw_ids.filtered(
                            lambda m: m.date_delay_alert
                        ).move_orig_ids._get_delay_alert_documents()
                    ],
                }
            )

    @api.depends("production_group_id.move_ids.picking_id")
    def _compute_picking_ids(self):
        move_per_production_group = self.env["stock.move"]._read_group(
            [("production_group_id", "in", self.production_group_id.ids)],
            ["production_group_id"],
            ["picking_id:recordset"],
        )
        move_per_production = dict(move_per_production_group)
        for order in self:
            order.picking_ids = move_per_production.get(
                order.production_group_id, False
            )

    @api.depends("product_uom_id", "product_qty", "product_id.uom_id")
    def _compute_product_uom_qty(self):
        for production in self:
            if production.product_id.uom_id != production.product_uom_id:
                production.product_uom_qty = (
                    production.product_uom_id._get_quantity_in_unit(
                        production.product_qty, production.product_id.uom_id
                    )
                )
            else:
                production.product_uom_qty = production.product_qty

    @api.depends("product_id", "company_id")
    def _compute_production_location_id(self):
        if not self.company_id:
            return
        location_by_company = self.env["stock.location"]._read_group(
            [("company_id", "in", self.company_id.ids), ("usage", "=", "production")],
            ["company_id"],
            ["id:array_agg"],
        )
        location_by_company = {company.id: ids for company, ids in location_by_company}
        for production in self:
            prod_loc = production.product_id.with_company(
                production.company_id
            ).property_stock_production
            comp_locs = location_by_company.get(production.company_id.id)
            production.production_location_id = prod_loc or (comp_locs and comp_locs[0])

    @api.depends("product_id.tracking")
    def _compute_show_final_lots(self):
        for production in self:
            production.show_final_lots = production.product_id.tracking != "none"

    def _inverse_finished_move_line_ids(self):
        pass

    @api.depends("move_finished_ids.move_line_ids")
    def _compute_finished_move_line_ids(self):
        for production in self:
            production.finished_move_line_ids = production.move_finished_ids.mapped(
                "move_line_ids"
            )

    @api.depends(
        "move_raw_ids.state",
        "move_raw_ids.quantity",
        "move_finished_ids.state",
        "workorder_ids.state",
        "product_qty",
        "qty_producing",
        "move_raw_ids.picked",
    )
    def _compute_state(self):
        for production in self:
            by = "stays_draft"  # debuglog
            if (
                not production.state
                or not production.product_uom_id
                or not (production.id or production._origin.id)
            ):
                by = "no_identity"  # debuglog
                production.state = "draft"
            elif production.state == "cancel" or (
                production.move_finished_ids
                and all(move.state == "cancel" for move in production.move_finished_ids)
            ):
                by = "all_finished_cancelled"  # debuglog
                production.state = "cancel"
            elif production.state == "done" or (
                (
                    production.move_raw_ids
                    and all(
                        move.state in ("cancel", "done")
                        for move in production.move_raw_ids
                    )
                )
                and all(
                    move.state in ("cancel", "done")
                    for move in production.move_finished_ids
                )
            ):
                by = "all_moves_closed"  # debuglog
                production.state = "done"
            elif (
                production.workorder_ids
                and all(
                    wo_state in ("done", "cancel")
                    for wo_state in production.workorder_ids.mapped("state")
                )
            ) or (
                not production.workorder_ids
                and production.product_uom_id.compare(
                    production.qty_producing, production.product_qty
                )
                >= 0
            ):
                by = "qty_reached_or_wo_closed"  # debuglog
                production.state = "to_close"
            elif (
                any(
                    wo_state in ("progress", "done")
                    for wo_state in production.workorder_ids.mapped("state")
                )
                or (
                    production.product_uom_id
                    and not production.product_uom_id.is_zero(production.qty_producing)
                )
                or any(production.move_raw_ids.mapped("picked"))
            ):
                by = "wo_started_or_qty_producing"  # debuglog
                production.state = "progress"
            elif production.state != "draft":
                by = "reopened_confirmed"  # debuglog
                production.state = "confirmed"
            _debug.logic(
                "production_state",
                production=production.id,
                state=production.state,
                by=by,
            )

    @api.depends(
        "bom_id",
        "product_id",
        "product_qty",
        "product_uom_id",
        "never_product_template_attribute_value_ids",
    )
    def _compute_workorder_ids(self):
        batch = self.with_context(
            bom_cost_share_cache=self.env["mrp.bom"]._get_explosion_scratch()
        )
        for production in batch:
            if production.state != "draft":
                continue
            workorders_list = [
                Command.link(wo.id)
                for wo in production.workorder_ids.filtered(lambda wo: wo.ids)
            ]
            relevant_boms = [
                exploded_boms[0]
                for exploded_boms in production.bom_id._explode(
                    production.product_id,
                    1.0,
                    picking_type=production.bom_id.picking_type_id,
                )[0]
            ]
            deleted_workorders_ids = production.workorder_ids.filtered(
                lambda wo, relevant_boms=relevant_boms: (
                    wo.operation_id and wo.operation_id.bom_id not in relevant_boms
                )
            ).mapped("id")
            workorders_list += [
                Command.delete(wo_id) for wo_id in deleted_workorders_ids
            ]
            if not production.bom_id and not production._origin.product_id:
                production.workorder_ids = workorders_list
            if (
                production.product_id != production._origin.product_id
                or (not production._origin.bom_id and production.bom_id)
                or (
                    production._origin.bom_id != production.bom_id
                    and production._origin.bom_id.operation_ids
                    and not production.workorder_ids.filtered(
                        lambda wo: wo.ids and wo.operation_id
                    )
                )
            ):
                production.workorder_ids = [Command.clear()]
            if (
                production.bom_id
                and production.product_id
                and production.product_qty > 0
            ):
                workorders_values = []
                product_qty = production.product_uom_id._get_quantity_in_unit(
                    production.product_qty, production.bom_id.product_uom_id
                )
                exploded_boms, _dummy = production.bom_id._explode(
                    production.product_id,
                    product_qty / production.bom_id.product_qty,
                    picking_type=production.bom_id.picking_type_id,
                    never_attribute_values=production.never_product_template_attribute_value_ids,
                )

                for bom, bom_data in exploded_boms:
                    if not (
                        bom.operation_ids
                        and (
                            not bom_data["parent_line"]
                            or bom_data["parent_line"].bom_id.operation_ids
                            != bom.operation_ids
                        )
                    ):
                        continue
                    for operation in bom.operation_ids:
                        if operation._is_bom_line_skipped(
                            bom_data["product"]
                            if not bom_data["parent_line"]
                            else bom_data["parent_line"]["product_id"],
                            production.never_product_template_attribute_value_ids,
                        ):
                            workorder = production.workorder_ids.filtered(
                                lambda wo, operation=operation, bom=bom: (
                                    wo.operation_id == operation
                                    and wo.operation_id.bom_id == bom
                                )
                            )
                            if workorder:
                                workorders_list += [Command.delete(workorder.id)]
                            continue
                        workorders_values += [
                            {
                                "name": operation.name,
                                "production_id": production.id,
                                "workcenter_id": operation.workcenter_id.id,
                                "product_uom_id": production.product_uom_id.id,
                                "operation_id": operation.id,
                                "state": "ready",
                            }
                        ]
                workorders_dict = {
                    wo.operation_id.id: wo
                    for wo in production.workorder_ids.filtered(
                        lambda wo, deleted_workorders_ids=deleted_workorders_ids: (
                            wo.operation_id and wo.id not in deleted_workorders_ids
                        )
                    )
                }
                for workorder_values in workorders_values:
                    if workorder_values["operation_id"] in workorders_dict:
                        workorders_list += [
                            Command.update(
                                workorders_dict[workorder_values["operation_id"]].id,
                                workorder_values,
                            )
                        ]
                    else:
                        workorders_list += [Command.create(workorder_values)]
                production.workorder_ids = workorders_list
            else:
                production.workorder_ids = [
                    Command.delete(wo_id)
                    for wo_id in production.workorder_ids.filtered(
                        lambda wo: wo.operation_id
                    ).mapped("id")
                ]

    @api.depends(
        "state",
        "move_raw_ids.state",
        "move_raw_ids.picked",
        "move_raw_ids.product_uom_qty",
        "bom_id.ready_to_produce",
        "workorder_ids.operation_id",
        "move_raw_ids.operation_id",
    )
    def _compute_reservation_state(self):
        for production in self:
            if production.state in ("draft", "done", "cancel"):
                production.reservation_state = False
                continue
            relevant_move_state = production.move_raw_ids.filtered(
                lambda m: (
                    m.product_id
                    and not (
                        m.picked
                        or m.product_uom_id.is_zero(
                            m.product_uom_qty,
                        )
                    )
                )
            )._get_relevant_state_among_moves()
            if relevant_move_state == "partially_available":
                if (
                    production.workorder_ids.operation_id
                    and production.bom_id.ready_to_produce == "asap"
                ):
                    production.reservation_state = (
                        production._get_ready_to_produce_state()
                    )
                else:
                    production.reservation_state = "confirmed"
            elif relevant_move_state != "draft":
                production.reservation_state = relevant_move_state
            else:
                production.reservation_state = False

    @api.depends(
        "move_raw_ids",
        "state",
        "move_raw_ids.product_uom_qty",
        "move_raw_ids.picked",
        "move_raw_ids.move_line_ids",
    )
    def _compute_reservation_visibility(self):
        for order in self:
            already_reserved = order.state not in ("done", "cancel") and order.mapped(
                "move_raw_ids.move_line_ids"
            )
            any_quantity_done = any(order.move_raw_ids.mapped("picked"))

            order.unreserve_visible = not any_quantity_done and already_reserved
            order.reserve_visible = order.state in (
                "confirmed",
                "progress",
                "to_close",
            ) and any(
                move.product_uom_qty
                and move.state in ["confirmed", "partially_available"]
                for move in order.move_raw_ids
            )

    @api.depends(
        "product_id",
        "move_finished_ids",
        "move_finished_ids.state",
        "move_finished_ids.product_id",
        "move_finished_ids.quantity",
        "move_finished_ids.picked",
    )
    def _compute_qty_produced(self):
        for production in self:
            done_moves = production.move_finished_ids.filtered(
                lambda x, production=production: (
                    x.state != "cancel" and x.product_id.id == production.product_id.id
                )
            )
            production.qty_produced = sum(
                done_moves.filtered(lambda m: m.picked).mapped("quantity")
            )

    @api.depends("scrap_ids")
    def _compute_scrap_count(self):
        data = self.env["stock.scrap"]._read_group(
            [("production_id", "in", self.ids)], ["production_id"], ["__count"]
        )
        count_data = {production.id: count for production, count in data}
        for production in self:
            production.scrap_count = count_data.get(production.id, 0)

    @api.depends("move_finished_ids")
    def _compute_move_byproduct_ids(self):
        for order in self:
            order.move_byproduct_ids = order.move_finished_ids.filtered(
                lambda m, order=order: m.product_id != order.product_id
            )

    def _inverse_move_byproduct_ids(self):
        move_finished_ids = self.move_finished_ids.filtered(
            lambda m: m.product_id == self.product_id
        )
        self.move_finished_ids = move_finished_ids | self.move_byproduct_ids

    @api.depends("state")
    @api.depends_context("uid")
    def _compute_show_lock(self):
        for order in self:
            order.show_lock = order.state == "done" or (
                not self.env.user.has_group("mrp.group_unlocked_by_default")
                and order.id
                and order.state not in {"cancel", "draft"}
            )

    @api.depends("state", "move_raw_ids", "move_raw_ids.product_id.tracking")
    def _compute_show_lot_ids(self):
        for order in self:
            order.show_lot_ids = order.state != "draft" and any(
                m.product_id.tracking != "none" for m in order.move_raw_ids
            )

    @api.depends(
        "state", "picking_type_id", "move_finished_ids", "move_finished_ids.product_id"
    )
    @api.depends_context("uid")
    def _compute_show_allocation(self):
        self.show_allocation = False
        if not self.env.user.has_group("mrp.group_mrp_reception_report"):
            return
        Move = self.env["stock.move"]
        lines_by_order = {}
        orders_by_scope = defaultdict(lambda: self.env["mrp.production"])
        for order in self:
            warehouse = order.picking_type_id.warehouse_id
            if not warehouse:
                continue
            lines = order.move_finished_ids.filtered(
                lambda m: m.product_id.is_storable and m.state != "cancel"
            )
            if not lines:
                continue
            lines_by_order[order.id] = lines
            allowed_states = ("confirmed", "partially_available", "waiting")
            if order.state == "done":
                allowed_states += ("assigned",)
            orders_by_scope[(warehouse, allowed_states)] |= order

        for (warehouse, allowed_states), orders in orders_by_scope.items():
            location_ids = self.env["stock.location"]._search(
                [
                    ("id", "child_of", warehouse.view_location_id.id),
                    ("usage", "!=", "supplier"),
                ]
            )
            batch_lines = Move.union(*(lines_by_order[order.id] for order in orders))
            scope = [
                ("state", "in", list(allowed_states)),
                ("product_qty", ">", 0),
                ("location_id", "in", location_ids),
                ("product_id", "in", batch_lines.product_id.ids),
            ]
            unchained_owners = defaultdict(set)
            for product, raw_production in Move._read_group(  # noqa: E8507 - one query per batch of orders
                [*scope, ("move_orig_ids", "=", False)],
                ["product_id", "raw_material_production_id"],
            ):
                unchained_owners[product].add(raw_production.id)
            chained = Move.search([*scope, ("move_orig_ids", "in", batch_lines.ids)])  # noqa: E8507 - one query per batch of orders

            for order in orders:
                lines = lines_by_order[order.id]
                if any(
                    unchained_owners[product] - {order.id}
                    for product in lines.product_id
                ):
                    order.show_allocation = True
                    continue
                order.show_allocation = any(
                    move.product_id in lines.product_id
                    and move.raw_material_production_id != order
                    and move.move_orig_ids & lines
                    for move in chained
                )

    @api.depends("product_uom_qty", "date_start", "product_id", "location_dest_id")
    def _compute_forecasted_issue(self):
        for order in self:
            warehouse = order.location_dest_id.warehouse_id
            order.forecasted_issue = False
            if order.product_id:
                qty_available_virtual = order.product_id.with_context(
                    warehouse_id=warehouse.id, to_date=order.date_start
                ).qty_available_virtual
                if order.state == "draft":
                    qty_available_virtual += order.product_uom_qty
                if qty_available_virtual < 0:
                    order.forecasted_issue = True

    @api.depends(
        "bom_id.produce_delay",
        "company_id",
        "date_start",
        "is_planned",
        "product_id",
        "workorder_ids.duration_expected",
    )
    def _compute_date_end(self):
        for production in self:
            if (
                not production.date_start
                or production.is_planned
                or production.state == "done"
            ):
                continue
            days_delay = production.bom_id.produce_delay
            date_end = production.date_start + relativedelta(days=days_delay)
            if production._is_date_end_postponement_required(date_end):
                date_end = production._get_date_end_expected(date_end) or (
                    date_end
                    + relativedelta(
                        minutes=sum(
                            production.workorder_ids.mapped("duration_expected")
                        )
                        or 60
                    )
                )
            production.date_end = date_end

    def _get_date_end_expected(self, date_start):
        if not isinstance(date_start, datetime.datetime) or not self.workorder_ids:
            return False

        date_finished_per_workcenter = defaultdict(lambda: date_start)
        for wo in self.workorder_ids:
            if not wo.workcenter_id.resource_calendar_id:
                return False
            wo_optimal_date_start = date_finished_per_workcenter[wo.workcenter_id.id]
            _dummy, to_date = wo.workcenter_id._get_first_available_slot(
                wo_optimal_date_start, wo.duration_expected
            )
            if not isinstance(to_date, datetime.datetime):
                return False
            date_finished_per_workcenter[wo.workcenter_id.id] = to_date
        return max(date_finished_per_workcenter.values())

    @api.depends(
        "company_id",
        "bom_id",
        "product_id",
        "product_qty",
        "product_uom_id",
        "location_src_id",
        "never_product_template_attribute_value_ids",
    )
    def _compute_move_raw_ids(self):
        batch = self.with_context(
            bom_cost_share_cache=self.env["mrp.bom"]._get_explosion_scratch()
        )
        deferred_move_vals = []
        for production in batch:
            if production.state != "draft" or self.env.context.get(
                "skip_compute_move_raw_ids"
            ):
                continue
            list_move_raw = [
                Command.link(move.id)
                for move in production.move_raw_ids.filtered(
                    lambda m: not m.bom_line_id
                )
            ]
            if not production.bom_id and not production._origin.product_id:
                production.move_raw_ids = list_move_raw
            if any(
                move.bom_line_id.bom_id != production.bom_id
                or move.bom_line_id._is_bom_line_skipped(
                    production.product_id,
                    production.never_product_template_attribute_value_ids,
                )
                for move in production.move_raw_ids
                if move.bom_line_id
            ):
                production.move_raw_ids = [Command.clear()]
            if (
                production.bom_id
                and production.product_id
                and production.product_qty > 0
            ):
                moves_raw_values = production._prepare_moves_raw_vals()
                move_raw_dict = {
                    move.bom_line_id.id: move
                    for move in production.move_raw_ids.filtered(
                        lambda m: m.bom_line_id
                    )
                }
                for move_raw_values in moves_raw_values:
                    if move_raw_values["bom_line_id"] in move_raw_dict:
                        list_move_raw += [
                            Command.update(
                                move_raw_dict[move_raw_values["bom_line_id"]].id,
                                move_raw_values,
                            )
                        ]
                    elif isinstance(production.id, int):
                        # The vals already carry `raw_material_production_id`,
                        # so the move can be created with every other
                        # production's in one call instead of being flushed by
                        # this record's own assignment. See
                        # `_create_deferred_moves`.
                        deferred_move_vals.append(move_raw_values)
                    else:
                        list_move_raw += [Command.create(move_raw_values)]
                production.move_raw_ids = list_move_raw
            else:
                production.move_raw_ids = [
                    Command.delete(move.id)
                    for move in production.move_raw_ids.filtered(
                        lambda m: m.bom_line_id
                    )
                ]
        self._create_deferred_moves(deferred_move_vals)

    def _create_deferred_moves(self, move_vals):
        """Create in one call the moves an x2many assignment would flush singly.

        `Command.create` inside `production.move_raw_ids = [...]` is written out
        by that assignment: the ORM folds each record's commands on its own and
        calls `stock.move.create()` once per record. Collecting the vals and
        creating them here costs one call for the whole batch, and the rows are
        identical -- they already carry the inverse, which is what the command
        would have set. Measured on 25 orders of three components: 50 calls to
        `stock.move.create()` became 2.

        Deferring is only possible for a production that already has a real id.
        A `NewId` parent -- a Form, an onchange -- keeps the command, because
        the inverse cannot be written before the parent exists.
        """
        if move_vals:
            self.env["stock.move"].create(move_vals)

    @api.depends(
        "product_id",
        "bom_id",
        "product_qty",
        "product_uom_id",
        "location_dest_id",
        "date_end",
        "move_dest_ids",
        "never_product_template_attribute_value_ids",
    )
    def _compute_move_finished_ids(self):
        production_with_move_finished_ids_to_unlink_ids = OrderedSet()
        ignored_mo_ids = self.env.context.get("ignore_mo_ids", [])
        for production in self:
            if production.id in ignored_mo_ids:
                continue
            if production.state != "draft":
                updated_values = {}
                if production.date_end:
                    updated_values["date"] = production.date_end
                if production.date_deadline:
                    updated_values["date_deadline"] = production.date_deadline
                if "date" in updated_values or "date_deadline" in updated_values:
                    production.move_finished_ids = [
                        Command.update(m.id, updated_values)
                        for m in production.move_finished_ids
                        if any(
                            updated_values.get(field)
                            and m[field] != updated_values[field]
                            for field in ("date", "date_deadline")
                        )
                    ]
                continue
            production_with_move_finished_ids_to_unlink_ids.add(production.id)

        production_with_move_finished_ids_to_unlink = self.browse(
            production_with_move_finished_ids_to_unlink_ids
        )

        production_with_move_finished_ids_to_unlink.move_finished_ids = [
            Command.delete(m)
            for m in production_with_move_finished_ids_to_unlink.move_finished_ids.ids
        ]
        production_with_move_finished_ids_to_unlink.move_finished_ids = [
            Command.clear()
        ]

        deferred_move_vals = []
        for production in production_with_move_finished_ids_to_unlink:
            if production.product_id:
                production._create_update_move_finished(deferred_move_vals)
            else:
                production.move_finished_ids = [
                    Command.delete(move.id)
                    for move in production.move_finished_ids
                    if move.bom_line_id
                ]
        self._create_deferred_moves(deferred_move_vals)

    @api.depends("bom_id", "product_id", "move_raw_ids.product_id", "workorder_ids")
    def _compute_show_generate_bom(self):
        for production in self:
            production.show_generate_bom = (
                not production.bom_id
                and production.product_id
                and (
                    (
                        production.move_raw_ids
                        and production.product_id
                        not in production.move_raw_ids.product_id
                    )
                    or (not production.move_raw_ids and production.workorder_ids)
                )
            )

    @api.depends("state", "product_qty", "qty_producing")
    def _compute_produce_visibility(self):
        for production in self:
            state_ok = production.state in ("confirmed", "progress", "to_close")
            qty_none_or_all = production.qty_producing in (0, production.product_qty)
            production.show_produce_all = state_ok and qty_none_or_all
            production.show_produce = state_ok and not qty_none_or_all

    def _search_is_delayed(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        delayed_productions = Domain(
            [
                ("state", "in", ["confirmed", "progress", "to_close"]),
                ("date_deadline", "!=", False),
            ]
        ) & (
            Domain.custom(
                to_sql=lambda model, alias, query: SQL(
                    "%s < %s",
                    SQL.identifier(alias, "date_deadline"),
                    SQL.identifier(alias, "date_end"),
                )
            )
            | Domain("date_deadline", "<", fields.Datetime.now())
        )
        return [("id", operator, delayed_productions)]

    @api.depends("state", "date_deadline", "date_end")
    def _compute_is_delayed(self):
        for record in self:
            record.is_delayed = bool(
                record.state in ["confirmed", "progress", "to_close"]
                and (
                    record.date_deadline
                    and (
                        record.date_deadline < datetime.datetime.now()
                        or record.date_deadline < record.date_end
                    )
                )
            )

    def _search_date_category(self, operator, value):
        if operator != "in":
            return NotImplemented
        dates = value
        return Domain.OR(
            self.get_domain_date_category("date_start", date) for date in dates
        )

    @api.depends("lot_producing_ids", "product_tracking")
    def _compute_serial_numbers_count(self):
        for production in self:
            if production.product_tracking != "serial":
                production.serial_numbers_count = 0
                continue
            production.serial_numbers_count = len(production.lot_producing_ids)

    def _update_qty_producing(self):
        if self.state in ["draft", "cancel"] or (
            self.state == "done" and self.is_locked
        ):
            return False
        if self.product_tracking == "serial" and self.lot_producing_ids:
            self.qty_producing = len(self.lot_producing_ids)
        productions_bypass_qty_producting = self.filtered(
            lambda p: (
                p.lot_producing_ids
                and p.product_tracking == "lot"
                and p._origin
                and p._origin.qty_producing == p.qty_producing
            )
        )
        (
            self - productions_bypass_qty_producting
        ).sudo()._update_moves_from_qty_producing(False)
        return True

    @api.onchange("qty_producing")
    def _onchange_qty_producing(self):
        self._update_qty_producing()

    @api.onchange("lot_producing_ids")
    def _onchange_lot_producing(self):
        if self._update_qty_producing():
            return self._get_serial_numbers_warning()
        return None

    def _get_serial_numbers_warning(self, sns=None):
        self.check_singleton()
        sns = sns or self.lot_producing_ids
        if self.product_id.tracking == "serial" and sns:
            messages = []
            for sn in sns:
                message, _dummy = (
                    self.env["stock.quant"]
                    .sudo()
                    ._get_serial_number_warning(self.product_id, sn, self.company_id)
                )
                if message:
                    messages.append(message)
            if messages:
                return {
                    "warning": {"title": _("Warning"), "message": ",".join(messages)}
                }
        return None

    @api.constrains("move_finished_ids")
    def _check_byproducts(self):
        for order in self:
            if any(move.cost_share < 0 for move in order.move_byproduct_ids):
                raise ValidationError(_("By-products cost shares must be positive."))
            if (
                sum(
                    order.move_byproduct_ids.filtered(
                        lambda m: m.state != "cancel"
                    ).mapped("cost_share")
                )
                > 100
            ):
                raise ValidationError(
                    _(
                        "The total cost share for a manufacturing order's by-products cannot exceed 100."
                    )
                )

    @api.constrains("lot_producing_ids")
    def _check_lot_producing_ids(self):
        for record in self:
            if record.product_tracking == "lot" and len(record.lot_producing_ids) > 1:
                raise UserError(_("You cannot set more than 1 lot"))

    @api.constrains("production_group_id", "company_id")
    def _check_production_group_company(self):
        for group in self.production_group_id:
            if len(group.production_ids.company_id) > 1:
                raise ValidationError(
                    _(
                        "All the manufacturing orders of a production group "
                        "must belong to the same company."
                    )
                )

    def write(self, vals):
        vals = self._prepare_write_vals(dict(vals))
        if "product_id" in vals:
            editable = self.filtered(lambda production: production.state == "draft")
            if editable and editable != self:
                _debug.logic(
                    "production_write_split",
                    reason="product_id_on_non_draft",
                    productions=self,
                    editable=editable,
                )
                frozen = {k: v for k, v in vals.items() if k != "product_id"}
                result = editable.write(vals)
                if frozen:
                    result = (self - editable).write(frozen) and result
                return result
            if not editable:
                _debug.logic(
                    "production_write_dropped",
                    field="product_id",
                    reason="no_draft_order",
                    productions=self,
                )
                del vals["product_id"]
        move_keys = [
            key for key in ("move_raw_ids", "move_finished_ids") if key in vals
        ]
        if len(self) > 1 and move_keys and not vals.get("location_src_id"):
            by_warehouse = self.grouped(
                lambda production: production.location_src_id.warehouse_id
            )
            if len(by_warehouse) > 1:
                _debug.logic(
                    "production_write_split",
                    reason="moves_across_warehouses",
                    productions=self,
                    warehouses=len(by_warehouse),
                )
                result = True
                for group in by_warehouse.values():
                    result = group.write(vals) and result
                return result

        self._check_write_preconditions(vals)
        production_to_replan = self.filtered(lambda p: p.is_planned)
        self._update_move_warehouse_vals(vals, move_keys)
        moves_to_reassign = self._pre_write_picking_type(vals)

        res = super().write(vals)

        _debug.lifecycle(
            "write",
            productions=self,
            fields=list(vals),
            to_replan=len(production_to_replan),
            to_reassign=len(moves_to_reassign),
        )
        self._post_write(vals, production_to_replan)
        self._post_write_reassign(moves_to_reassign)
        return res

    def _check_write_preconditions(self, vals):
        if "date_start" not in vals or self.env.context.get("force_date", False):
            return
        if any(production.state in ("done", "cancel") for production in self):
            _debug.logic(
                "production_refused", reason="date_start_on_closed", productions=self
            )
            raise UserError(
                _("You cannot move a manufacturing order once it is cancelled or done.")
            )

    def _prepare_write_vals(self, vals):
        return self._merge_byproduct_commands(
            vals, self._get_main_product_id_from_vals(vals)
        )

    def _get_main_product_id_from_vals(self, vals):
        if vals.get("product_id"):
            return vals["product_id"]
        if len(self.product_id) == 1:
            return self.product_id.id
        if vals.get("bom_id"):
            bom = self.env["mrp.bom"].browse(vals["bom_id"])
            return (bom.product_id or bom.product_tmpl_id.product_variant_id).id
        return False

    @api.model
    def _merge_byproduct_commands(self, vals, main_product_id=False):
        if "move_byproduct_ids" not in vals:
            return vals
        byproduct_commands = vals.pop("move_byproduct_ids")
        finished_commands = vals.get("move_finished_ids") or []
        if main_product_id:

            def is_main(command):
                return command[2].get("product_id") == main_product_id
        else:
            byproduct_product_ids = {
                command[2].get("product_id")
                for command in byproduct_commands
                if command[0] == Command.CREATE and command[2].get("product_id")
            }

            def is_main(command):
                return command[2].get("product_id") not in byproduct_product_ids

        vals["move_finished_ids"] = [
            command
            for command in finished_commands
            if command[0] != Command.CREATE or is_main(command)
        ] + byproduct_commands
        return vals

    def _update_move_warehouse_vals(self, vals, move_keys):
        if not move_keys:
            return
        if any(production.state in ("cancel", "done") for production in self):
            return
        warehouse_id = self.location_src_id.warehouse_id.id
        if vals.get("location_src_id"):
            location_source = self.env["stock.location"].browse(vals["location_src_id"])
            warehouse_id = location_source.warehouse_id.id
        for move_str in move_keys:
            stamped_commands = []
            for move_vals in vals[move_str]:
                if move_vals[0] != Command.CREATE:
                    stamped_commands.append(move_vals)
                    continue
                command, command_id, field_values = move_vals
                if not field_values.get("warehouse_id"):
                    field_values = {**field_values, "warehouse_id": warehouse_id}
                stamped_commands.append((command, command_id, field_values))
            vals[move_str] = stamped_commands

    def _pre_write_picking_type(self, vals):
        if not vals.get("picking_type_id"):
            return self.env["stock.move"]
        picking_type = self.env["stock.picking.type"].browse(vals["picking_type_id"])
        moves_to_reassign = self.env["stock.move"]
        for production in self:
            if production.state in ("cancel", "done"):
                continue
            if picking_type == production.picking_type_id:
                continue
            previous_name = production.name
            production.name = picking_type.sequence_id.next_by_id()
            production.move_raw_ids.reference_ids.filtered(
                lambda r, previous_name=previous_name: r.name == previous_name
            ).name = production.name
            moves_to_reassign |= production.move_raw_ids
        return moves_to_reassign

    def _post_write(self, vals, production_to_replan):
        if "date_start" in vals and not self.env.context.get("force_date", False):
            production_to_replan.button_unplan()
        if vals.get("date_start"):
            date_start = self[:1].date_start
            self.move_raw_ids.write({"date": date_start, "date_deadline": date_start})
        if vals.get("date_end"):
            self.move_finished_ids.write({"date": self[:1].date_end})
        if any(
            field in ("move_raw_ids", "move_finished_ids", "workorder_ids")
            for field in vals
        ):
            open_orders = self.filtered(lambda p: p.state != "draft")
            _debug.pipeline(
                "production_moves_rewritten",
                productions=self,
                open_orders=len(open_orders),
                replan=len(open_orders & production_to_replan),
            )
            if open_orders:
                open_orders.with_context(
                    no_procurement=True
                )._confirm_draft_moves_and_workorders()
                for production in open_orders & production_to_replan:
                    production._plan_workorders()
        for production in self:
            production._post_write_one(vals)

    def _post_write_one(self, vals):
        self.check_singleton()
        if self.state == "done" and "qty_producing" in vals:
            self.move_finished_ids.filtered(
                lambda move: move.product_id == self.product_id and move.state == "done"
            ).quantity = vals["qty_producing"]
        if (
            self._has_workorders()
            and not self.workorder_ids.operation_id
            and vals.get("date_start")
            and not vals.get("date_end")
        ):
            new_date_start = fields.Datetime.to_datetime(vals["date_start"])
            if not self.date_end or new_date_start >= self.date_end:
                self.date_end = new_date_start + datetime.timedelta(hours=1)

    def _post_write_reassign(self, moves_to_reassign):
        if not moves_to_reassign:
            return
        moves_to_reassign._unreserve()
        moves_to_reassign._filtered_to_assign_at_confirm()._action_assign()

    @api.model_create_multi
    def create(self, vals_list):
        default_picking_type_by_company = {}
        vals_needing_group = []
        for vals in vals_list:
            if vals.get("move_byproduct_ids") and vals.get("move_finished_ids"):
                self._merge_byproduct_commands(vals, vals.get("product_id"))
            if not vals.get("name", False) or vals["name"] == _("New"):
                picking_type_id = vals.get("picking_type_id")
                if not picking_type_id:
                    company_id = vals.get("company_id", self.env.company.id)
                    if company_id not in default_picking_type_by_company:
                        default_picking_type_by_company[company_id] = (
                            self._get_default_picking_type_id(company_id)
                        )
                    picking_type_id = default_picking_type_by_company[company_id]
                    vals["picking_type_id"] = picking_type_id
                vals["name"] = (
                    self.env["stock.picking.type"]
                    .browse(picking_type_id)
                    .sequence_id.next_by_id()
                )
            if not vals.get("production_group_id"):
                vals_needing_group.append(vals)
        if vals_needing_group:
            groups = self.env["mrp.production.group"].create(
                [{"name": vals["name"]} for vals in vals_needing_group]
            )
            for vals, group in zip(vals_needing_group, groups, strict=True):
                vals["production_group_id"] = group.id
        res = super().create(vals_list)
        _debug.lifecycle(
            "create",
            count=len(res),
            productions=res,
            new_groups=len(vals_needing_group),
        )
        reference_vals_list = []
        # One write per distinct value rather than one per order: a procurement
        # run creates orders that share a start date, and the moves the compute
        # built already carry their production's group, so the regrouping set is
        # usually empty.
        moves_by_group = defaultdict(lambda: self.env["stock.move"])
        raw_moves_by_date = defaultdict(lambda: self.env["stock.move"])
        finished_moves_by_date = defaultdict(lambda: self.env["stock.move"])
        for rec, vals in zip(res, vals_list, strict=True):
            if vals.get("move_dest_ids"):
                rec.move_finished_ids.move_dest_ids = vals.get("move_dest_ids")
            regrouped = (rec.move_raw_ids | rec.move_finished_ids).filtered(
                lambda move, group=rec.production_group_id: (
                    move.production_group_id != group
                )
            )
            if regrouped:
                moves_by_group[rec.production_group_id.id] |= regrouped
            if not rec.reference_ids:
                reference_vals_list.append(
                    {
                        "name": rec.name,
                        "production_ids": [Command.set(rec.ids)],
                        "move_ids": [
                            Command.set(
                                rec.move_raw_ids.ids + rec.move_finished_ids.ids
                            )
                        ],
                    }
                )
            if (
                rec.move_raw_ids
                and rec.move_raw_ids[0].date
                and vals.get("date_start")
                and rec.move_raw_ids[0].date != vals["date_start"]
            ):
                raw_moves_by_date[vals["date_start"]] |= rec.move_raw_ids
            if (
                rec.move_finished_ids
                and rec.move_finished_ids[0].date
                and vals.get("date_end")
                and rec.move_finished_ids[0].date != vals["date_end"]
            ):
                finished_moves_by_date[vals["date_end"]] |= rec.move_finished_ids
            elif (
                rec.move_finished_ids
                and rec.date_end
                and rec.move_finished_ids[0].date != rec.date_end
                and not vals.get("date_end")
            ):
                finished_moves_by_date[rec.date_end] |= rec.move_finished_ids
        for group_id, moves in moves_by_group.items():
            moves.production_group_id = group_id
        for date, moves in raw_moves_by_date.items():
            moves.write({"date": date, "date_deadline": date})
        for date, moves in finished_moves_by_date.items():
            moves.write({"date": date})
        if reference_vals_list:
            _debug.lifecycle("references_created", count=len(reference_vals_list))
            self.env["stock.reference"].sudo().create(reference_vals_list)
        return res

    def unlink(self):
        self.action_cancel()
        workorders_to_delete = self.workorder_ids.filtered(
            lambda wo: wo.state != "done"
        )
        _debug.lifecycle(
            "unlink", productions=self, workorders=len(workorders_to_delete)
        )
        if workorders_to_delete:
            workorders_to_delete.unlink()
        return super().unlink()

    @api.ondelete(at_uninstall=True)
    def _unlink_except_done_at_uninstall(self):
        if any(mo.state == "done" for mo in self):
            _debug.logic("production_refused", reason="unlink_done", productions=self)
            raise UserError(
                _("You cannot delete a manufacturing order that is already done.")
            )

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for production, vals in zip(self, vals_list, strict=True):
            if not default or "move_finished_ids" not in default:
                move_finished_ids = production.move_finished_ids
                if production.state != "cancel":
                    move_finished_ids = production.move_finished_ids.filtered(
                        lambda m: m.state != "cancel" and m.product_qty
                    )
                vals["move_finished_ids"] = [
                    (0, 0, move_vals) for move_vals in move_finished_ids.copy_data()
                ]
            if not default or "move_raw_ids" not in default:
                vals["move_raw_ids"] = [
                    (0, 0, move_vals)
                    for move_vals in production.move_raw_ids.filtered(
                        lambda m: m.product_qty
                    ).copy_data()
                ]
        return vals_list

    def action_generate_bom(self):
        self.check_singleton()
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "mrp.mrp_bom_form_action"
        )
        action["view_mode"] = "form"
        action["views"] = [(False, "form")]

        bom_lines_vals, byproduct_vals, operations_vals = self._prepare_bom_commands()
        action["context"] = {
            "default_bom_line_ids": bom_lines_vals,
            "default_byproduct_ids": byproduct_vals,
            "default_code": _("New BoM from %(mo_name)s", mo_name=self.display_name),
            "default_company_id": self.company_id.id,
            "default_operation_ids": operations_vals,
            "default_product_id": self.product_id.id,
            "default_product_qty": self.product_qty,
            "default_product_tmpl_id": self.product_id.product_tmpl_id.id,
            "default_product_uom_id": self.product_uom_id.id,
            "parent_production_id": self.id,
        }
        return action

    def action_view_mo_delivery(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.action_picking_tree_all"
        )
        if len(self.picking_ids) > 1:
            action["domain"] = [("id", "in", self.picking_ids.ids)]
        elif self.picking_ids:
            action["res_id"] = self.picking_ids.id
            picking_form = self.env.ref("stock.view_stock_picking_form", False)
            picking_form_view = [((picking_form and picking_form.id) or False, "form")]
            action["views"] = picking_form_view + [
                (state, view)
                for state, view in action.get("views", [])
                if view != "form"
            ]
        action["context"] = dict(self.env.context, default_origin=self.name)
        return action

    def action_toggle_is_locked(self):
        self.check_singleton()
        self.is_locked = not self.is_locked
        return True

    def action_product_forecast_report(self):
        self.check_singleton()
        action = self.product_id.action_product_forecast_report()
        action["context"] = {
            "active_id": self.product_id.id,
            "active_model": "product.product",
            "move_to_match_ids": self.move_finished_ids.filtered(
                lambda m: m.product_id == self.product_id
            ).ids,
        }
        warehouse = self.picking_type_id.warehouse_id
        if warehouse:
            action["context"]["warehouse_id"] = warehouse.id
        return action

    def action_update_bom(self):
        for production in self:
            if production.bom_id:
                production._link_bom(production.bom_id)
        self.is_outdated_bom = False

    def _prepare_bom_commands(self, ratio=1):
        self.check_singleton()

        def get_uom_and_quantity(move):
            target_uom = (
                move.bom_line_id or move.byproduct_id
            ).product_uom_id or move.product_uom_id
            qty = move.quantity or move.product_uom_qty
            qty = move.product_uom_id._get_quantity_in_unit(qty * ratio, target_uom)
            return (target_uom, qty)

        bom_lines_values = []
        for move_raw in self.move_raw_ids:
            uom, qty = get_uom_and_quantity(move_raw)
            bom_line_vals = {
                "product_id": move_raw.product_id.id,
                "product_qty": qty,
                "product_uom_id": uom.id,
            }
            bom_lines_values.append(Command.create(bom_line_vals))
        byproduct_values = []
        for move_byproduct in self.move_byproduct_ids:
            uom, qty = get_uom_and_quantity(move_byproduct)
            bom_byproduct_vals = {
                "cost_share": move_byproduct.cost_share,
                "product_id": move_byproduct.product_id.id,
                "product_qty": qty,
                "product_uom_id": uom.id,
            }
            byproduct_values.append(Command.create(bom_byproduct_vals))
        operations_values = [
            Command.create(wo._prepare_operation_vals()) for wo in self.workorder_ids
        ]
        return (bom_lines_values, byproduct_values, operations_values)

    @api.model
    def _get_default_picking_type_id(self, company_id):
        return (
            self.env["stock.picking.type"]
            .search(
                [
                    ("code", "=", "mrp_operation"),
                    ("warehouse_id.company_id", "=", company_id),
                ],
                limit=1,
            )
            .id
        )

    def _prepare_move_finished_vals(
        self,
        product_id,
        product_uom_qty,
        product_uom_id,
        operation_id=False,
        byproduct_id=False,
        cost_share=0,
    ):
        move_dest_ids = (
            self.env["stock.move"]
            if byproduct_id
            else self._get_finished_move_dest_ids()
        )
        return {
            "product_id": product_id,
            "product_uom_qty": product_uom_qty,
            "product_uom_id": product_uom_id,
            "operation_id": operation_id,
            "byproduct_id": byproduct_id,
            "date": self.date_end,
            "date_deadline": self.date_deadline,
            "picking_type_id": self.picking_type_id.id,
            "location_id": self.production_location_id.id,
            "location_dest_id": self.location_dest_id.id,
            "company_id": self.company_id.id,
            "production_id": self.id,
            "warehouse_id": self.location_dest_id.warehouse_id.id,
            "origin": self.product_id.partner_ref,
            "reference_ids": self.reference_ids.ids,
            "propagate_cancel": self.propagate_cancel,
            "move_dest_ids": (
                [Command.set(move_dest_ids.ids)] if not byproduct_id else []
            ),
            "cost_share": cost_share,
            "production_group_id": self.production_group_id.id,
        }

    def _get_finished_move_dest_ids(self):
        self.check_singleton()
        if self.move_dest_ids:
            return self.move_dest_ids
        group_orders = (
            self.reference_ids.production_ids.production_group_id.production_ids
        ).filtered(
            lambda production: (
                production.production_group_id.parent_ids
                == self.production_group_id.parent_ids
            )
        )
        return group_orders.move_finished_ids.filtered(
            lambda move: move.product_id == self.product_id
        ).move_dest_ids

    def _prepare_moves_finished_vals(self):
        moves = []
        for production in self:
            if production.product_id in production.bom_id.byproduct_ids.mapped(
                "product_id"
            ):
                raise UserError(
                    _(
                        "You cannot have %s as the finished product and in the Byproducts",
                        production.product_id.name,
                    )
                )
            finished_move_values = production._prepare_move_finished_vals(
                production.product_id.id,
                production.product_qty,
                production.product_uom_id.id,
            )
            finished_move_values["location_final_id"] = production.location_final_id.id
            moves.append(finished_move_values)
            for byproduct in production.bom_id.byproduct_ids:
                if byproduct._is_bom_line_skipped(
                    production.product_id,
                    production.never_product_template_attribute_value_ids,
                ):
                    continue
                product_uom_factor = production.product_uom_id._get_quantity_in_unit(
                    production.product_qty, production.bom_id.product_uom_id
                )
                qty = byproduct.product_qty * (
                    product_uom_factor / production.bom_id.product_qty
                )
                moves.append(
                    production._prepare_move_finished_vals(
                        byproduct.product_id.id,
                        qty,
                        byproduct.product_uom_id.id,
                        byproduct.operation_id.id,
                        byproduct.id,
                        byproduct.cost_share,
                    )
                )
        return moves

    def _create_update_move_finished(self, deferred_move_vals=None):
        list_move_finished = []
        moves_finished_values = self._prepare_moves_finished_vals()
        moves_byproduct_dict = {
            move.byproduct_id.id: move
            for move in self.move_finished_ids.filtered(lambda m: m.byproduct_id)
        }
        move_finished = self.move_finished_ids.filtered(
            lambda m: m.product_id == self.product_id
        )
        for move_finished_values in moves_finished_values:
            if move_finished_values.get("byproduct_id") in moves_byproduct_dict:
                list_move_finished += [
                    Command.update(
                        moves_byproduct_dict[move_finished_values["byproduct_id"]].id,
                        move_finished_values,
                    )
                ]
            elif (
                move_finished_values.get("product_id") == self.product_id.id
                and move_finished
            ):
                list_move_finished += [
                    Command.update(move_finished.id, move_finished_values)
                ]
            elif deferred_move_vals is not None and isinstance(self.id, int):
                # See `_create_deferred_moves`: the vals already carry
                # `production_id`, so the row can be created with the rest of
                # the batch instead of being flushed by this assignment.
                deferred_move_vals.append(move_finished_values)
            else:
                list_move_finished += [Command.create(move_finished_values)]
        self.move_finished_ids = list_move_finished

    def _prepare_moves_raw_vals(self):
        moves = []
        batch = self.with_context(
            bom_cost_share_cache=self.env["mrp.bom"]._get_explosion_scratch()
        )
        for production in batch:
            if not production.bom_id:
                continue
            factor = (
                production.product_uom_id._get_quantity_in_unit(
                    production.product_qty,
                    production.bom_id.product_uom_id,
                    round=False,
                )
                / production.bom_id.product_qty
            )
            _boms, lines = production.bom_id._explode(
                production.product_id,
                factor,
                picking_type=production.bom_id.picking_type_id,
                never_attribute_values=production.never_product_template_attribute_value_ids,
            )
            for bom_line, line_data in lines:
                if (
                    bom_line.child_bom_id and bom_line.child_bom_id.type == "phantom"
                ) or bom_line.product_id.type != "consu":
                    continue
                operation = bom_line.operation_id.id or (
                    line_data["parent_line"]
                    and line_data["parent_line"].operation_id.id
                )
                moves.append(
                    production._prepare_move_raw_vals(
                        bom_line.product_id,
                        line_data["qty"],
                        bom_line.product_uom_id,
                        operation,
                        bom_line,
                    )
                )
        return moves

    def _prepare_move_raw_vals(
        self,
        product,
        product_uom_qty,
        product_uom_id,
        operation_id=False,
        bom_line=False,
    ):
        source_location = self.location_src_id
        return {
            "sequence": bom_line.sequence if bom_line else 10,
            "date": self.date_start,
            "date_deadline": self.date_start,
            "bom_line_id": bom_line.id if bom_line else False,
            "picking_type_id": self.picking_type_id.id,
            "product_id": product.id,
            "product_uom_qty": product_uom_qty,
            "product_uom_id": product_uom_id.id,
            "location_id": source_location.id,
            "location_dest_id": self.production_location_id.id,
            "raw_material_production_id": self.id,
            "production_group_id": self.production_group_id.id,
            "company_id": self.company_id.id,
            "operation_id": operation_id,
            "procure_method": "make_to_stock",
            "origin": self._get_origin(),
            "state": "draft",
            "warehouse_id": source_location.warehouse_id.id,
            "reference_ids": self.reference_ids.ids,
            "propagate_cancel": self.propagate_cancel,
            "manual_consumption": self.env[
                "stock.move"
            ]._is_manual_consumption_from_bom_line(bom_line),
        }

    def _get_origin(self):
        origin = self.name
        if self.orderpoint_id and self.origin:
            origin = self.origin
            origin = "%s,%s" % (origin, self.name)
        return origin

    def _mark_byproducts_as_produced(self):
        self.move_byproduct_ids.picked = True

    def _update_moves_from_qty_producing(self, pick_manual_consumption_moves=True):
        if self.product_id.tracking == "serial":
            qty_producing_uom = self.product_uom_id._get_quantity_in_unit(
                self.qty_producing, self.product_id.uom_id, rounding_method="HALF-UP"
            )
            qty_production_uom = self.product_uom_id._get_quantity_in_unit(
                self.product_qty, self.product_id.uom_id, rounding_method="HALF-UP"
            )
            if qty_producing_uom != qty_production_uom and not (
                qty_producing_uom == 0
                and self._origin.qty_producing != self.qty_producing
            ):
                self.qty_producing = self.product_id.uom_id._get_quantity_in_unit(
                    len(self.lot_producing_ids),
                    self.product_uom_id,
                    rounding_method="HALF-UP",
                )

        for move in self.move_raw_ids | self.move_finished_ids.filtered(
            lambda m: (
                m.product_id != self.product_id or m.product_id.tracking == "serial"
            )
        ):
            is_byproduct = move in self.move_byproduct_ids
            if move.picked and (is_byproduct or move.manual_consumption):
                continue

            if move.sudo()._is_qty_producing_bypass_required():
                continue

            new_qty = move._get_qty_to_process()
            if move.has_tracking != "none":
                qty_waiting = 0
                for move_orig in move.move_orig_ids:
                    if move_orig.state not in ("draft", "done", "cancel"):
                        qty_waiting += move_orig.product_uom_id._get_quantity_in_unit(
                            move_orig.quantity, move.product_uom_id
                        )
                if not move.product_uom_id.is_zero(qty_waiting):
                    new_qty = min(new_qty, move.product_uom_qty - qty_waiting)
            move._update_quantity_done(new_qty)
            if (
                (not move.manual_consumption or pick_manual_consumption_moves)
                and move.quantity
                and not is_byproduct
                and (
                    move.raw_material_production_id
                    or move.product_id.tracking != "serial"
                )
            ):
                move.picked = True

    def _is_date_end_postponement_required(self, date_end):
        self.check_singleton()
        return date_end == self.date_start

    def _update_raw_moves(self, factor):
        self.check_singleton()
        update_info = []
        moves_to_reference = self.env["stock.move"]
        for move in self.move_raw_ids.filtered(
            lambda m: m.state not in ("done", "cancel")
        ):
            old_qty = move.product_uom_qty
            new_qty = move.product_uom_id.round(old_qty * factor, rounding_method="UP")
            if new_qty > 0:
                move.write({"product_uom_qty": new_qty})
                update_info.append((move, old_qty, new_qty))
            if move.reference_ids != self.reference_ids:
                moves_to_reference |= move
        # The references are the production's own, so every move that needs them
        # needs the same ones: one relational write, not one per move.
        if moves_to_reference:
            moves_to_reference.reference_ids = self.reference_ids.ids
        _debug.pipeline(
            "raw_moves_rescaled",
            production=self.id,
            factor=factor,
            updated=len(update_info),
        )
        return update_info

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done(self):
        if any(production.state == "done" for production in self):
            _debug.logic("production_refused", reason="delete_done", productions=self)
            raise UserError(_("Cannot delete a manufacturing order in done state."))
        not_cancel = self.filtered(lambda m: m.state != "cancel")
        if not_cancel:
            _debug.logic(
                "production_refused",
                reason="delete_not_cancelled",
                productions=not_cancel,
            )
            productions_name = ", ".join([prod.display_name for prod in not_cancel])
            raise UserError(
                _("%s cannot be deleted. Try to cancel them before.", productions_name)
            )

    def _get_ready_to_produce_state(self):
        self.check_singleton()
        operations = self.workorder_ids.operation_id
        if len(operations) == 1:
            moves_in_first_operation = self.move_raw_ids
        else:
            first_operation = operations[0]
            moves_in_first_operation = self.move_raw_ids.filtered(
                lambda move: move.operation_id == first_operation
            )
        moves_in_first_operation = moves_in_first_operation.filtered(
            lambda move: (
                move.bom_line_id
                and not move.bom_line_id._is_bom_line_skipped(
                    self.product_id, self.never_product_template_attribute_value_ids
                )
            )
        )

        if all(move.state == "assigned" for move in moves_in_first_operation):
            _debug.logic(
                "ready_state",
                production=self.id,
                state="assigned",
                first_operation_moves=len(moves_in_first_operation),
            )
            return "assigned"
        _debug.logic(
            "ready_state",
            production=self.id,
            state="confirmed",
            first_operation_moves=len(moves_in_first_operation),
        )
        return "confirmed"

    def _confirm_draft_moves_and_workorders(self):
        open_productions = self.filtered(
            lambda production: production.state not in ("done", "cancel")
        )
        additional_moves = open_productions.move_raw_ids.filtered(
            lambda move: move.state == "draft"
        )
        additional_moves._update_procure_method()
        moves_to_confirm = (
            additional_moves
            | open_productions.move_finished_ids.filtered(
                lambda move: move.state == "draft"
            )
        )

        _debug.pipeline(
            "draft_moves_confirmed",
            productions=self,
            open_orders=len(open_productions),
            moves=len(moves_to_confirm),
        )
        if moves_to_confirm:
            moves_to_confirm = moves_to_confirm._action_confirm()
            moves_to_confirm._trigger_scheduler()

        self.workorder_ids.filtered(
            lambda w: w.state not in ["done", "cancel"]
        )._action_confirm()

    def _get_children(self):
        self.check_singleton()
        return self.production_group_id.child_ids.production_ids

    def _get_sources(self):
        self.check_singleton()
        return self.production_group_id.parent_ids.production_ids

    def set_qty_producing(self):
        self.check_singleton()
        self._update_moves_from_qty_producing(False)

    def action_view_mrp_production_childs(self):
        self.check_singleton()
        mrp_production_ids = self._get_children().ids
        action = {
            "res_model": "mrp.production",
            "type": "ir.actions.act_window",
        }
        if len(mrp_production_ids) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": mrp_production_ids[0],
                }
            )
        else:
            action.update(
                {
                    "name": _("%s Child MO's", self.name),
                    "domain": [("id", "in", mrp_production_ids)],
                    "view_mode": "list,form",
                }
            )
        return action

    def action_view_mrp_production_sources(self):
        self.check_singleton()
        mrp_production_ids = self._get_sources().ids
        action = {
            "res_model": "mrp.production",
            "type": "ir.actions.act_window",
        }
        if len(mrp_production_ids) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": mrp_production_ids[0],
                }
            )
        else:
            action.update(
                {
                    "name": _("MO Generated by %s", self.name),
                    "domain": [("id", "in", mrp_production_ids)],
                    "view_mode": "list,form",
                }
            )
        return action

    def action_view_mrp_production_backorders(self):
        backorder_ids = self.production_group_id.production_ids.ids
        return {
            "res_model": "mrp.production",
            "type": "ir.actions.act_window",
            "name": _("Backorder MO's"),
            "domain": [("id", "in", backorder_ids)],
            "view_mode": "list,form",
        }

    def _prepare_stock_lot_values(self):
        self.check_singleton()
        return self.env["stock.lot"]._prepare_next_lot_vals(
            self.company_id, self.product_id
        )

    def action_generate_serial(self, workorder=False):
        self.check_singleton()
        if self.product_tracking == "lot":
            if self.lot_producing_ids:
                _debug.logic(
                    "production_refused", reason="lot_already_set", productions=self
                )
                raise UserError(_("You cannot set more than 1 lot per product"))
            _debug.lifecycle("lot_generated", production=self.id, tracking="lot")
            self.lot_producing_ids = [Command.create(self._prepare_stock_lot_values())]
            if self.picking_type_id.auto_print_generated_mrp_lot:
                return self._prepare_action_autoprint_generated_lot(
                    self.lot_producing_ids[-1]
                )
        elif self.product_tracking == "serial":
            if self.product_qty == 1 and not self.lot_producing_ids:
                self.lot_producing_ids = [
                    Command.create(self._prepare_stock_lot_values())
                ]
                _debug.lifecycle(
                    "lot_generated", production=self.id, tracking="serial", qty=1
                )
                self.qty_producing = 1
                (workorder or self).set_qty_producing()
                if self.picking_type_id.auto_print_generated_mrp_lot:
                    return self._prepare_action_autoprint_generated_lot(
                        self.lot_producing_ids[-1]
                    )
                return None
            _debug.logic(
                "serial_wizard_opened",
                production=self.id,
                qty=self.product_qty,
                existing=len(self.lot_producing_ids),
            )
            action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
                "mrp.action_assign_serial_numbers"
            )
            action["context"] = {
                "default_production_id": self.id,
            }
            if workorder:
                action["context"]["default_workorder_id"] = workorder.id
            return action
        return None

    def action_confirm(self):
        self._check_company()
        moves_ids_to_confirm = set()
        move_raws_ids_to_adjust = set()
        workorder_ids_to_confirm = set()
        for production in self:
            production_vals = {}
            if production.bom_id:
                production_vals.update({"consumption": production.bom_id.consumption})
            if (
                production.product_tracking == "serial"
                and production.product_uom_id != production.product_id.uom_id
            ):
                production_vals.update(
                    {
                        "product_qty": production.product_uom_id._get_quantity_in_unit(
                            production.product_qty, production.product_id.uom_id
                        ),
                        "product_uom_id": production.product_id.uom_id,
                    }
                )
                for move_finish in production.move_finished_ids.filtered(
                    lambda m, production=production: (
                        m.product_id == production.product_id
                    )
                ):
                    move_finish.write(
                        {
                            "product_uom_qty": move_finish.product_uom_id._get_quantity_in_unit(
                                move_finish.product_uom_qty,
                                move_finish.product_id.uom_id,
                            ),
                            "product_uom_id": move_finish.product_id.uom_id,
                        }
                    )
            if production_vals:
                production.write(production_vals)
            move_raws_ids_to_adjust.update(production.move_raw_ids.ids)
            moves_ids_to_confirm.update(
                (production.move_raw_ids | production.move_finished_ids).ids
            )
            workorder_ids_to_confirm.update(production.workorder_ids.ids)

        move_raws_to_adjust = self.env["stock.move"].browse(
            sorted(move_raws_ids_to_adjust)
        )
        moves_to_confirm = self.env["stock.move"].browse(sorted(moves_ids_to_confirm))
        workorder_to_confirm = self.env["mrp.workorder"].browse(
            sorted(workorder_ids_to_confirm)
        )

        ignored_mo_ids = self.env.context.get("ignore_mo_ids", [])
        _debug.pipeline(
            "production_confirm",
            productions=self,
            raw_moves=len(move_raws_to_adjust),
            moves=len(moves_to_confirm),
            workorders=len(workorder_to_confirm),
        )
        move_raws_to_adjust._update_procure_method()
        moves_to_confirm._action_confirm(merge=False)
        workorder_to_confirm._action_confirm()
        workorder_to_confirm._update_cost_mode()
        self.move_raw_ids.with_context(
            ignore_mo_ids=ignored_mo_ids + self.ids
        )._trigger_scheduler()
        self.picking_ids.filtered(
            lambda p: p.state not in ["cancel", "done"]
        ).action_confirm()
        _debug.lifecycle(
            "production_confirmed",
            productions=self,
            from_draft=len(self.filtered(lambda mo: mo.state == "draft")),
        )
        self.filtered(lambda mo: mo.state == "draft").state = "confirmed"
        return True

    def _link_workorders_and_moves(self):
        self.check_singleton()
        if not self.workorder_ids:
            return
        workorder_per_operation = {
            workorder.operation_id: workorder for workorder in self.workorder_ids
        }
        last_workorder_per_bom = defaultdict(lambda: self.env["mrp.workorder"])
        self.allow_workorder_dependencies = self.bom_id.allow_operation_dependencies
        _debug.pipeline(
            "workorders_linked",
            production=self.id,
            workorders=len(self.workorder_ids),
            by="dependencies" if self.allow_workorder_dependencies else "sequence",
        )

        if self.allow_workorder_dependencies:
            for workorder in self.workorder_ids._sorted_by_routing():
                workorder.blocked_by_workorder_ids = [
                    Command.link(workorder_per_operation[operation_id].id)
                    for operation_id in workorder.operation_id.blocked_by_operation_ids
                    if operation_id in workorder_per_operation
                ]
                if not workorder.needed_by_workorder_ids:
                    last_workorder_per_bom[workorder.operation_id.bom_id] = workorder
        else:
            previous_workorder = False
            for workorder in self.workorder_ids._sorted_by_routing():
                if previous_workorder:
                    workorder.blocked_by_workorder_ids = [
                        Command.link(previous_workorder.id)
                    ]
                previous_workorder = workorder
                last_workorder_per_bom[workorder.operation_id.bom_id] = workorder
        moves_by_workorder = defaultdict(lambda: self.env["stock.move"])
        for move in self.move_raw_ids | self.move_finished_ids:
            if move.operation_id:
                workorder = workorder_per_operation.get(move.operation_id)
                moves_by_workorder[workorder.id if workorder else False] |= move
        # Several moves share one operation, so they share one work order: one
        # write per work order rather than one per move.
        for workorder_id, moves in moves_by_workorder.items():
            moves.write({"workorder_id": workorder_id})

    def action_assign(self):
        with _debug.perf(
            "production_assign",
            cr=self.env.cr,
            productions=self,
            raw_moves=len(self.move_raw_ids),
        ):
            self.move_raw_ids._action_assign()
        return True

    def button_plan(self):
        orders_to_plan = self.filtered(lambda order: not order.is_planned)
        orders_to_confirm = orders_to_plan.filtered(lambda mo: mo.state == "draft")
        _debug.pipeline(
            "production_plan_requested",
            productions=self,
            to_plan=len(orders_to_plan),
            to_confirm=len(orders_to_confirm),
        )
        orders_to_confirm.action_confirm()
        for order in orders_to_plan:
            order._plan_workorders()
        return True

    def _plan_workorders(self, replan=False):
        self.check_singleton()

        if not self.workorder_ids:
            _debug.logic("production_planned", production=self.id, by="no_workorders")
            self.is_planned = True
            return

        self._link_workorders_and_moves()

        final_workorders = self.workorder_ids.filtered(
            lambda wo: not wo.needed_by_workorder_ids
        )
        planned = set()
        with _debug.perf(
            "workorders_planned",
            cr=self.env.cr,
            production=self.id,
            replan=replan,
            leaves=len(final_workorders),
        ) as span:
            for workorder in final_workorders:
                workorder._plan_workorder(replan, planned)
            span.set(planned=len(planned))

        workorders = self.workorder_ids.filtered(
            lambda w: w.state not in ["done", "cancel"]
        )
        if not workorders:
            _debug.logic(
                "production_plan_skipped", production=self.id, reason="all_closed"
            )
            return

        self.with_context(force_date=True).write(
            {
                "date_start": min(
                    (wo.date_start for wo in workorders if wo.date_start),
                    default=None,
                ),
                "date_end": max(
                    (wo.date_end for wo in workorders if wo.date_end),
                    default=None,
                ),
            }
        )

    def button_unplan(self):
        if any(wo.state == "done" for wo in self.workorder_ids):
            _debug.logic(
                "production_refused", reason="unplan_done_wo", productions=self
            )
            raise UserError(
                _(
                    "Some work orders are already done, so you cannot unplan this manufacturing order.\n\n"
                    "It’d be a shame to waste all that progress, right?"
                )
            )
        if any(wo.state == "progress" for wo in self.workorder_ids):
            _debug.logic(
                "production_refused", reason="unplan_started_wo", productions=self
            )
            raise UserError(
                _(
                    "Some work orders have already started, so you cannot unplan this manufacturing order.\n\n"
                    "It’d be a shame to waste all that progress, right?"
                )
            )

        _debug.lifecycle(
            "production_unplanned", productions=self, workorders=len(self.workorder_ids)
        )
        self.workorder_ids.write(
            {
                "date_start": False,
                "date_end": False,
            }
        )
        self.is_planned = False

    def _get_consumption_issues(self):
        issues = []
        if self.env.context.get("skip_consumption", False):
            _debug.logic("consumption_scan_skipped", productions=self, by="context")
            return issues
        orders = self.with_context(
            bom_cost_share_cache=self.env["mrp.bom"]._get_explosion_scratch()
        )
        for order in orders:
            if (
                order.consumption == "flexible"
                or not order.bom_id
                or not order.bom_id.bom_line_ids
            ):
                continue
            expected_move_values = order._prepare_moves_raw_vals()
            expected_qty_by_product = defaultdict(float)
            for move_values in expected_move_values:
                move_product = self.env["product.product"].browse(
                    move_values["product_id"]
                )
                move_uom = self.env["uom.uom"].browse(move_values["product_uom_id"])
                move_product_qty = move_uom._get_quantity_in_unit(
                    move_values["product_uom_qty"], move_product.uom_id
                )
                expected_qty_by_product[move_product] += (
                    move_product_qty * order.qty_producing / order.product_qty
                )

            done_qty_by_product = defaultdict(float)
            for move in order.move_raw_ids:
                quantity = move.product_uom_id._get_quantity_in_unit(
                    move._get_picked_quantity(), move.product_id.uom_id
                )
                if (
                    move.product_id not in expected_qty_by_product
                    and move.picked
                    and not move.product_id.uom_id.is_zero(quantity)
                ):
                    issues.append((order, move.product_id, quantity, 0.0))
                    continue
                done_qty_by_product[move.product_id] += quantity if move.picked else 0.0

            for product, qty_to_consume in expected_qty_by_product.items():
                quantity = done_qty_by_product.get(product, 0.0)
                if product.uom_id.compare(qty_to_consume, quantity) != 0:
                    issues.append((order, product, quantity, qty_to_consume))

        _debug.pipeline("consumption_scanned", productions=self, issues=len(issues))
        return issues

    def _prepare_action_consumption_wizard(self, consumption_issues):
        ctx = self.env.context.copy()
        lines = []
        for order, product_id, consumed_qty, expected_qty in consumption_issues:
            lines.append(
                (
                    0,
                    0,
                    {
                        "mrp_production_id": order.id,
                        "product_id": product_id.id,
                        "consumption": order.consumption,
                        "product_uom_id": product_id.uom_id.id,
                        "product_consumed_qty_uom": consumed_qty,
                        "product_expected_qty_uom": expected_qty,
                    },
                )
            )
        ctx.update(
            {
                "default_mrp_production_ids": self.ids,
                "default_mrp_consumption_warning_line_ids": lines,
                "form_view_ref": False,
            }
        )
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "mrp.action_mrp_consumption_warning"
        )
        action["context"] = ctx
        return action

    def _get_quantity_produced_issues(self):
        quantity_issues = []
        if self.env.context.get("skip_backorder", False):
            return quantity_issues
        quantity_issues.extend(
            order
            for order in self
            if not order.product_uom_id.is_zero(order._get_quantity_to_backorder())
        )
        return quantity_issues

    def _prepare_action_backorder_wizard(self, quantity_issues):
        ctx = self.env.context.copy()
        lines = [
            (0, 0, {"mrp_production_id": order.id, "to_backorder": True})
            for order in quantity_issues
        ]
        ctx.update(
            {
                "default_mrp_production_ids": self.ids,
                "default_mrp_production_backorder_line_ids": lines,
            }
        )
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "mrp.action_mrp_production_backorder"
        )
        action["context"] = ctx
        return action

    def action_cancel(self):
        if any(mo.state == "done" for mo in self):
            _debug.logic("production_refused", reason="cancel_done", productions=self)
            raise UserError(
                _("You cannot cancel a manufacturing order that is already done.")
            )
        self._action_cancel()
        return True

    def _action_cancel(self):
        activity_mixin = self.env["mixin.stock.activity"]
        documents_by_production = {}
        for production in self:
            documents = defaultdict(list)
            for move_raw_id in production.move_raw_ids.filtered(
                lambda m: m.state not in ("done", "cancel")
            ):
                iterate_key = self._get_document_iterate_key(move_raw_id)
                if iterate_key:
                    document = activity_mixin._get_log_activity_documents(
                        {move_raw_id: (move_raw_id.product_uom_qty, 0)},
                        iterate_key,
                        "UP",
                    )
                    for key, value in document.items():
                        documents[key] += [value]
            if documents:
                documents_by_production[production] = documents
            if self.env.context.get("skip_activity"):
                continue
            finish_moves = production.move_finished_ids.filtered(
                lambda x: x.state not in ("done", "cancel")
            )
            if finish_moves:
                production._log_downside_manufactured_quantity(
                    dict.fromkeys(finish_moves, (production.product_uom_qty, 0.0)),
                    cancel=True,
                )

        if self._has_workorders():
            self.workorder_ids.filtered(
                lambda x: x.state not in ["done", "cancel"]
            ).action_cancel()
        finish_moves = self.move_finished_ids.filtered(
            lambda x: x.state not in ("done", "cancel")
        )
        raw_moves = self.move_raw_ids.filtered(
            lambda x: x.state not in ("done", "cancel")
        )
        _debug.pipeline(
            "production_cancel",
            productions=self,
            finish_moves=len(finish_moves),
            raw_moves=len(raw_moves),
            documented=len(documents_by_production),
        )
        (finish_moves | raw_moves).with_context(skip_mo_check=True)._action_cancel()
        picking_ids = self.picking_ids.filtered(
            lambda x: (
                x.state not in ("done", "cancel")
                and not (
                    x.move_ids.move_dest_ids
                    or any(mo.state == "done" for mo in x.production_ids)
                )
            )
        )
        _debug.lifecycle("production_cancelled", productions=self, pickings=picking_ids)
        picking_ids.action_cancel()

        for production, documents in documents_by_production.items():
            filtered_documents = {}
            for (parent, responsible), rendering_context in documents.items():
                if (
                    not parent
                    or (parent._name == "stock.picking" and parent.state == "cancel")
                    or parent == production
                ):
                    continue
                filtered_documents[(parent, responsible)] = rendering_context
            production._log_manufacture_exception(filtered_documents, cancel=True)

        return True

    def _get_document_iterate_key(self, move_raw_id):
        return (move_raw_id.move_orig_ids and "move_orig_ids") or False

    def _update_finished_moves_price_unit(self, consumed_moves):
        self.check_singleton()
        return True

    def _post_inventory(self, cancel_backorder=False):
        moves_to_do, moves_not_to_do, moves_to_cancel = set(), set(), set()
        for move in self.move_raw_ids:
            if move.state == "done":
                moves_not_to_do.add(move.id)
            elif not move.picked:
                moves_to_cancel.add(move.id)
            elif move.state != "cancel":
                moves_to_do.add(move.id)

        with _debug.perf(
            "production_consume_raw",
            cr=self.env.cr,
            productions=self,
            to_do=len(moves_to_do),
            done=len(moves_not_to_do),
            to_cancel=len(moves_to_cancel),
        ):
            self.with_context(skip_mo_check=True).env["stock.move"].browse(
                moves_to_do
            )._action_done(cancel_backorder=cancel_backorder)
            self.with_context(skip_mo_check=True).env["stock.move"].browse(
                moves_to_cancel
            )._action_cancel()
        moves_to_do = self.move_raw_ids.filtered(
            lambda x: x.state == "done"
        ) - self.env["stock.move"].browse(moves_not_to_do)
        moves_to_do_by_order = defaultdict(
            lambda: self.env["stock.move"],
            [
                (key, self.env["stock.move"].concat(*values))
                for key, values in tools_groupby(
                    moves_to_do, key=lambda m: m.raw_material_production_id.id
                )
            ],
        )
        for order in self:
            finish_moves = order.move_finished_ids.filtered(
                lambda m, order=order: (
                    m.product_id == order.product_id
                    and m.state not in ("done", "cancel")
                )
            )
            for move in finish_moves:
                if move.has_tracking != "none" and not move.lot_ids:
                    move.lot_ids = order.lot_producing_ids.ids
                move.quantity = order.product_uom_id.round(
                    order.qty_producing - order.qty_produced, rounding_method="HALF-UP"
                )
                extra_vals = order._prepare_finished_extra_vals()
                if extra_vals:
                    move.move_line_ids.write(extra_vals)
            for workorder in order.workorder_ids:
                if workorder.state not in ("done", "cancel"):
                    workorder.duration_expected = workorder._get_duration_expected()
                if workorder.state == "cancel":
                    workorder.duration = 0.0
                elif not workorder.duration:
                    workorder.duration = workorder.duration_expected
                    workorder.duration_unit = round(
                        workorder.duration / max(workorder.qty_produced, 1), 2
                    )
            order.with_company(order.company_id)._update_finished_moves_price_unit(
                moves_to_do_by_order[order.id]
            )
        moves_to_finish = self.move_finished_ids.filtered(
            lambda x: x.state not in ("done", "cancel")
        )
        moves_to_finish.picked = True
        with _debug.perf(
            "production_produce_finished",
            cr=self.env.cr,
            productions=self,
            moves=len(moves_to_finish),
            cancel_backorder=cancel_backorder,
        ):
            moves_to_finish = moves_to_finish._action_done(
                cancel_backorder=cancel_backorder
            )
        finished_lines_by_order = defaultdict(
            lambda: self.env["stock.move.line"],
            [
                (key, self.env["stock.move.line"].concat(*values))
                for key, values in tools_groupby(
                    moves_to_finish.move_line_ids,
                    key=lambda line: line.move_id.production_id.id,
                )
            ],
        )
        for order in self:
            # Only the lines this pass produced, and only when this pass
            # consumed something. An order can be posted more than once -- post
            # part of it, then mark the rest done -- and `move_finished_ids`
            # carries every batch, so writing the whole set would hand the
            # earlier batch's produced lines this batch's components. When the
            # raw moves were already done, `consume_move_lines` is empty and a
            # replace would erase the first batch's traceability outright.
            consume_move_lines = moves_to_do_by_order[order.id].move_line_ids
            if not consume_move_lines:
                continue
            finished_lines_by_order[order.id].consume_line_ids = [
                Command.set(consume_move_lines.ids)
            ]
        return True

    def _get_name_backorder(self, name, sequence):
        if not sequence:
            return name
        seq_back = (
            "-"
            + "0" * (SIZE_BACK_ORDER_NUMBERING - 1 - int(math.log10(sequence)))
            + str(sequence)
        )
        regex = re.compile(r"-\d+$")
        if regex.search(name) and (
            max(
                self.production_group_id.production_ids.mapped("backorder_sequence"),
                default=0,
            )
            > 1
            or sequence > 1
        ):
            return regex.sub(seq_back, name)
        return name + seq_back

    def _prepare_backorder_mo_vals(self):
        self.check_singleton()
        return {
            "reference_ids": self.reference_ids.ids,
            "production_group_id": self.production_group_id.id,
            "move_raw_ids": None,
            "move_finished_ids": None,
            "lot_producing_ids": False,
            "origin": self.origin,
            "state": "draft" if self.state == "draft" else "confirmed",
            "date_deadline": self.date_deadline,
            "orderpoint_id": self.orderpoint_id.id,
        }

    def _split_productions(
        self, amounts=False, cancel_remaining_qty=False, set_consumed_qty=False
    ):
        amounts, has_backorder_to_ignore = self._get_split_amounts(
            amounts, cancel_remaining_qty
        )
        backorders, initial_qty_by_production = self._create_split_backorders(amounts)
        production_to_backorders, production_ids = self._get_split_backorder_map(
            amounts, backorders
        )
        move_to_backorder_moves, backorder_moves = self._split_moves_into_backorders(
            production_to_backorders, initial_qty_by_production
        )
        self._split_move_lines(
            move_to_backorder_moves,
            backorder_moves,
            set_consumed_qty,
            has_backorder_to_ignore,
        )
        self._update_split_workorders(
            production_to_backorders, initial_qty_by_production
        )
        _debug.pipeline(
            "production_split",
            productions=self,
            backorders=backorders,
            cancel_remaining=cancel_remaining_qty,
            set_consumed_qty=set_consumed_qty,
        )
        backorders._action_confirm_mo_backorders()
        return self.env["mrp.production"].browse(production_ids)

    def _get_default_split_amounts(self):
        self.check_singleton()
        return [self.qty_producing, self._get_quantity_to_backorder()]

    def _get_split_amounts(self, amounts, cancel_remaining_qty):
        amounts = dict(amounts) if amounts else {}
        has_backorder_to_ignore = defaultdict(lambda: False)
        for production in self:
            production_amounts = amounts.get(production)
            if not production_amounts:
                amounts[production] = production._get_default_split_amounts()
                continue
            diff = production.product_uom_id.compare(
                production.product_qty, sum(production_amounts)
            )
            if diff > 0 and not cancel_remaining_qty:
                amounts[production] = production_amounts + [
                    production.product_qty - sum(production_amounts)
                ]
                has_backorder_to_ignore[production] = True
            elif not self.env.context.get("allow_more") and (
                diff < 0 or production.state in ("done", "cancel")
            ):
                _debug.logic(
                    "split_refused",
                    reason="more_than_producible",
                    production=production.id,
                    diff=diff,
                    state=production.state,
                )
                raise UserError(
                    _("Unable to split with more than the quantity to produce.")
                )
        return amounts, has_backorder_to_ignore

    def _create_split_backorders(self, amounts):
        backorder_vals_list = []
        initial_qty_by_production = {}
        next_seq_by_group = {}
        for production in self.sudo():
            initial_qty_by_production[production] = production.product_qty
            if production.backorder_sequence == 0:
                production.backorder_sequence = 1
            production.name = production._get_name_backorder(
                production.name, production.backorder_sequence
            )
            (
                production.move_raw_ids | production.move_finished_ids
            ).origin = production._get_origin()
            backorder_vals = production.copy_data(
                default=production._prepare_backorder_mo_vals()
            )[0]
            backorder_qtys = amounts[production][1:]
            production.with_context(
                skip_compute_move_raw_ids=True
            ).product_qty = amounts[production][0]

            group = production.production_group_id
            if group.id not in next_seq_by_group:
                next_seq_by_group[group.id] = max(
                    group.production_ids.mapped("backorder_sequence"),
                    default=1,
                )
            for qty_to_backorder in backorder_qtys:
                next_seq_by_group[group.id] += 1
                next_seq = next_seq_by_group[group.id]
                backorder_vals_list.append(
                    dict(
                        backorder_vals,
                        product_qty=qty_to_backorder,
                        name=production._get_name_backorder(production.name, next_seq),
                        backorder_sequence=next_seq,
                    )
                )
        backorders = (
            self.env["mrp.production"]
            .with_context(skip_confirm=True)
            .sudo()
            .create(backorder_vals_list)
        )
        _debug.lifecycle("backorders_created", productions=self, backorders=backorders)
        return backorders, initial_qty_by_production

    def _get_split_backorder_map(self, amounts, backorders):
        index = 0
        production_to_backorders = {}
        production_ids = OrderedSet()
        for production in self:
            backorders_created = len(amounts[production]) - 1
            production_backorders = backorders[index : index + backorders_created]
            production_to_backorders[production] = production_backorders
            production_ids.update(production.ids)
            production_ids.update(production_backorders.ids)
            index += backorders_created
        return production_to_backorders, production_ids

    def _split_moves_into_backorders(
        self, production_to_backorders, initial_qty_by_production
    ):
        new_moves_vals = []
        split_moves = []
        move_to_backorder_moves = {}
        (self.move_raw_ids | self.move_finished_ids).filtered(
            lambda m: m.picked and not m.additional
        ).move_line_ids.filtered(lambda ml: not ml.picked).unlink()
        for production in self:
            for move in production.move_raw_ids | production.move_finished_ids:
                if move.additional:
                    continue
                move_to_backorder_moves[move] = self.env["stock.move"]
                unit_factor = (
                    move.product_uom_qty / initial_qty_by_production[production]
                )
                initial_move_vals = move.copy_data(move._prepare_backorder_move_vals())[
                    0
                ]
                move.with_context(
                    do_not_unreserve=True, no_procurement=True
                ).product_uom_qty = production.product_qty * unit_factor

                for backorder in production_to_backorders[production]:
                    move_vals = dict(
                        initial_move_vals,
                        product_uom_qty=backorder.product_qty * unit_factor,
                    )
                    if move.raw_material_production_id:
                        move_vals["raw_material_production_id"] = backorder.id
                    else:
                        move_vals["production_id"] = backorder.id
                    new_moves_vals.append(move_vals)
                    split_moves.append(move)

        backorder_moves = self.env["stock.move"].create(new_moves_vals)
        for move, backorder_move in zip(split_moves, backorder_moves, strict=True):
            move_to_backorder_moves[move] |= backorder_move
        return move_to_backorder_moves, backorder_moves

    def _split_move_lines(
        self,
        move_to_backorder_moves,
        backorder_moves,
        set_consumed_qty,
        has_backorder_to_ignore,
    ):
        move_lines_vals = []
        assigned_moves = set()
        partially_assigned_moves = set()
        move_lines_to_unlink = set()
        moves_to_consume = self.env["stock.move"]

        for initial_move, split_backorder_moves in move_to_backorder_moves.items():
            moves_to_consume |= self._get_split_moves_to_consume(
                initial_move,
                split_backorder_moves,
                set_consumed_qty,
                has_backorder_to_ignore,
                move_lines_vals,
            )

        for initial_move, split_backorder_moves in move_to_backorder_moves.items():
            self._spread_reservation_over_split_moves(
                initial_move,
                split_backorder_moves,
                move_lines_vals,
                assigned_moves,
                partially_assigned_moves,
            )
            move_lines_to_unlink.update(
                initial_move.move_line_ids.filtered(lambda ml: not ml.quantity).ids
            )

        self.env["stock.move"].browse(assigned_moves).write({"state": "assigned"})
        self.env["stock.move"].browse(partially_assigned_moves).write(
            {"state": "partially_available"}
        )
        self.env["stock.move.line"].create(move_lines_vals)
        backorder_moves._filtered_to_assign_at_confirm()._action_assign()

        emptied_lines = self.env["stock.move.line"].browse(move_lines_to_unlink)
        emptied_lines.write({"move_id": False})
        emptied_lines.unlink()
        moves_to_consume.write({"picked": True})

    def _spread_reservation_over_split_moves(
        self,
        initial_move,
        split_backorder_moves,
        move_lines_vals,
        assigned_moves,
        partially_assigned_moves,
    ):
        product_uom_id = initial_move.product_id.uom_id
        ml_by_move = []
        if not initial_move.picked:
            for move_line in initial_move.move_line_ids:
                available_qty = move_line.product_uom_id._get_quantity_in_unit(
                    move_line.quantity, product_uom_id, rounding_method="HALF-UP"
                )
                if product_uom_id.compare(available_qty, 0) <= 0:
                    continue
                ml_by_move.append((available_qty, move_line, move_line.copy_data()[0]))

        remaining = list(initial_move | split_backorder_moves)
        move = remaining.pop(0)
        move_qty_to_reserve = move.product_qty

        def get_next_move():
            return remaining.pop(0) if remaining else self.env["stock.move"]

        for index, (quantity, move_line, ml_vals) in enumerate(ml_by_move):
            taken_qty = min(quantity, move_qty_to_reserve)
            taken_qty_uom = product_uom_id._get_quantity_in_unit(
                taken_qty, move_line.product_uom_id, rounding_method="HALF-UP"
            )
            if move_line.product_uom_id.is_zero(taken_qty_uom):
                continue
            move_line.write({"quantity": taken_qty_uom, "move_id": move.id})
            move_qty_to_reserve -= taken_qty
            ml_by_move[index] = (quantity - taken_qty, move_line, ml_vals)
            if move.product_uom_id.compare(move_qty_to_reserve, 0) <= 0:
                assigned_moves.add(move.id)
                move = get_next_move()
                move_qty_to_reserve = move.product_qty if move else 0

        for quantity, move_line, ml_vals in ml_by_move:
            while product_uom_id.compare(quantity, 0) > 0 and move:
                taken_qty = min(move_qty_to_reserve, quantity)
                taken_qty_uom = product_uom_id._get_quantity_in_unit(
                    taken_qty, move_line.product_uom_id, rounding_method="HALF-UP"
                )
                if move == initial_move:
                    move_line.quantity += taken_qty_uom
                elif not move_line.product_uom_id.is_zero(taken_qty_uom):
                    move_lines_vals.append(
                        dict(ml_vals, quantity=taken_qty_uom, move_id=move.id)
                    )
                quantity -= taken_qty
                move_qty_to_reserve -= taken_qty
                if move.product_uom_id.compare(move_qty_to_reserve, 0) <= 0:
                    assigned_moves.add(move.id)
                    move = get_next_move()
                    move_qty_to_reserve = move.product_qty if move else 0

        if move and move_qty_to_reserve != move.product_qty:
            partially_assigned_moves.add(move.id)

    def _get_split_moves_to_consume(
        self,
        initial_move,
        split_backorder_moves,
        set_consumed_qty,
        has_backorder_to_ignore,
        move_lines_vals,
    ):
        if not set_consumed_qty:
            return self.env["stock.move"]
        if not initial_move.raw_material_production_id and not (
            initial_move.production_id
            and initial_move.product_id != initial_move.production_id.product_id
        ):
            return self.env["stock.move"]
        ml_vals = initial_move._prepare_move_line_vals()
        backorder_move_to_ignore = (
            split_backorder_moves[-1]
            if has_backorder_to_ignore[initial_move.raw_material_production_id]
            else self.env["stock.move"]
        )
        moves_to_consume = (
            initial_move + split_backorder_moves - backorder_move_to_ignore
        )
        if not initial_move.move_line_ids:
            move_lines_vals.extend(
                dict(ml_vals, quantity=move.product_uom_qty, move_id=move.id)
                for move in moves_to_consume
            )
        return moves_to_consume

    def _update_split_workorders(
        self, production_to_backorders, initial_qty_by_production
    ):
        workorders_to_cancel = self.env["mrp.workorder"]
        for production in self:
            initial_qty = initial_qty_by_production[production]
            backorders = production_to_backorders[production]

            for workorder in backorders.workorder_ids:
                workorder.duration_expected = workorder._get_duration_expected()

            remaining_qtys = []
            for workorder in production.workorder_ids.sorted("id"):
                remaining_qtys.append(
                    max(
                        initial_qty
                        - workorder.qty_reported_from_previous_wo
                        - workorder.qty_produced,
                        0,
                    )
                )
                if workorder.production_id.id not in (
                    self.env.context.get("mo_ids_to_backorder") or []
                ):
                    workorder.qty_produced = min(
                        workorder.qty_produced, workorder.qty_production
                    )
            # A backorder's work orders are copies of the production's, made in id
            # order, so their ids pair them with the quantities above. Their _order
            # does not: work orders sharing a sequence sort by planned start.
            for backorder in backorders.sorted("id"):
                for index, workorder in enumerate(backorder.workorder_ids.sorted("id")):
                    remaining_qty = remaining_qtys[index]
                    workorder.qty_reported_from_previous_wo = max(
                        workorder.qty_production - remaining_qty, 0
                    )
                    _debug.logic(
                        "split_workorder_paired",
                        production=production.id,
                        backorder=backorder.id,
                        workorder=workorder.id,
                        operation=workorder.operation_id.id,
                        remaining=remaining_qty,
                    )
                    if remaining_qty:
                        remaining_qtys[index] = max(
                            remaining_qty - workorder.qty_produced, 0
                        )
                    else:
                        workorders_to_cancel += workorder
        workorders_to_cancel.action_cancel()

    def _action_confirm_mo_backorders(self):
        self.workorder_ids._action_confirm()

    def button_mark_done(self):
        res = self.pre_button_mark_done()
        if res is not True:
            _debug.logic(
                "mark_done_deferred",
                productions=self,
                action=res.get("res_model") if isinstance(res, dict) else None,
            )
            return res

        if self.env.context.get("mo_ids_to_backorder"):
            productions_to_backorder = self.browse(
                self.env.context["mo_ids_to_backorder"]
            )
            productions_not_to_backorder = self - productions_to_backorder
        else:
            productions_not_to_backorder = self
            productions_to_backorder = self.env["mrp.production"]
        productions_not_to_backorder = productions_not_to_backorder.with_context(
            no_procurement=True
        )
        _debug.pipeline(
            "mark_done",
            productions=self,
            to_backorder=len(productions_to_backorder),
            straight=len(productions_not_to_backorder),
            workorders=len(self.workorder_ids),
        )
        self.workorder_ids.button_finish()

        backorders = (
            productions_to_backorder and productions_to_backorder._split_productions()
        )
        backorders -= productions_to_backorder

        productions_not_to_backorder._post_inventory(cancel_backorder=True)
        productions_to_backorder._post_inventory(cancel_backorder=True)

        done_move_finished_ids = (
            productions_to_backorder.move_finished_ids
            | productions_not_to_backorder.move_finished_ids
        ).filtered(lambda m: m.state == "done")
        done_move_finished_ids._trigger_assign()

        (
            productions_not_to_backorder.move_raw_ids
            | productions_not_to_backorder.move_finished_ids
        ).filtered(lambda x: x.state not in ("done", "cancel")).write(
            {
                "state": "done",
                "product_uom_qty": 0.0,
            }
        )
        self.write(
            {
                "date_end": fields.Datetime.now(),
                "priority": "0",
                "is_locked": True,
                "state": "done",
            }
        )

        _debug.lifecycle("production_done", productions=self, backorders=backorders)
        backorders_to_assign = backorders.filtered(
            lambda order: order.picking_type_id.reservation_method == "at_confirm"
        )
        for backorder in backorders_to_assign:
            backorder.action_assign()

        return self._prepare_action_mark_done(backorders)

    def _prepare_action_mark_done(self, backorders):
        report_actions = self._prepare_actions_autoprint_done()
        if self.env.context.get("skip_redirection"):
            if report_actions:
                return {
                    "type": "ir.actions.client",
                    "tag": "do_multi_print",
                    "context": {},
                    "params": {"reports": report_actions},
                }
            return True

        another_action = (
            self._prepare_action_backorder_redirect(backorders)
            if backorders
            else self._prepare_action_closed_redirect()
        )
        if report_actions:
            return {
                "type": "ir.actions.client",
                "tag": "do_multi_print",
                "params": {
                    "reports": report_actions,
                    "anotherAction": another_action,
                },
            }
        return another_action or True

    def _prepare_action_closed_redirect(self):
        if self.env.context.get("from_workorder"):
            return {
                "type": "ir.actions.act_window",
                "res_model": "mrp.production",
                "views": [[self.env.ref("mrp.mrp_production_form_view").id, "form"]],
                "res_id": self.id,
                "target": "main",
            }
        if not self.env.user.has_group("mrp.group_mrp_reception_report"):
            return False
        mos_to_show = self.filtered(
            lambda mo: mo.picking_type_id.auto_show_reception_report
        )
        lines = mos_to_show.move_finished_ids.filtered(
            lambda m: (
                m.product_id.is_storable
                and m.state != "cancel"
                and m.picked
                and not m.move_dest_ids
            )
        )
        if lines and any(mo.show_allocation for mo in mos_to_show):
            return mos_to_show.action_view_reception_report()
        return False

    def _prepare_action_backorder_redirect(self, backorders):
        context = {
            k: False if k.startswith("skip_") else v
            for k, v in self.env.context.items()
            if not k.startswith("default_")
        }
        action = {
            "res_model": "mrp.production",
            "type": "ir.actions.act_window",
            "context": dict(context, mo_ids_to_backorder=None),
        }
        if len(backorders) == 1:
            action.update(
                {
                    "views": [[False, "form"]],
                    "view_mode": "form",
                    "res_id": backorders[0].id,
                }
            )
        else:
            action.update(
                {
                    "name": _("Backorder MO"),
                    "domain": [("id", "in", backorders.ids)],
                    "views": [[False, "list"], [False, "form"]],
                    "view_mode": "list,form",
                }
            )
        return action

    def pre_button_mark_done(self):
        self._check_ready_to_mark_done()
        production_auto_ids = set()
        production_missing_lot_ids = set()
        for production in self:
            if production._is_auto_completable():
                production_auto_ids.add(production.id)
            elif not production.lot_producing_ids:
                production_missing_lot_ids.add(production.id)

        _debug.pipeline(
            "mark_done_preflight",
            productions=self,
            auto=len(production_auto_ids),
            missing_lot=len(production_missing_lot_ids),
        )
        if production_missing_lot_ids:
            if len(production_missing_lot_ids) > 1:
                raise UserError(
                    _(
                        "You need to generate Lot/Serial Number(s) to mark as done some productions"
                    )
                )
            return (
                self.env["mrp.production"]
                .browse(production_missing_lot_ids)
                .action_generate_serial()
            )

        productions_auto = self.env["mrp.production"].browse(production_auto_ids)
        for production in productions_auto:
            production._update_quantities()

        self.move_raw_ids.filtered(
            lambda m: m.manual_consumption and not m.picked
        ).picked = True

        (self - productions_auto)._mark_byproducts_as_produced()

        consumption_issues = self._get_consumption_issues()
        if consumption_issues:
            _debug.logic(
                "mark_done_blocked",
                by="consumption_issues",
                productions=self,
                issues=len(consumption_issues),
            )
            return self._prepare_action_consumption_wizard(consumption_issues)

        quantity_issues = self._get_quantity_produced_issues()
        if quantity_issues:
            mo_ids_always = []
            mos_ask = []
            for mo in quantity_issues:
                if mo.picking_type_id.create_backorder == "always":
                    mo_ids_always.append(mo.id)
                elif mo.picking_type_id.create_backorder == "ask":
                    mos_ask.append(mo)
            _debug.logic(
                "mark_done_blocked",
                by="quantity_issues",
                productions=self,
                always=len(mo_ids_always),
                ask=len(mos_ask),
            )
            if mos_ask:
                return self.with_context(
                    always_backorder_mo_ids=mo_ids_always
                )._prepare_action_backorder_wizard(mos_ask)
            elif mo_ids_always:
                res = self.with_context(
                    skip_backorder=True, mo_ids_to_backorder=mo_ids_always
                ).button_mark_done()
                if res is not True:
                    res["context"] = dict(
                        res.get("context", {}),
                        marked_as_done=all(mo.state == "done" for mo in self),
                    )
                return res if self._is_result_return_required() else True
        return True

    def _check_ready_to_mark_done(self):
        self._check_company()
        for order in self:
            order._check_sn_uniqueness()

    def _is_auto_completable(self):
        self.check_singleton()
        return (
            all(
                p.tracking == "none"
                for p in self.move_raw_ids.product_id
                | self.move_finished_ids.product_id
            )
            or self.product_uom_qty == 1
            or (
                self.product_id.tracking != "serial"
                and self.reservation_state in ("assigned", "confirmed", "waiting")
            )
        )

    def _is_result_return_required(self):
        return True

    def action_unreserve(self):
        (self.move_finished_ids | self.move_raw_ids).filtered(
            lambda x: x.state not in ("done", "cancel")
        )._unreserve()

    def button_scrap(self):
        self.check_singleton()
        return {
            "name": _("Scrap Products"),
            "view_mode": "form",
            "res_model": "stock.scrap",
            "views": [[self.env.ref("stock.view_stock_scrap_form2").id, "form"]],
            "type": "ir.actions.act_window",
            "context": {
                "default_production_id": self.id,
                "product_ids": (
                    self.move_raw_ids.filtered(
                        lambda x: x.state not in ("done", "cancel")
                    )
                    | self.move_finished_ids.filtered(lambda x: x.state == "done")
                )
                .mapped("product_id")
                .ids,
                "default_company_id": self.company_id.id,
            },
            "target": "new",
        }

    def action_view_move_scrap(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.action_stock_scrap"
        )
        action["domain"] = [("production_id", "=", self.id)]
        action["context"] = dict(self.env.context, default_origin=self.name)
        return action

    def action_view_reception_report(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "mrp.mrp_reception_action"
        )
        action["context"] = dict(
            {"default_production_ids": self.ids}, **self.env.context
        )
        return action

    def action_view_mrp_production_unbuilds(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "mrp.mrp_unbuild"
        )
        action["domain"] = [("mo_id", "=", self.id)]
        context = self.env["ir.actions.actions"]._eval_action_context(action["context"])
        context.update(self.env.context)
        context["default_mo_id"] = self.id
        action["context"] = context
        return action

    @api.model
    def get_empty_list_help(self, help_message):
        self = self.with_context(
            empty_list_help_document_name=_("manufacturing order"),
        )
        return super().get_empty_list_help(help_message)

    def _log_downside_manufactured_quantity(self, moves_modification, cancel=False):
        def get_groupby_key(move):
            return (move.picking_id, move.product_id.responsible_id)

        def _render_note_exception_quantity_mo(rendering_context):
            values = {
                "production_order": self,
                "order_exceptions": rendering_context,
                "impacted_pickings": False,
                "cancel": cancel,
            }
            return self.env["ir.qweb"]._render("mrp.exception_on_mo", values)

        documents = self.env["mixin.stock.activity"]._get_log_activity_documents(
            moves_modification, "move_dest_ids", "DOWN", get_groupby_key
        )
        documents = self.env[
            "stock.picking"
        ]._add_less_quantities_than_expected_documents(moves_modification, documents)
        self.env["mixin.stock.activity"]._log_activity(
            _render_note_exception_quantity_mo, documents
        )

    def _log_manufacture_exception(self, documents, cancel=False):
        def _render_note_exception_quantity_mo(rendering_context):
            visited_objects = []
            order_exceptions = {}
            for exception in rendering_context:
                order_exception, visited = exception
                order_exceptions.update(order_exception)
                visited_objects += visited
            visited_objects = [sm for sm in visited_objects if sm._name == "stock.move"]
            impacted_object = []
            if visited_objects:
                visited_objects = self.env[visited_objects[0]._name].concat(
                    *visited_objects
                )
                visited_objects |= visited_objects.mapped("move_orig_ids")
                impacted_object = visited_objects.filtered(
                    lambda m: m.state not in ("done", "cancel")
                ).mapped("picking_id")
            values = {
                "production_order": self,
                "order_exceptions": order_exceptions,
                "impacted_object": impacted_object,
                "cancel": cancel,
            }
            return self.env["ir.qweb"]._render("mrp.exception_on_mo", values)

        self.env["mixin.stock.activity"]._log_activity(
            _render_note_exception_quantity_mo, documents
        )

    def button_unbuild(self):
        self.check_singleton()
        return {
            "name": _("Unbuild: %s", self.product_id.display_name),
            "view_mode": "form",
            "res_model": "mrp.unbuild",
            "view_id": self.env.ref("mrp.mrp_unbuild_form_view_simplified").id,
            "type": "ir.actions.act_window",
            "context": {
                "default_product_id": self.product_id.id,
                "default_lot_id": self.lot_producing_ids[:1].id,
                "default_mo_id": self.id,
                "default_company_id": self.company_id.id,
                "default_location_id": self.location_dest_id.id,
                "default_location_dest_id": self.location_src_id.id,
                "create": False,
                "edit": False,
            },
            "target": "new",
        }

    def action_split(self):
        self._check_split_merge_allowed(split=True)
        if len(self) > 1:
            productions = [
                Command.create({"production_id": production.id}) for production in self
            ]
            wizard = self.env["mrp.production.split.multi"].create(
                {"production_ids": productions}
            )
            action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
                "mrp.action_mrp_production_split_multi"
            )
            action["res_id"] = wizard.id
            return action
        else:
            action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
                "mrp.action_mrp_production_split"
            )
            action["context"] = {
                "default_production_id": self.id,
            }
            return action

    def action_merge(self):
        self._check_split_merge_allowed(merge=True)
        products = {(production.product_id, production.bom_id) for production in self}
        product_id, bom_id = products.pop()
        users = {production.user_id for production in self}
        if len(users) == 1:
            user_id = users.pop()
        else:
            user_id = self.env.user

        origs = self._prepare_merge_orig_links()
        dests = {}
        for move in self.move_finished_ids:
            dests.setdefault(move.byproduct_id.id, []).extend(move.move_dest_ids.ids)

        production = (
            self.env["mrp.production"]
            .with_context(default_picking_type_id=self.picking_type_id.id)
            .create(
                {
                    "product_id": product_id.id,
                    "bom_id": bom_id.id,
                    "picking_type_id": self.picking_type_id.id,
                    "product_qty": sum(
                        production.product_uom_qty for production in self
                    ),
                    "product_uom_id": product_id.uom_id.id,
                    "location_final_id": all(mo.location_final_id for mo in self)
                    and len(self.location_final_id) == 1
                    and self.location_final_id.id,
                    "user_id": user_id.id,
                    "reference_ids": [Command.link(r.id) for r in self.reference_ids],
                    "origin": ",".join(
                        sorted([production.name for production in self])
                    ),
                }
            )
        )

        self.env["stock.move"].search(
            [
                ("production_group_id", "in", self.production_group_id.ids),
            ]
        ).production_group_id = production.production_group_id

        production.production_group_id.parent_ids = [
            Command.set(self.production_group_id.parent_ids.ids)
        ]
        production.production_group_id.child_ids = [
            Command.set(self.production_group_id.child_ids.ids)
        ]

        for move in production.move_raw_ids:
            for field, vals in origs[move.bom_line_id.id].items():
                move[field] = vals

        for move in production.move_finished_ids:
            move.move_dest_ids = [Command.set(dests[move.byproduct_id.id])]

        self.move_dest_ids.created_production_id = production.id

        if "confirmed" in self.mapped("state"):
            production.move_raw_ids._update_procure_method()
            (production.move_raw_ids | production.move_finished_ids).write(
                {"state": "confirmed"}
            )
            production.action_confirm()

        self.with_context(skip_activity=True)._action_cancel()
        self_sudo = self.sudo()
        groups = {
            production.production_group_id
            for production in self_sudo
            if production.production_group_id
        }
        self_sudo.production_group_id = False
        for group in groups:
            if not group.production_ids:
                group.unlink()
        production.move_raw_ids.move_orig_ids.with_context(
            date_deadline_propagate_ids=set(production.move_raw_ids.ids)
        ).write({"date_deadline": production.date_start})
        for p in self:
            p._message_log(
                body=_("This production has been merge in %s", production.display_name)
            )

        return {
            "type": "ir.actions.act_window",
            "res_model": "mrp.production",
            "view_mode": "form",
            "res_id": production.id,
        }

    def action_plan_with_components_availability(self):
        for production in self.filtered(lambda p: p.state in ("draft", "confirmed")):
            if production.state == "draft":
                production.action_confirm()
            move_expected_date = production.move_raw_ids.filtered(
                "date_planned_forecast"
            ).mapped("date_planned_forecast")
            expected_date = max(move_expected_date, default=False)
            if (
                expected_date
                and production.components_availability_state != "unavailable"
            ):
                production.date_start = expected_date
        self.filtered(lambda p: p.state == "confirmed").button_plan()

    def _has_workorders(self):
        return self.workorder_ids

    def _link_bom(self, bom):
        self.check_singleton()
        product_qty = self.product_qty
        uom = self.product_uom_id
        moves_to_unlink = self.env["stock.move"]
        workorders_to_unlink = self.env["mrp.workorder"]
        if self.state == "draft" and self.bom_id == bom:
            self.bom_id = False
        if self.state in ["cancel", "done", "draft"]:
            if self.state == "draft":
                moves_to_unlink = self.move_raw_ids
                workorders_to_unlink = self.workorder_ids
            _debug.pipeline(
                "bom_linked",
                production=self.id,
                bom=bom.id,
                by="wholesale_replace",
                state=self.state,
            )
            self.bom_id = bom
            moves_to_unlink.exists().unlink()
            workorders_to_unlink.exists().unlink()
            if self.state == "draft":
                self.write({"product_qty": product_qty, "product_uom_id": uom.id})
            return

        ratio = self._get_ratio_between_mo_and_bom_quantities(bom)
        bom_lines_by_id = self._get_bom_lines_to_link(bom)
        bom_byproducts_by_id = {
            byproduct.id: byproduct
            for byproduct in bom.byproduct_ids.filtered(self._is_bom_record_applicable)
        }
        operations_by_id = {
            operation.id: operation
            for operation in bom.operation_ids.filtered(self._is_bom_record_applicable)
        }

        _debug.pipeline(
            "bom_linked",
            production=self.id,
            bom=bom.id,
            by="reconcile",
            ratio=ratio,
            lines=len(bom_lines_by_id),
            byproducts=len(bom_byproducts_by_id),
            operations=len(operations_by_id),
        )
        workorders_to_unlink |= self._link_bom_operations(operations_by_id)
        moves_to_unlink |= self._link_bom_lines(bom, bom_lines_by_id, ratio)
        moves_to_unlink |= self._link_bom_byproducts(bom_byproducts_by_id, ratio)

        if self.warehouse_id.manufacture_steps in ("pbm", "pbm_sam"):
            moves_to_unlink.product_uom_qty = 0
        _debug.lifecycle(
            "bom_link_pruned",
            production=self.id,
            moves=len(moves_to_unlink),
            workorders=len(workorders_to_unlink),
        )
        moves_to_unlink._action_cancel()
        moves_to_unlink.unlink()
        workorders_to_unlink.unlink()
        self.bom_id = bom

    def _is_bom_record_applicable(self, record, product=None):
        self.check_singleton()
        if product is None:
            product = self.product_id
        product_attribute_ids = product.product_template_attribute_value_ids.ids
        return not record.bom_product_template_attribute_value_ids or any(
            attribute_value.id in product_attribute_ids
            for attribute_value in record.bom_product_template_attribute_value_ids
        )

    def _get_bom_lines_to_link(self, bom):
        self.check_singleton()
        _dummy, bom_lines = bom._explode(self.product_id, bom.product_qty)
        bom_lines_by_id = defaultdict(lambda: [None, 0])
        for line, exploded_values in bom_lines:
            if not self._is_bom_record_applicable(line, exploded_values["product"]):
                continue
            key = (line.id, line.product_id.id)
            bom_lines_by_id[key][0] = line
            bom_lines_by_id[key][1] += (
                exploded_values["qty"] / exploded_values["original_qty"]
            )
        return bom_lines_by_id

    def _link_bom_operations(self, operations_by_id):
        self.check_singleton()

        def get_operation_key(record):
            return tuple(record[key] for key in ("company_id", "name", "workcenter_id"))

        workorders_to_unlink = self.env["mrp.workorder"]
        for workorder in self.workorder_ids:
            operation = operations_by_id.pop(workorder.operation_id.id, False)
            if not operation:
                for operation_id, candidate in operations_by_id.items():
                    if get_operation_key(candidate) == get_operation_key(workorder):
                        operation = operations_by_id.pop(operation_id)
                        break
            if operation and workorder.operation_id != operation:
                workorder.operation_id = operation
            elif operation and workorder.operation_id == operation:
                if workorder.workcenter_id != operation.workcenter_id:
                    workorder.workcenter_id = operation.workcenter_id
                if workorder.name != operation.name:
                    workorder.name = operation.name
            elif workorder.operation_id:
                workorders_to_unlink |= workorder
        self.workorder_ids += self.env["mrp.workorder"].create(
            [
                {
                    "name": operation.name,
                    "operation_id": operation.id,
                    "sequence": operation.sequence,
                    "product_uom_id": self.product_uom_id.id,
                    "production_id": self.id,
                    "state": "blocked",
                    "workcenter_id": operation.workcenter_id.id,
                }
                for operation in operations_by_id.values()
            ]
        )
        return workorders_to_unlink

    def _link_bom_lines(self, bom, bom_lines_by_id, ratio):
        self.check_singleton()
        moves_to_unlink = self.env["stock.move"]
        for move_raw in self.move_raw_ids:
            bom_line, bom_qty = bom_lines_by_id.pop(
                (move_raw.bom_line_id.id, move_raw.product_id.id), (False, None)
            )
            if not bom_line:
                for candidate, _candidate_qty in bom_lines_by_id.values():
                    if move_raw.product_id == candidate.product_id:
                        bom_line, bom_qty = bom_lines_by_id.pop(
                            (candidate.id, move_raw.product_id.id)
                        )
                        if bom_line:
                            break
            if not bom_line:
                moves_to_unlink |= move_raw
                continue
            move_raw_qty = move_raw.product_uom_id._get_quantity_in_unit(
                move_raw.product_uom_qty * ratio, bom_line.product_uom_id
            )
            if (
                move_raw.bom_line_id
                and move_raw.bom_line_id.bom_id == bom
                and move_raw.operation_id == bom_line.operation_id
                and bom_line.product_qty == move_raw_qty
            ):
                continue
            move_raw.bom_line_id = bom_line
            move_raw.product_id = bom_line.product_id
            move_raw.product_uom_qty = bom_qty / ratio
            move_raw.product_uom_id = bom_line.product_uom_id
            if move_raw.operation_id != bom_line.operation_id:
                move_raw.operation_id = bom_line.operation_id
                move_raw.workorder_id = self.workorder_ids.filtered(
                    lambda wo, move_raw=move_raw: (
                        wo.operation_id == move_raw.operation_id
                    )
                )
            move_raw.manual_consumption = move_raw._is_manual_consumption_from_bom_line(
                bom_line
            )
        self.env["stock.move"].create(
            [
                self._prepare_move_raw_vals(
                    bom_line.product_id,
                    bom_qty / ratio,
                    bom_line.product_uom_id,
                    bom_line=bom_line,
                )
                for bom_line, bom_qty in bom_lines_by_id.values()
            ]
        )
        return moves_to_unlink

    def _link_bom_byproducts(self, bom_byproducts_by_id, ratio):
        self.check_singleton()
        moves_to_unlink = self.env["stock.move"]
        for move_byproduct in self.move_byproduct_ids:
            bom_byproduct = bom_byproducts_by_id.pop(
                move_byproduct.byproduct_id.id, False
            )
            if not bom_byproduct:
                for candidate in bom_byproducts_by_id.values():
                    if move_byproduct.product_id == candidate.product_id:
                        bom_byproduct = bom_byproducts_by_id.pop(candidate.id)
                        break
            if not bom_byproduct:
                moves_to_unlink |= move_byproduct
                continue
            move_byproduct_qty = move_byproduct.product_uom_id._get_quantity_in_unit(
                move_byproduct.product_uom_qty * ratio, bom_byproduct.product_uom_id
            )
            if (
                move_byproduct.byproduct_id
                and bom_byproduct.product_id == move_byproduct.product_id
                and bom_byproduct.product_qty == move_byproduct_qty
            ):
                continue
            move_byproduct.byproduct_id = bom_byproduct
            move_byproduct.cost_share = bom_byproduct.cost_share
            move_byproduct.product_uom_qty = bom_byproduct.product_qty / ratio
            move_byproduct.product_uom_id = bom_byproduct.product_uom_id
        self.move_finished_ids += self.env["stock.move"].create(
            [
                self._prepare_move_finished_vals(
                    bom_byproduct.product_id.id,
                    bom_byproduct.product_qty / ratio,
                    bom_byproduct.product_uom_id.id,
                    bom_byproduct.operation_id.id,
                    bom_byproduct.id,
                    bom_byproduct.cost_share,
                )
                for bom_byproduct in bom_byproducts_by_id.values()
            ]
        )
        return moves_to_unlink

    def _get_quantity_to_backorder(self):
        self.check_singleton()
        return max(self.product_qty - self.qty_producing, 0)

    def _get_ratio_between_mo_and_bom_quantities(self, bom):
        self.check_singleton()
        bom_product_uom = (bom.product_id or bom.product_tmpl_id).uom_id
        bom_qty = bom.product_uom_id._get_quantity_in_unit(
            bom.product_qty, bom_product_uom
        )
        return bom_qty / self.product_uom_qty

    def _check_sn_uniqueness(self):
        self.check_singleton()
        if self.product_tracking == "serial" and self.lot_producing_ids:
            lots_to_check = self.lot_producing_ids.filtered(
                lambda l: l.id not in self.move_raw_ids.lot_ids.ids
            )
            if lots_to_check and self._is_any_finished_serial_already_produced(
                lots_to_check,
                suspect_lots=self._get_serials_produced_in_production_location(
                    lots_to_check
                ),
            ):
                raise UserError(
                    _(
                        "Serial number(s) for product %(product_name)s already produced",
                        product_name=self.product_id.name,
                    )
                )

        byproduct_lines = self.env["stock.move.line"].union(
            *(
                move_line
                for move in self.move_finished_ids
                if move.has_tracking == "serial" and move.product_id != self.product_id
                for move_line in move.move_line_ids
                if not move_line.product_uom_id.is_zero(move_line.quantity)
            )
        )
        suspect_lots = self._get_serials_produced_in_production_location(
            byproduct_lines.lot_id
        )
        for move_line in byproduct_lines:
            if self._is_any_finished_serial_already_produced(
                move_line.lot_id, excluded_sml=move_line, suspect_lots=suspect_lots
            ):
                raise UserError(
                    _(
                        "The serial number %(number)s used for byproduct %(product_name)s has already been produced",
                        number=move_line.lot_id.name,
                        product_name=move_line.product_id.name,
                    )
                )

        self._check_consumed_serials_are_not_reused()

    def _check_consumed_serials_are_not_reused(self):
        self.check_singleton()
        consumed_sn_ids = []
        sn_error_msg = {}
        for move in self.move_raw_ids:
            if move.has_tracking != "serial" or not move.picked:
                continue
            for move_line in move.move_line_ids:
                if (
                    not move_line.picked
                    or move_line.product_uom_id.is_zero(move_line.quantity)
                    or not move_line.lot_id
                ):
                    continue
                sml_sn = move_line.lot_id
                message = _(
                    "The serial number %(number)s used for component %(component)s has already been consumed",
                    number=sml_sn.name,
                    component=move_line.product_id.name,
                )
                consumed_sn_ids.append(sml_sn.id)
                sn_error_msg[sml_sn.id] = message
                duplicates = (
                    self.move_raw_ids.move_line_ids.filtered(
                        lambda ml, sml_sn=sml_sn: ml.quantity and ml.lot_id == sml_sn
                    )
                    - move_line
                )
                if duplicates:
                    raise UserError(message)

        if not consumed_sn_ids:
            return

        consumed_qties = dict(
            self.env["stock.move.line"]._read_group(
                [
                    ("lot_id", "in", consumed_sn_ids),
                    ("quantity", "=", 1),
                    ("state", "=", "done"),
                    ("location_dest_id.usage", "=", "production"),
                    ("production_id", "!=", False),
                ],
                ["lot_id"],
                ["quantity:sum"],
            )
        )
        if not consumed_qties:
            return

        returned_qties = defaultdict(
            float,
            self.env["stock.move.line"]._read_group(
                [
                    ("lot_id", "in", [lot.id for lot in consumed_qties]),
                    ("quantity", "=", 1),
                    ("state", "=", "done"),
                    ("location_id.usage", "=", "production"),
                    "|",
                    ("move_id.production_id", "=", False),
                    "&",
                    ("move_id.production_id", "!=", False),
                    ("move_id.production_id.product_id", "=", self.product_id.id),
                ],
                ["lot_id"],
                ["quantity:sum"],
            ),
        )

        for lot, consumed_qty in consumed_qties.items():
            if consumed_qty - returned_qties[lot] > 0:
                raise UserError(sn_error_msg[lot.id])

    def _get_serials_produced_in_production_location(self, lots):
        if not lots:
            return self.env["stock.lot"]
        groups = self.env["stock.move.line"]._read_group(
            [
                ("lot_id", "in", lots.ids),
                ("quantity", "=", 1),
                ("state", "=", "done"),
                ("location_id.usage", "=", "production"),
                ("move_id.unbuild_id", "=", False),
            ],
            ["lot_id"],
        )
        return self.env["stock.lot"].union(*(lot for [lot] in groups))

    def _is_any_finished_serial_already_produced(
        self, lots, excluded_sml=None, suspect_lots=None
    ):
        if not lots:
            return False
        excluded_sml = excluded_sml or self.env["stock.move.line"]
        domain = [
            ("lot_id", "in", lots.ids),
            ("quantity", "=", 1),
            ("state", "=", "done"),
        ]
        co_prod_move_lines = self.move_finished_ids.move_line_ids - excluded_sml
        domain_unbuild = domain + [
            ("production_id", "=", False),
            ("location_dest_id.usage", "=", "production"),
        ]
        if suspect_lots is not None and not (lots & suspect_lots):
            duplicates = 0
        else:
            duplicates = self.env["stock.move.line"].search_count(
                domain
                + [
                    ("location_id.usage", "=", "production"),
                    ("move_id.unbuild_id", "=", False),
                ]
            )
        if duplicates:
            duplicates_unbuild = self.env["stock.move.line"].search_count(
                domain_unbuild + [("move_id.unbuild_id", "!=", False)]
            )
            removed = self.env["stock.move.line"].search_count(
                [
                    ("lot_id", "in", lots.ids),
                    ("state", "=", "done"),
                    ("location_id.usage", "!=", "inventory"),
                    ("location_dest_id.usage", "=", "inventory"),
                ]
            )
            unremoved = self.env["stock.move.line"].search_count(
                [
                    ("lot_id", "in", lots.ids),
                    ("state", "=", "done"),
                    ("location_id.usage", "=", "inventory"),
                    ("location_dest_id.usage", "!=", "inventory"),
                ]
            )
            if not (
                (duplicates_unbuild or removed)
                and duplicates - duplicates_unbuild - removed + unremoved == 0
            ):
                return True
        duplicates = co_prod_move_lines.filtered(
            lambda ml: ml.quantity and ml.lot_id.id in lots.ids
        )
        return bool(duplicates)

    def _check_split_merge_allowed(self, merge=False, split=False):
        if not merge and not split:
            return True
        ope_str = (merge and _("merged")) or _("split")
        if any(production.state not in ("draft", "confirmed") for production in self):
            _debug.logic(
                "split_merge_refused",
                reason="state",
                merge=merge,
                split=split,
                productions=self,
            )
            raise UserError(
                _(
                    "Only manufacturing orders in either a draft or confirmed state can be %s.",
                    ope_str,
                )
            )
        if any(not production.bom_id for production in self):
            _debug.logic(
                "split_merge_refused", reason="no_bom", merge=merge, productions=self
            )
            raise UserError(
                _(
                    "Only manufacturing orders with a Bill of Materials can be %s.",
                    ope_str,
                )
            )
        if split:
            return True

        if len(self) < 2:
            _debug.logic("split_merge_refused", reason="too_few", productions=self)
            raise UserError(_("You need at least two production orders to merge them."))
        products = {(production.product_id, production.bom_id) for production in self}
        if len(products) > 1:
            raise UserError(
                _(
                    "You can only merge manufacturing orders of identical products with same BoM."
                )
            )
        additional_raw_ids = self.mapped("move_raw_ids").filtered(
            lambda move: not move.bom_line_id
        )
        additional_byproduct_ids = self.mapped("move_byproduct_ids").filtered(
            lambda move: not move.byproduct_id
        )
        if additional_raw_ids or additional_byproduct_ids:
            raise UserError(
                _(
                    "You can only merge manufacturing orders with no additional components or by-products."
                )
            )
        if len(set(self.mapped("state"))) > 1:
            raise UserError(_("You can only merge manufacturing with the same state."))
        if len(set(self.mapped("picking_type_id"))) > 1:
            raise UserError(
                _("You can only merge manufacturing with the same operation type")
            )
        return True

    def _prepare_merge_orig_links(self):
        origs = defaultdict(dict)
        for move in self.move_raw_ids:
            if not move.move_orig_ids:
                continue
            origs[move.bom_line_id.id].setdefault("move_orig_ids", set()).update(
                move.move_orig_ids.ids
            )
        for vals in origs.values():
            if not vals.get("move_orig_ids"):
                continue
            vals["move_orig_ids"] = [Command.set(vals["move_orig_ids"])]
        return origs

    def _update_quantities(self):
        self.check_singleton()
        if self.product_tracking in ("lot", "serial") and not self.lot_producing_ids:
            self.action_generate_serial()

        if not self.qty_producing:
            self.qty_producing = self.product_qty - self.qty_produced
            self._update_moves_from_qty_producing()

        self._mark_byproducts_as_produced()

    def _add_report_action(self, report_actions, report_xmlid, docids, **kwargs):
        action = self.env.ref(report_xmlid).report_action(
            docids, config=False, **kwargs
        )
        clean_action(action, self.env)
        report_actions.append(action)
        return action

    _LOT_LABEL_REPORTS = {
        "pdf": "stock.action_report_lot_label",
        "zpl": "stock.label_lot_template",
    }
    _PRODUCT_LABEL_REPORTS = {
        "pdf": "mrp.action_report_finished_product",
        "zpl": "mrp.label_manufacture_template",
    }

    def _add_actions_autoprint_by_format(
        self, report_actions, productions, format_field, reports, docids_of
    ):
        by_format = productions.grouped(lambda p: p.picking_type_id[format_field])
        for print_format, grouped_productions in by_format.items():
            report_xmlid = reports.get(print_format)
            if not report_xmlid:
                continue
            self._add_report_action(
                report_actions, report_xmlid, docids_of(grouped_productions)
            )

    def _prepare_actions_autoprint_done(self):
        report_actions = []
        productions_to_print = self.filtered(
            lambda p: p.picking_type_id.auto_print_done_production_order
        )
        if productions_to_print:
            self._add_report_action(
                report_actions,
                "mrp.action_report_production_order",
                productions_to_print.ids,
            )
        self._add_actions_autoprint_by_format(
            report_actions,
            self.filtered(
                lambda p: p.picking_type_id.auto_print_done_mrp_product_labels
            ),
            "mrp_product_label_to_print",
            self._PRODUCT_LABEL_REPORTS,
            lambda productions: productions.ids,
        )
        if self.env.user.has_group("mrp.group_mrp_reception_report"):
            reception_reports_to_print = self.filtered(
                lambda p: (
                    p.picking_type_id.auto_print_mrp_reception_report
                    and p.picking_type_id.code == "mrp_operation"
                    and p.move_finished_ids.move_dest_ids
                )
            )
            if reception_reports_to_print:
                action = self._add_report_action(
                    report_actions,
                    "stock.stock_reception_report_action",
                    reception_reports_to_print,
                )
                action["context"] = dict(
                    {"default_production_ids": reception_reports_to_print.ids},
                    **self.env.context,
                )
            reception_labels_to_print = self.filtered(
                lambda p: (
                    p.picking_type_id.auto_print_mrp_reception_report_labels
                    and p.picking_type_id.code == "mrp_operation"
                )
            )
            if reception_labels_to_print:
                moves_to_print = (
                    reception_labels_to_print.move_finished_ids.move_dest_ids
                )
                if moves_to_print:
                    quantities = ",".join(
                        str(qty)
                        for qty in moves_to_print.mapped(
                            lambda m: math.ceil(m.product_uom_qty)
                        )
                    )
                    self._add_report_action(
                        report_actions,
                        "stock.label_picking",
                        moves_to_print,
                        data={
                            "docids": moves_to_print.ids,
                            "quantity": quantities,
                        },
                    )
        if self.env.user.has_group("stock.group_production_lot"):
            self._add_actions_autoprint_by_format(
                report_actions,
                self.filtered(
                    lambda p: (
                        p.picking_type_id.auto_print_done_mrp_lot
                        and p.move_finished_ids.move_line_ids.lot_id
                    )
                ),
                "done_mrp_lot_label_to_print",
                self._LOT_LABEL_REPORTS,
                lambda productions: (
                    productions.move_finished_ids.move_line_ids.lot_id.ids
                ),
            )
        return report_actions

    def _prepare_action_autoprint_generated_lot(self, lot_id):
        self.check_singleton()
        report_xmlid = self._LOT_LABEL_REPORTS.get(
            self.picking_type_id.generated_mrp_lot_label_to_print
        )
        if not report_xmlid:
            return None
        return self._add_report_action([], report_xmlid, lot_id.id)

    def _prepare_actions_autoprint_generated_lots(self):
        actions = []
        self._add_actions_autoprint_by_format(
            actions,
            self.filtered(lambda p: p.picking_type_id.auto_print_generated_mrp_lot),
            "generated_mrp_lot_label_to_print",
            self._LOT_LABEL_REPORTS,
            lambda productions: productions.lot_producing_ids.ids,
        )
        return actions

    def _prepare_finished_extra_vals(self):
        self.check_singleton()
        return {}

    def action_view_label_layout(self):
        view = self.env.ref("stock.product_label_layout_form_picking")
        return {
            "name": _("Choose Labels Layout"),
            "type": "ir.actions.act_window",
            "res_model": "product.label.layout",
            "views": [(view.id, "form")],
            "target": "new",
            "context": {
                "default_product_ids": self.move_finished_ids.product_id.ids,
                "default_move_ids": self.move_finished_ids.ids,
                "default_move_quantity": "move",
            },
        }

    def action_view_label_type(self):
        move_line_ids = self.move_finished_ids.mapped("move_line_ids")
        if (
            self.env.user.has_group("stock.group_production_lot")
            and move_line_ids.lot_id
        ):
            view = self.env.ref("stock.picking_label_type_form")
            return {
                "name": _("Choose Type of Labels To Print"),
                "type": "ir.actions.act_window",
                "res_model": "picking.label.type",
                "views": [(view.id, "form")],
                "target": "new",
                "context": {"default_production_ids": self.ids},
            }
        return self.action_view_label_layout()

    def action_start(self):
        self.check_singleton()
        if self.state == "confirmed":
            self.state = "progress"

    def action_view_serial_numbers(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.action_stock_lot_form"
        )
        action["domain"] = [("id", "in", self.lot_producing_ids.ids)]
        action["name"] = _("Serial Numbers")
        action["context"] = {
            "create": False,
            "delete": False,
        }
        return action

    def action_clear_lot_producing_ids(self):
        self.lot_producing_ids = [Command.clear()]
        self.qty_producing = 0
        self._update_moves_from_qty_producing(False)

    def _track_subtype(self, init_values):
        self.check_singleton()
        if "state" in init_values and self.state == "confirmed":
            return self.env.ref("mrp.mrp_mo_in_confirmed")
        elif "state" in init_values and self.state == "progress":
            return self.env.ref("mrp.mrp_mo_in_progress")
        elif "state" in init_values and self.state == "to_close":
            return self.env.ref("mrp.mrp_mo_in_to_close")
        elif "state" in init_values and self.state == "done":
            return self.env.ref("mrp.mrp_mo_in_done")
        elif "state" in init_values and self.state == "cancel":
            return self.env.ref("mrp.mrp_mo_in_cancelled")
        return super()._track_subtype(init_values)

    def _get_order_line_values(self, child_field=False):
        default_data = super()._get_order_line_values(child_field)
        new_default_data = self.env["stock.move"]._get_product_catalog_lines_data(
            parent_record=self
        )

        return {**default_data, **new_default_data}

    def _get_product_catalog_order_data(self, products, **kwargs):
        product_catalog = super()._get_product_catalog_order_data(products, **kwargs)
        for product in products:
            product_catalog[product.id] |= self._get_product_price_and_data(product)
        return product_catalog

    def _get_product_price_and_data(self, product):
        return {"price": product.standard_price}

    def _get_domain_product_catalog(self):
        return super()._get_domain_product_catalog() & Domain("type", "=", "consu")

    def _update_catalog_line_quantity(self, line, quantity, **kwargs):
        line.product_uom_qty = quantity

    def _prepare_new_catalog_line_vals(self, product_id, quantity, **kwargs):
        return {"product_id": product_id, "product_uom_qty": quantity}

    def _is_display_stock_in_catalog(self):
        return True

    def _post_run_manufacture(self, post_production_values):
        note_subtype_id = self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_note")
        from_report = self.browse()
        origins = []
        for production, procurement in zip(self, post_production_values, strict=True):
            if group_id := procurement.values.get("production_group_id"):
                production.production_group_id.parent_ids = [Command.link(group_id)]
            orderpoint = production.orderpoint_id
            if (
                orderpoint
                and orderpoint.create_uid.id == api.SUPERUSER_ID
                and orderpoint.trigger == "manual"
            ):
                from_report |= production
            elif orderpoint:
                origins.append((production.id, orderpoint))
            else:
                origins.append(
                    (production.id, production.move_dest_ids.raw_material_production_id)
                )
        if from_report:
            from_report._message_post_batch(
                dict.fromkeys(
                    from_report.ids,
                    _(
                        "This production order has been created from Replenishment Report."
                    ),
                ),
                message_type="comment",
                subtype_id=note_subtype_id,
            )
        _debug.pipeline(
            "post_run_manufacture",
            productions=self,
            from_report=len(from_report),
            origins=len(origins),
        )
        self._message_post_origin_links(origins, subtype_id=note_subtype_id)
        return True

    def _resequence_workorders(self):
        self.check_singleton()
        workorders = self.workorder_ids._sorted_by_routing()
        phantom_workorders = workorders.filtered(
            lambda wo: wo.operation_id.bom_id.type == "phantom"
        )
        for index_wo, wo in enumerate(
            phantom_workorders + (workorders - phantom_workorders)
        ):
            _debug.logic(
                "workorder_resequenced",
                production=self.id,
                workorder=wo.id,
                previous=wo.sequence,
                sequence=index_wo,
            )
            wo.sequence = index_wo
        return True

    def _track_get_fields(self):
        res = super()._track_get_fields()
        if res:
            res = OrderedSet(topological_sort(self.fields_get(res, ("depends",))))
        return res

    def _add_reference(self, reference):
        self.check_singleton()
        self.reference_ids = [
            Command.link(stock_reference.id) for stock_reference in reference
        ]

    def _remove_reference(self, reference):
        self.check_singleton()
        self.reference_ids = [
            Command.unlink(stock_reference.id) for stock_reference in reference
        ]
