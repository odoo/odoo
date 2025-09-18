import json
import math
from ast import literal_eval
from collections import defaultdict
from datetime import date, timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command, Domain
from odoo.tools import OrderedSet, format_date, format_datetime, groupby
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.tools.misc import clean_context
from odoo.tools.translate import _

from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from odoo.addons.web.controllers.utils import clean_action


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Transfer"
    _order = "priority desc, date_planned asc, id desc"

    def _default_picking_type_id(self):
        picking_type_code = self.env.context.get("restricted_picking_type_code")
        if picking_type_code:
            picking_types = self.env["stock.picking.type"].search(
                [
                    ("code", "=", picking_type_code),
                    ("company_id", "=", self.env.company.id),
                ],
            )
            return picking_types[:1].id

    name = fields.Char(
        string="Reference",
        default="/",
        readonly=True,
        copy=False,
        index="trigram",
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
        readonly=True,
        check_company=True,
        copy=False,
        index="btree_not_null",
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
        readonly=True,
        check_company=True,
        copy=False,
        index="btree_not_null",
        help="If this picking was created as a return of another picking, this field links to the original picking.",
    )
    return_ids = fields.One2many(
        comodel_name="stock.picking",
        inverse_name="return_id",
        string="Returns",
    )
    return_count = fields.Integer(
        string="# Returns",
        compute="_compute_return_count",
        compute_sudo=False,
    )

    move_type = fields.Selection(
        selection=[
            ("direct", "As soon as possible"),
            ("one", "When all products are ready"),
        ],
        string="Shipping Policy",
        required=True,
        compute="_compute_move_type",
        store=True,
        precompute=True,
        readonly=False,
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
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
        help=" * Draft: The transfer is not confirmed yet. Reservation doesn't apply.\n"
        " * Waiting another operation: This transfer is waiting for another operation before being ready.\n"
        ' * Waiting: The transfer is waiting for the availability of some products.\n(a) The shipping policy is "As soon as possible": no product could be reserved.\n(b) The shipping policy is "When all products are ready": not all the products could be reserved.\n'
        ' * Ready: The transfer is ready to be processed.\n(a) The shipping policy is "As soon as possible": at least one product has been reserved.\n(b) The shipping policy is "When all products are ready": all product have been reserved.\n'
        " * Done: The transfer has been processed.\n"
        " * Cancelled: The transfer has been cancelled.",
    )
    reference_ids = fields.Many2many(
        related="move_ids.reference_ids",
        comodel_name="stock.reference",
        string="References",
        readonly=True,
    )
    priority = fields.Selection(
        selection=PROCUREMENT_PRIORITIES,
        string="Priority",
        default="0",
        help="Products will be reserved first for the transfers with the highest priorities.",
    )
    date_planned = fields.Datetime(
        string="Scheduled Date",
        default=fields.Datetime.now,
        compute="_compute_date_planned",
        store=True,
        inverse="_set_date_planned",
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
        default=False,
        compute="_compute_has_deadline_issue",
        store=True,
        help="Is late or will be late depending on the deadline and scheduled date",
    )
    date_done = fields.Datetime(
        string="Date of Transfer",
        copy=False,
        help="Date at which the transfer has been processed or cancelled.",
    )
    date_delay_alert = fields.Datetime(
        string="Delay Alert Date",
        compute="_compute_date_delay_alert",
        search="_search_date_delay_alert",
    )
    json_popover = fields.Char(
        string="JSON data for the popover widget",
        compute="_compute_json_popover",
    )
    location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Source Location",
        required=True,
        compute="_compute_location_id",
        store=True,
        precompute=True,
        readonly=False,
        check_company=True,
    )
    location_dest_id = fields.Many2one(
        comodel_name="stock.location",
        string="Destination Location",
        required=True,
        compute="_compute_location_id",
        store=True,
        precompute=True,
        readonly=False,
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
        compute="_has_scrap_move",
    )
    picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Operation Type",
        required=True,
        default=_default_picking_type_id,
        index=True,
        tracking=True,
    )
    warehouse_address_id = fields.Many2one(
        related="picking_type_id.warehouse_id.partner_id",
        comodel_name="res.partner",
    )
    picking_type_code = fields.Selection(
        related="picking_type_id.code",
        readonly=True,
    )
    picking_type_entire_packs = fields.Boolean(
        related="picking_type_id.show_entire_packs",
    )
    use_create_lots = fields.Boolean(
        related="picking_type_id.use_create_lots",
    )
    use_existing_lots = fields.Boolean(
        related="picking_type_id.use_existing_lots",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contact",
        check_company=True,
        index="btree_not_null",
    )
    company_id = fields.Many2one(
        related="picking_type_id.company_id",
        comodel_name="res.company",
        string="Company",
        store=True,
        readonly=True,
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        default=lambda self: self.env.user,
        domain=lambda self: [
            ("all_group_ids", "in", self.env.ref("stock.group_stock_user").id),
        ],
        copy=False,
        tracking=True,
    )
    move_line_ids = fields.One2many(
        comodel_name="stock.move.line",
        inverse_name="picking_id",
        string="Operations",
    )
    packages_count = fields.Integer(
        string="Packages Count",
        compute="_compute_packages_count",
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
        check_company=True,
        index="btree_not_null",
        help="When validating the transfer, the products will be assigned to this owner.",
    )
    printed = fields.Boolean(string="Printed", copy=False)
    signature = fields.Image(
        string="Signature",
        attachment=True,
        copy=False,
        help="Signature",
    )
    is_signed = fields.Boolean(
        string="Is Signed",
        compute="_compute_is_signed",
    )
    is_locked = fields.Boolean(
        default=True,
        copy=False,
        help="When the picking is not done this allows changing the "
        "initial demand. When the picking is done this allows "
        "changing the done quantities.",
    )
    is_date_editable = fields.Boolean(
        "Is Scheduled Date Editable",
        compute="_compute_is_date_editable",
    )

    weight_bulk = fields.Float(
        string="Bulk Weight",
        compute="_compute_bulk_weight",
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

    # Used to search on pickings
    product_id = fields.Many2one(
        related="move_ids.product_id",
        comodel_name="product.product",
        string="Product",
        readonly=True,
    )
    lot_id = fields.Many2one(
        related="move_line_ids.lot_id",
        comodel_name="stock.lot",
        string="Lot/Serial Number",
        readonly=True,
    )
    # TODO: delete this field `show_operations`
    show_operations = fields.Boolean(related="picking_type_id.show_operations")
    show_lots_text = fields.Boolean(compute="_compute_show_lots_text")
    has_tracking = fields.Boolean(compute="_compute_has_tracking")
    products_availability = fields.Char(
        string="Product Availability",
        compute="_compute_products_availability",
        help="Latest product availability status of the picking",
    )
    products_availability_state = fields.Selection(
        selection=[
            ("available", "Available"),
            ("expected", "Expected"),
            ("late", "Late"),
        ],
        compute="_compute_products_availability",
        search="_search_products_availability_state",
    )

    picking_properties = fields.Properties(
        string="Properties",
        definition="picking_type_id.picking_properties_definition",
        copy=True,
    )
    show_next_pickings = fields.Boolean(compute="_compute_show_next_pickings")
    search_date_category = fields.Selection(
        selection=[
            ("before", "Before"),
            ("yesterday", "Yesterday"),
            ("today", "Today"),
            ("day_1", "Tomorrow"),
            ("day_2", "The day after tomorrow"),
            ("after", "After"),
        ],
        string="Date Category",
        store=False,
        readonly=True,
        search="_search_date_category",
    )
    partner_country_id = fields.Many2one(
        related="partner_id.country_id",
        comodel_name="res.country",
    )
    picking_warning_text = fields.Text(
        string="Picking Instructions",
        compute="_compute_picking_warning_text",
        help="Internal instructions for the partner or its parent company as set by the user.",
    )

    _name_uniq = models.Constraint(
        "unique(name, company_id)",
        "Reference must be unique per company!",
    )

    def _compute_has_tracking(self):
        for picking in self:
            picking.has_tracking = any(
                m.has_tracking != "none" for m in picking.move_ids
            )

    def _compute_is_date_editable(self):
        for picking in self:
            if picking.state in ["done", "cancel"]:
                picking.is_date_editable = not picking.is_locked
            else:
                picking.is_date_editable = True

    @api.depends("picking_type_id")
    def _compute_move_type(self):
        for record in self:
            record.move_type = record.picking_type_id.move_type

    @api.depends("date_deadline", "date_planned")
    def _compute_has_deadline_issue(self):
        for picking in self:
            picking.has_deadline_issue = (
                picking.date_deadline and picking.date_deadline < picking.date_planned
            ) or False

    def _search_date_category(self, operator, value):
        if operator != "in":
            return NotImplemented
        return Domain.OR(
            self.date_category_to_domain("date_planned", item) for item in value
        )

    @api.depends("move_ids.date_delay_alert")
    def _compute_date_delay_alert(self):
        date_delay_alert_data = self.env["stock.move"]._read_group(
            [("id", "in", self.move_ids.ids), ("date_delay_alert", "!=", False)],
            ["picking_id"],
            ["date_delay_alert:max"],
        )
        date_delay_alert_data = {
            picking.id: date_delay_alert
            for picking, date_delay_alert in date_delay_alert_data
        }
        for picking in self:
            picking.date_delay_alert = date_delay_alert_data.get(picking.id, False)

    @api.depends("signature")
    def _compute_is_signed(self):
        for picking in self:
            picking.is_signed = picking.signature

    @api.depends(
        "state",
        "picking_type_code",
        "date_planned",
        "move_ids",
        "move_ids.forecast_availability",
        "move_ids.date_planned_forecast",
    )
    def _compute_products_availability(self):
        pickings = self.filtered(
            lambda picking: picking.state in ("waiting", "confirmed", "assigned")
            and picking.picking_type_code in ("outgoing", "internal"),
        )
        pickings.products_availability_state = "available"
        pickings.products_availability = _("Available")
        other_pickings = self - pickings
        other_pickings.products_availability = False
        other_pickings.products_availability_state = False

        all_moves = pickings.move_ids
        # Force to prefetch more than 1000 by 1000
        all_moves._fields["forecast_availability"].compute_value(all_moves)
        for picking in pickings:
            # In case of draft the behavior of forecast_availability is different : if forecast_availability < 0 then there is a issue else not.
            if any(
                move.product_id.uom_id.compare(
                    move.forecast_availability,
                    0 if move.state == "draft" else move.product_qty,
                )
                == -1
                for move in picking.move_ids
            ):
                picking.products_availability = _("Not Available")
                picking.products_availability_state = "late"
            else:
                forecast_date = max(
                    picking.move_ids.filtered("date_planned_forecast").mapped(
                        "date_planned_forecast",
                    ),
                    default=False,
                )
                if forecast_date:
                    picking.products_availability = _(
                        "Exp %s",
                        format_date(self.env, forecast_date),
                    )
                    picking.products_availability_state = (
                        "late"
                        if picking.date_planned and picking.date_planned < forecast_date
                        else "expected"
                    )

    @api.depends(
        "move_line_ids",
        "picking_type_id.use_create_lots",
        "picking_type_id.use_existing_lots",
        "state",
    )
    def _compute_show_lots_text(self):
        group_production_lot_enabled = self.env.user.has_group(
            "stock.group_production_lot",
        )
        for picking in self:
            if (
                not picking.move_line_ids
                and not picking.picking_type_id.use_create_lots
            ):
                picking.show_lots_text = False
            elif (
                group_production_lot_enabled
                and picking.picking_type_id.use_create_lots
                and not picking.picking_type_id.use_existing_lots
                and picking.state != "done"
            ):
                picking.show_lots_text = True
            else:
                picking.show_lots_text = False

    def _compute_json_popover(self):
        picking_no_alert = self.filtered(
            lambda p: p.state in ("done", "cancel") or not p.date_delay_alert,
        )
        picking_no_alert.json_popover = False
        for picking in self - picking_no_alert:
            picking.json_popover = json.dumps(
                {
                    "popoverTemplate": "stock.PopoverStockRescheduling",
                    "date_delay_alert": format_datetime(
                        self.env,
                        picking.date_delay_alert,
                        dt_format=False,
                    ),
                    "late_elements": [
                        {
                            "id": late_move.id,
                            "name": late_move.display_name,
                            "model": late_move._name,
                        }
                        for late_move in picking.move_ids.filtered(
                            lambda m: m.date_delay_alert,
                        ).move_orig_ids._delay_alert_get_documents()
                    ],
                },
            )

    @api.depends("move_type", "move_ids.state", "move_ids.picking_id")
    def _compute_state(self):
        """State of a picking depends on the state of its related stock.move
        - Draft: only used for "planned pickings"
        - Waiting: if the picking is not ready to be sent so if
          - (a) no quantity could be reserved at all or if
          - (b) some quantities could be reserved and the shipping policy is "deliver all at once"
        - Waiting another move: if the picking is waiting for another move
        - Ready: if the picking is ready to be sent so if:
          - (a) all quantities are reserved or if
          - (b) some quantities could be reserved and the shipping policy is "as soon as possible"
          - (c) it's an incoming picking
        - Done: if the picking is done.
        - Cancelled: if the picking is cancelled
        """
        picking_moves_state_map = defaultdict(dict)
        picking_move_lines = defaultdict(set)
        for move in self.env["stock.move"].search([("picking_id", "in", self.ids)]):
            picking_id = move.picking_id
            move_state = move.state
            picking_moves_state_map[picking_id.id].update(
                {
                    "any_draft": picking_moves_state_map[picking_id.id].get(
                        "any_draft",
                        False,
                    )
                    or move_state == "draft",
                    "all_cancel": picking_moves_state_map[picking_id.id].get(
                        "all_cancel",
                        True,
                    )
                    and move_state == "cancel",
                    "all_cancel_done": picking_moves_state_map[picking_id.id].get(
                        "all_cancel_done",
                        True,
                    )
                    and move_state in ("cancel", "done"),
                    "all_done_are_scrapped": picking_moves_state_map[picking_id.id].get(
                        "all_done_are_scrapped",
                        True,
                    )
                    and (
                        move.location_dest_usage == "inventory"
                        if move_state == "done"
                        else True
                    ),
                    "any_cancel_and_not_scrapped": picking_moves_state_map[
                        picking_id.id
                    ].get("any_cancel_and_not_scrapped", False)
                    or (
                        move_state == "cancel"
                        and move.location_dest_usage != "inventory"
                    ),
                },
            )
            picking_move_lines[picking_id.id].add(move.id)
        for picking in self:
            picking_id = (picking.ids and picking.ids[0]) or picking.id
            if (
                not picking_moves_state_map[picking_id]
                or picking_moves_state_map[picking_id]["any_draft"]
            ):
                picking.state = "draft"
            elif picking_moves_state_map[picking_id]["all_cancel"]:
                picking.state = "cancel"
            elif picking_moves_state_map[picking_id]["all_cancel_done"]:
                if (
                    picking_moves_state_map[picking_id]["all_done_are_scrapped"]
                    and picking_moves_state_map[picking_id][
                        "any_cancel_and_not_scrapped"
                    ]
                ):
                    picking.state = "cancel"
                else:
                    picking.state = "done"
            else:
                if picking.location_id.should_bypass_reservation() and all(
                    m.procure_method == "make_to_stock" for m in picking.move_ids
                ):
                    picking.state = "assigned"
                else:
                    relevant_move_state = (
                        self.env["stock.move"]
                        .browse(picking_move_lines[picking_id])
                        ._get_relevant_state_among_moves()
                    )
                    if relevant_move_state == "partially_available":
                        picking.state = "assigned"
                    else:
                        picking.state = relevant_move_state

    @api.depends("move_ids.state", "move_ids.date", "move_type")
    def _compute_date_planned(self):
        for picking in self:
            if not picking.id:
                continue
            moves_dates = picking.move_ids.filtered(
                lambda move: move.state not in ("done", "cancel"),
            ).mapped("date")
            if picking.move_type == "direct":
                picking.date_planned = min(
                    moves_dates,
                    default=picking.date_planned or fields.Datetime.now(),
                )
            else:
                picking.date_planned = max(
                    moves_dates,
                    default=picking.date_planned or fields.Datetime.now(),
                )

    @api.depends(
        "move_line_ids",
        "move_line_ids.result_package_id",
        "move_line_ids.product_uom_id",
        "move_line_ids.quantity",
    )
    def _compute_bulk_weight(self):
        picking_weights = defaultdict(float)
        res_groups = self.env["stock.move.line"]._read_group(
            [
                ("picking_id", "in", self.ids),
                ("product_id", "!=", False),
                ("result_package_id", "=", False),
            ],
            ["picking_id", "product_id", "product_uom_id", "quantity"],
            ["__count"],
        )
        for picking, product, product_uom, quantity, count in res_groups:
            picking_weights[picking.id] += (
                count
                * product_uom._compute_quantity(quantity, product.uom_id)
                * product.weight
            )
        for picking in self:
            picking.weight_bulk = picking_weights[picking.id]

    @api.depends(
        "move_line_ids.result_package_id",
        "move_line_ids.result_package_id.shipping_weight",
        "move_line_ids.result_package_id.outermost_package_id.shipping_weight",
        "weight_bulk",
    )
    def _compute_shipping_weight(self):
        for picking in self:
            # if shipping weight is not assigned => default to calculated product weight
            packages_weight = (
                picking.move_line_ids.result_package_id.sudo()._get_weight(picking.id)
            )

            shipping_weight = picking.weight_bulk
            relevant_packages = (
                picking.move_line_ids.result_package_id.outermost_package_id
            )
            children_packages_by_pack = (
                relevant_packages._get_all_children_package_dest_ids()[0]
            )
            for package in relevant_packages:
                if package.shipping_weight:
                    shipping_weight += package.shipping_weight
                else:
                    shipping_weight += package.package_type_id.base_weight
                    shipping_weight += sum(
                        packages_weight.get(pack, 0)
                        for pack in self.env["stock.package"].browse(
                            children_packages_by_pack.get(package),
                        )
                    )

            picking.shipping_weight = shipping_weight

    def _compute_shipping_volume(self):
        for picking in self:
            volume = 0
            for move in picking.move_ids:
                volume += (
                    move.product_uom._compute_quantity(
                        move.quantity,
                        move.product_id.uom_id,
                    )
                    * move.product_id.volume
                )
            picking.shipping_volume = volume

    @api.depends("move_ids.date_deadline", "move_type")
    def _compute_date_deadline(self):
        for picking in self:
            if picking.move_type == "direct":
                picking.date_deadline = min(
                    picking.move_ids.filtered("date_deadline").mapped("date_deadline"),
                    default=False,
                )
            else:
                picking.date_deadline = max(
                    picking.move_ids.filtered("date_deadline").mapped("date_deadline"),
                    default=False,
                )

    def _set_date_planned(self):
        for picking in self:
            if picking.state == "cancel":
                raise UserError(
                    _("You cannot change the Scheduled Date on a cancelled transfer."),
                )
            if picking.state == "done":
                continue
            picking.move_ids.write({"date": picking.date_planned})

    def _has_scrap_move(self):
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

    def _compute_packages_count(self):
        done_pickings = self.filtered(lambda picking: picking.state == "done")
        other_pickings = self - done_pickings

        packages_by_pick = defaultdict(int)
        # Cannot _read_group() as picking_ids isn't stored, nor grouped() because multiple pickings per package
        packages = self.env["stock.package"].search(
            [("picking_ids", "in", other_pickings.ids)],
        )
        for pack in packages:
            for picking in pack.picking_ids:
                packages_by_pick[picking] += 1

        histories_by_pick = self.env["stock.package.history"]._read_group(
            [("picking_ids", "in", done_pickings.ids)],
            ["picking_ids"],
            ["__count"],
        )
        histories_by_pick = dict(histories_by_pick)

        for picking in done_pickings:
            picking.packages_count = histories_by_pick.get(picking, 0)
        for picking in other_pickings:
            picking.packages_count = packages_by_pick.get(picking, 0)

    @api.depends("state", "move_ids.product_uom_qty", "picking_type_code")
    def _compute_show_check_availability(self):
        """According to `picking.show_check_availability`, the "check availability" button will be
        displayed in the form view of a picking.
        """
        for picking in self:
            if picking.state not in ("confirmed", "waiting", "assigned"):
                picking.show_check_availability = False
                continue
            if all(
                m.picked or m.product_uom_qty == m.quantity for m in picking.move_ids
            ):
                picking.show_check_availability = False
                continue
            picking.show_check_availability = any(
                move.state in ("waiting", "confirmed", "partially_available")
                and move.product_uom.compare(move.product_uom_qty, 0)
                for move in picking.move_ids
            )

    @api.depends("state", "move_ids", "picking_type_id")
    def _compute_show_allocation(self):
        self.show_allocation = False
        if not self.env.user.has_group("stock.group_reception_report"):
            return
        for picking in self:
            picking.show_allocation = picking._get_show_allocation(
                picking.picking_type_id,
            )

    @api.depends("picking_type_id", "partner_id")
    def _compute_location_id(self):
        for picking in self:
            if picking.state in ("cancel", "done") or picking.return_id:
                continue
            picking = picking.with_company(picking.company_id)
            if picking.picking_type_id:
                location_src = picking.picking_type_id.default_location_src_id
                if location_src.usage == "supplier" and picking.partner_id:
                    location_src = picking.partner_id.property_stock_supplier
                location_dest = picking.picking_type_id.default_location_dest_id
                if location_dest.usage == "customer" and picking.partner_id:
                    location_dest = picking.partner_id.property_stock_customer
                picking.location_id = location_src.id
                picking.location_dest_id = location_dest.id

    @api.depends("return_ids")
    def _compute_return_count(self):
        for picking in self:
            picking.return_count = len(picking.return_ids)

    @api.depends("partner_id.name", "partner_id.parent_id.name")
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

    def _get_next_transfers(self):
        next_pickings = self.move_ids.move_dest_ids.picking_id
        return next_pickings.filtered(lambda p: p not in self.return_ids)

    @api.depends("move_ids.move_dest_ids")
    def _compute_show_next_pickings(self):
        self.show_next_pickings = len(self._get_next_transfers()) != 0

    def _search_products_availability_state(self, operator, value):
        if operator != "in":
            return NotImplemented

        invalid_states = ("done", "cancel", "draft")
        if False in value:
            return [
                "|",
                ("state", "in", invalid_states),
                *self._search_products_availability_state("in", value - {False}),
            ]
        value = (
            set(self._fields["products_availability_state"].get_values(self.env))
            & value
        )
        if not value:
            return Domain.FALSE

        def _get_comparison_date(move):
            return move.picking_id.date_planned

        def _filter_picking_moves(picking):
            try:
                return picking.move_ids._match_searched_availability(
                    operator,
                    value,
                    _get_comparison_date,
                )
            except UserError:
                # invalid value for search
                return False

        pickings = (
            self.env["stock.picking"]
            .search([("state", "not in", invalid_states)], order="id")
            .filtered(_filter_picking_moves)
        )
        return Domain("id", "in", pickings.ids)

    def _get_show_allocation(self, picking_type_id):
        """Helper method for computing "show_allocation" value.
        Separated out from _compute function so it can be reused in other models (e.g. batch).
        """
        if not picking_type_id or picking_type_id.code == "outgoing":
            return False
        lines = self.move_ids.filtered(
            lambda m: m.product_id.is_storable and m.state != "cancel",
        )
        if lines:
            allowed_states = ["confirmed", "partially_available", "waiting"]
            if self[0].state == "done":
                allowed_states += ["assigned"]
            wh_location_ids = self.env["stock.location"]._search(
                [
                    (
                        "id",
                        "child_of",
                        picking_type_id.warehouse_id.view_location_id.id,
                    ),
                    ("usage", "!=", "supplier"),
                ],
            )
            if self.env["stock.move"].search_count(
                [
                    ("state", "in", allowed_states),
                    ("product_qty", ">", 0),
                    ("location_id", "in", wh_location_ids),
                    ("picking_id", "not in", self.ids),
                    ("product_id", "in", lines.product_id.ids),
                    "|",
                    ("move_orig_ids", "=", False),
                    ("move_orig_ids", "in", lines.ids),
                ],
                limit=1,
            ):
                return True

    @api.model
    def get_empty_list_help(self, help_message):
        return self.env["ir.ui.view"]._render_template(
            "stock.help_message_template",
            {
                "picking_type_code": self.env.context.get(
                    "restricted_picking_type_code",
                )
                or self.picking_type_code,
            },
        )

    @api.model
    def _search_date_delay_alert(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        return [("move_ids.date_delay_alert", operator, value)]

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
                parent_path = [
                    int(loc_id) for loc_id in ml.location_id.parent_path.split("/")[:-1]
                ]
                if self.location_id.id not in parent_path:
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

    @api.model_create_multi
    def create(self, vals_list):
        date_planneds = []
        for vals in vals_list:
            defaults = self.default_get(["name", "picking_type_id"])
            picking_type = self.env["stock.picking.type"].browse(
                vals.get("picking_type_id", defaults.get("picking_type_id")),
            )
            if (
                vals.get("name", "/") == "/"
                and defaults.get("name", "/") == "/"
                and vals.get("picking_type_id", defaults.get("picking_type_id"))
            ):
                if picking_type.sequence_id:
                    vals["name"] = picking_type.sequence_id.next_by_id()

            # make sure to write `schedule_date` *after* the `stock.move` creation in
            # order to get a determinist execution of `_set_date_planned`
            date_planneds.append(vals.pop("date_planned", False))

        pickings = super().create(vals_list)

        for picking, date_planned in zip(pickings, date_planneds):
            if date_planned:
                picking.with_context(mail_notrack=True).write(
                    {"date_planned": date_planned},
                )
        pickings._autoconfirm_picking()

        return pickings

    def write(self, vals):
        if vals.get("picking_type_id") and any(
            picking.state in ("done", "cancel") for picking in self
        ):
            raise UserError(
                _(
                    "Changing the operation type of this record is forbidden at this point.",
                ),
            )
        if vals.get("picking_type_id"):
            picking_type = self.env["stock.picking.type"].browse(
                vals.get("picking_type_id"),
            )
            for picking in self:
                if picking.picking_type_id != picking_type:
                    picking.name = picking_type.sequence_id.next_by_id()
                    vals["location_id"] = picking_type.default_location_src_id.id
                    vals["location_dest_id"] = picking_type.default_location_dest_id.id
        res = super().write(vals)
        if vals.get("date_done"):
            self.filtered(lambda p: p.state == "done").move_ids.date = vals["date_done"]
        if vals.get("signature"):
            for picking in self:
                picking._attach_sign()
        # Change locations of moves if those of the picking change
        after_vals = {}
        if vals.get("location_id"):
            after_vals["location_id"] = vals["location_id"]
        if vals.get("location_dest_id"):
            after_vals["location_dest_id"] = vals["location_dest_id"]
        if "partner_id" in vals:
            after_vals["partner_id"] = vals["partner_id"]
        if after_vals:
            self.move_ids.filtered(
                lambda move: move.location_dest_usage != "inventory",
            ).write(after_vals)
        if vals.get("move_ids"):
            self._autoconfirm_picking()

        return res

    def unlink(self):
        self.move_ids._action_cancel()
        self.with_context(
            prefetch_fields=False,
        ).move_ids.unlink()  # Checks if moves are not done
        return super().unlink()

    def do_print_picking(self):
        self.write({"printed": True})
        return self.env.ref("stock.action_report_picking").report_action(self)

    def action_confirm(self):
        self._check_company()
        # call `_action_confirm` on every draft move
        self.move_ids.filtered(lambda move: move.state == "draft")._action_confirm()

        # run scheduler for moves forecasted to not have enough in stock
        self.move_ids.filtered(
            lambda move: move.state not in ("draft", "cancel", "done"),
        )._trigger_scheduler()
        return True

    def action_assign(self):
        """Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        @return: True
        """
        self.filtered(lambda picking: picking.state == "draft").action_confirm()
        moves = self.move_ids.filtered(
            lambda move: move.state not in ("draft", "cancel", "done"),
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
        moves._action_assign()
        return True

    def action_cancel(self):
        self.move_ids._action_cancel()
        self.write({"is_locked": True})
        self.filtered(lambda x: not x.move_ids).state = "cancel"
        return True

    def action_detailed_operations(self):
        view_id = self.env.ref("stock.view_stock_move_line_detailed_operation_tree").id
        return {
            "name": _("Detailed Operations"),
            "view_mode": "list",
            "type": "ir.actions.act_window",
            "res_model": "stock.move.line",
            "views": [(view_id, "list")],
            "domain": [("id", "in", self.move_line_ids.ids)],
            "context": {
                "sml_specific_default": True,
                "default_picking_id": self.id,
                "default_location_id": self.location_id.id,
                "default_location_dest_id": self.location_dest_id.id,
                "default_company_id": self.company_id.id,
                "show_lots_text": self.show_lots_text,
                "picking_code": self.picking_type_code,
                "create": self.state not in ("done", "cancel"),
            },
        }

    def action_next_transfer(self):
        next_transfers = self._get_next_transfers()

        if len(next_transfers) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "stock.picking",
                "views": [[False, "form"]],
                "res_id": next_transfers.id,
            }
        return {
            "name": _("Next Transfers"),
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "views": [[False, "list"], [False, "form"]],
            "domain": [("id", "in", next_transfers.ids)],
        }

    def _action_done(self):
        """Call `_action_done` on the `stock.move` of the `stock.picking` in `self`.
        This method makes sure every `stock.move.line` is linked to a `stock.move` by either
        linking them to an existing one or a newly created one.

        If the context key `cancel_backorder` is present, backorders won't be created.

        :return: True
        :rtype: bool
        """
        self._check_company()

        todo_moves = self.move_ids.filtered(
            lambda self: self.state
            in ["draft", "waiting", "partially_available", "assigned", "confirmed"],
        )
        for picking in self:
            if picking.owner_id:
                picking.move_ids.write({"restrict_partner_id": picking.owner_id.id})
                picking.move_line_ids.write({"owner_id": picking.owner_id.id})
        todo_moves._action_done(
            cancel_backorder=self.env.context.get("cancel_backorder"),
        )
        self.write({"date_done": fields.Datetime.now(), "priority": "0"})

        # if incoming/internal moves make other confirmed/partially_available moves available, assign them
        done_incoming_moves = self.filtered(
            lambda p: p.picking_type_id.code in ("incoming", "internal"),
        ).move_ids.filtered(lambda m: m.state == "done")
        done_incoming_moves._trigger_assign()

        self._send_confirmation_email()
        return True

    def _send_confirmation_email(self):
        subtype_id = self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_comment")
        for stock_pick in self.filtered(
            lambda p: p.company_id.stock_move_email_validation
            and p.picking_type_id.code == "outgoing",
        ):
            delivery_template = (
                stock_pick.company_id.stock_mail_confirmation_template_id
            )
            stock_pick.with_context(force_send=True).message_post_with_source(
                delivery_template,
                email_layout_xmlid="mail.mail_notification_light",
                subtype_id=subtype_id,
            )

    def _get_entire_pack_location_dest(self, move_line_ids):
        location_dest_ids = move_line_ids.mapped("location_dest_id")
        if len(location_dest_ids) > 1:
            return False
        return location_dest_ids.id

    def _get_lot_move_lines_for_sanity_check(
        self,
        none_done_picking_ids,
        separate_pickings=True,
    ):
        """Get all move_lines with tracked products that need to be checked over in the sanity check.
        :param none_done_picking_ids: Set of all pickings ids that have no quantity set on any move_line.
        :param separate_pickings: Indicates if pickings should be checked independently for lot/serial numbers or not.
        """

        def get_relevant_move_line_ids(none_done_picking_ids, picking):
            # Get all move_lines if picking has no quantity set, otherwise only get the move_lines with some quantity set.
            if picking.id in none_done_picking_ids:
                return picking.move_line_ids.filtered(
                    lambda ml: ml.product_id and ml.product_id.tracking != "none",
                ).ids
            return get_line_with_done_qty_ids(picking.move_line_ids)

        def get_line_with_done_qty_ids(move_lines):
            # Get only move_lines that has some quantity set.
            return move_lines.filtered(
                lambda ml: ml.product_id
                and ml.product_id.tracking != "none"
                and ml.picked
                and ml.product_uom_id.compare(ml.quantity, 0),
            ).ids

        if separate_pickings:
            # If pickings are checked independently, get full/partial move_lines depending if each picking has no quantity set.
            lines_to_check_ids = [
                line_id
                for picking in self
                for line_id in get_relevant_move_line_ids(
                    none_done_picking_ids,
                    picking,
                )
            ]
        else:
            # If pickings are checked as one (like in a batch), then get only the move_lines with quantity across all pickings if there is at least one.
            if any(picking.id not in none_done_picking_ids for picking in self):
                lines_to_check_ids = get_line_with_done_qty_ids(self.move_line_ids)
            else:
                lines_to_check_ids = self.move_line_ids.filtered(
                    lambda ml: ml.product_id and ml.product_id.tracking != "none",
                ).ids

        return self.env["stock.move.line"].browse(lines_to_check_ids)

    def _sanity_check(self, separate_pickings=True):
        """Sanity check for `button_validate()`
        :param separate_pickings: Indicates if pickings should be checked independently for lot/serial numbers or not.
        """
        pickings_without_lots = self.browse()
        products_without_lots = self.env["product.product"]
        pickings_without_moves = self.filtered(
            lambda p: not p.move_ids and not p.move_line_ids,
        )
        precision_digits = self.env["decimal.precision"].precision_get("Product Unit")

        no_quantities_done_ids = set()
        pickings_without_quantities = self.env["stock.picking"]
        for picking in self:
            has_pick = any(
                move.picked and move.state not in ("done", "cancel")
                for move in picking.move_ids
            )
            if all(
                float_is_zero(move.quantity, precision_digits=precision_digits)
                for move in picking.move_ids.filtered(
                    lambda m: m.state not in ("done", "cancel")
                    and (not has_pick or m.picked),
                )
            ):
                pickings_without_quantities |= picking

        pickings_using_lots = self.filtered(
            lambda p: p.picking_type_id.use_create_lots
            or p.picking_type_id.use_existing_lots,
        )
        if pickings_using_lots:
            lines_to_check = pickings_using_lots._get_lot_move_lines_for_sanity_check(
                no_quantities_done_ids,
                separate_pickings,
            )
            for line in lines_to_check:
                if not line.lot_name and not line.lot_id:
                    pickings_without_lots |= line.picking_id
                    products_without_lots |= line.product_id

        if not self._should_show_transfers():
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
            if pickings_without_lots:
                message += _(
                    "\n\nTransfers %(transfer_list)s: You need to supply a Lot/Serial number for products %(product_list)s.",
                    transfer_list=pickings_without_lots.mapped("name"),
                    product_list=products_without_lots.mapped("display_name"),
                )
            if message:
                raise UserError(message.lstrip())

    def do_unreserve(self):
        self.move_ids._do_unreserve()

    def button_validate(self):
        self = self.filtered(lambda p: p.state != "done")
        draft_picking = self.filtered(lambda p: p.state == "draft")
        draft_picking.action_confirm()
        for move in draft_picking.move_ids:
            if move.product_uom.is_zero(move.quantity) and not move.product_uom.is_zero(
                move.product_uom_qty,
            ):
                move.quantity = move.product_uom_qty

        # Sanity checks.
        if not self.env.context.get("skip_sanity_check", False):
            self._sanity_check()

        # Run the pre-validation wizards. Processing a pre-validation wizard should work on the
        # moves and/or the context and never call `_action_done`.
        if not self.env.context.get("button_validate_picking_ids"):
            self = self.with_context(button_validate_picking_ids=self.ids)
        res = self._pre_action_done_hook()
        if res is not True:
            return res

        # Call `_action_done`.
        pickings_not_to_backorder = self.filtered(
            lambda p: p.picking_type_id.create_backorder == "never",
        )
        if self.env.context.get("picking_ids_not_to_backorder"):
            pickings_not_to_backorder |= self.browse(
                self.env.context["picking_ids_not_to_backorder"],
            ).filtered(lambda p: p.picking_type_id.create_backorder != "always")
        pickings_to_backorder = self - pickings_not_to_backorder
        if pickings_not_to_backorder:
            pickings_not_to_backorder.with_context(cancel_backorder=True)._action_done()
        if pickings_to_backorder:
            pickings_to_backorder.with_context(cancel_backorder=False)._action_done()
        report_actions = self._get_autoprint_report_actions()
        another_action = False
        if self.env.user.has_group("stock.group_reception_report"):
            pickings_show_report = self.filtered(
                lambda p: p.picking_type_id.auto_show_reception_report,
            )
            lines = pickings_show_report.move_ids.filtered(
                lambda m: m.product_id.is_storable
                and m.state != "cancel"
                and m.quantity
                and not m.move_dest_ids,
            )
            if lines:
                # don't show reception report if all already assigned/nothing to assign
                wh_location_ids = self.env["stock.location"]._search(
                    [
                        (
                            "id",
                            "child_of",
                            pickings_show_report.picking_type_id.warehouse_id.view_location_id.ids,
                        ),
                        ("usage", "!=", "supplier"),
                    ],
                )
                if self.env["stock.move"].search_count(
                    [
                        (
                            "state",
                            "in",
                            ["confirmed", "partially_available", "waiting", "assigned"],
                        ),
                        ("product_qty", ">", 0),
                        ("location_id", "in", wh_location_ids),
                        ("move_orig_ids", "=", False),
                        ("picking_id", "not in", pickings_show_report.ids),
                        ("product_id", "in", lines.product_id.ids),
                    ],
                    limit=1,
                ):
                    action = pickings_show_report.action_view_reception_report()
                    action["context"] = {
                        "default_picking_ids": pickings_show_report.ids,
                    }
                    if not report_actions:
                        return action
                    another_action = action
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
        if all(m.product_uom.is_zero(m.quantity) for m in self.move_ids):
            raise UserError(
                _(
                    "%s: Nothing to split. Fill the quantities you want in a new transfer in the done quantities",
                    self.display_name,
                ),
            )
        if all(
            m.product_uom.compare(m.quantity, m.product_uom_qty) == 0
            for m in self.move_ids
        ):
            raise UserError(
                _(
                    "%s: Nothing to split, all demand is done. For split you need at least one line not fully fulfilled",
                    self.display_name,
                ),
            )
        if any(
            m.product_uom.compare(m.quantity, m.product_uom_qty) > 0
            for m in self.move_ids
        ):
            raise UserError(
                _(
                    "%s: Can't split: quantities done can't be above demand",
                    self.display_name,
                ),
            )

        moves = self.move_ids.filtered(
            lambda m: m.state not in ("done", "cancel") and m.quantity != 0,
        )
        backorder_moves = moves._create_backorder()
        backorder_moves += self.move_ids.filtered(lambda m: m.quantity == 0)
        self._create_backorder(backorder_moves=backorder_moves)

    def _pre_action_done_hook(self):
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
                picking.move_ids.picked = True
        if not self.env.context.get("skip_backorder"):
            pickings_to_backorder = self._check_backorder()
            if pickings_to_backorder:
                return pickings_to_backorder._action_generate_backorder_wizard(
                    show_transfers=self._should_show_transfers(),
                )
        return True

    def _action_generate_backorder_wizard(self, show_transfers=False):
        view = self.env.ref("stock.view_backorder_confirmation")
        return {
            "name": _("Create Backorder?"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "stock.backorder.confirmation",
            "views": [(view.id, "form")],
            "view_id": view.id,
            "target": "new",
            "context": dict(
                self.env.context,
                default_show_transfers=show_transfers,
                default_pick_ids=[(4, p.id) for p in self],
            ),
        }

    def action_toggle_is_locked(self):
        self.ensure_one()
        self.is_locked = not self.is_locked
        return True

    def action_put_in_pack(
        self,
        *,
        package_id=False,
        package_type_id=False,
        package_name=False,
    ):
        self.ensure_one()
        if self.env.context.get("sml_specific_default"):
            self = self.with_context(clean_context(self.env.context))
        if self.state not in ("done", "cancel"):
            return self.move_line_ids.action_put_in_pack(
                package_id=package_id,
                package_type_id=package_type_id,
                package_name=package_name,
            )

    @api.model
    def date_category_to_domain(self, field_name, date_category):
        """
        Given a date category, returns a list of tuples of operator and value
        that can be used in a domain to filter records based on their scheduled date.

        Args:
            date_category (str): The date category to use for the computation.
                Allowed values are:
                * "before"
                * "yesterday"
                * "today"
                * "day_1"
                * "day_2"
                * "after"

        Returns:
            a list of tuples:
                each tuple consists of an operator and a value that can be used in
                a domain to filter records based on their scheduled date.
                The operator can be "<" or ">=". The value is a datetime object.
                If an incorrect date category is passed, this method returns None.
        """
        start_today = fields.Datetime.context_timestamp(
            self.env.user,
            fields.Datetime.now(),
        ).replace(hour=0, minute=0, second=0, microsecond=0)

        start_today = start_today.astimezone(pytz.UTC).replace(tzinfo=None)

        start_yesterday = start_today + timedelta(days=-1)
        start_day_1 = start_today + timedelta(days=1)
        start_day_2 = start_today + timedelta(days=2)
        start_day_3 = start_today + timedelta(days=3)

        date_category_to_search_domain = {
            "before": [(field_name, "<", start_yesterday)],
            "yesterday": [
                (field_name, ">=", start_yesterday),
                (field_name, "<", start_today),
            ],
            "today": [(field_name, ">=", start_today), (field_name, "<", start_day_1)],
            "day_1": [(field_name, ">=", start_day_1), (field_name, "<", start_day_2)],
            "day_2": [(field_name, ">=", start_day_2), (field_name, "<", start_day_3)],
            "after": [(field_name, ">=", start_day_3)],
        }

        return date_category_to_search_domain.get(date_category)

    def button_scrap(self):
        self.ensure_one()
        view = self.env.ref("stock.stock_scrap_form_view2")
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

    def action_add_entire_packs(self, package_ids):
        self.ensure_one()
        if self.state not in ("done", "cancel"):
            all_packages = self.env["stock.package"].search(
                [("id", "child_of", package_ids)],
            )
            all_package_ids = set(all_packages.ids)
            # Remove existing move lines that already pulled from these packages, as using them fully now.
            self.move_line_ids.filtered(
                lambda ml: ml.package_id.id in all_package_ids,
            ).unlink()
            move_line_vals = self._prepare_entire_pack_move_line_vals(all_packages)
            pack_move_lines = self.env["stock.move.line"].create(move_line_vals)
            pack_move_lines._apply_putaway_strategy()
            # Need to set the right package dest for now fully contained packages
            self.move_line_ids.result_package_id._apply_package_dest_for_entire_packs(
                allowed_package_ids=all_package_ids,
            )
            return True
        return False

    def action_see_move_scrap(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_stock_scrap")
        scraps = self.env["stock.scrap"].search([("picking_id", "=", self.id)])
        action["domain"] = [("id", "in", scraps.ids)]
        action["context"] = dict(self.env.context, create=False)
        return action

    def action_see_packages(self):
        self.ensure_one()
        return {
            "name": self.env._("Packages"),
            "res_model": "stock.package",
            "view_mode": "list,kanban,form",
            "views": [
                (self.env.ref("stock.stock_package_view_list_editable").id, "list"),
                (False, "kanban"),
                (False, "form"),
            ],
            "type": "ir.actions.act_window",
            "domain": [("picking_ids", "in", self.ids)],
            "context": {
                "picking_ids": self.ids,
                "location_id": self.location_id.id,
                "can_add_entire_packs": self.picking_type_code != "incoming",
                "search_default_main_packages": True,
            },
        }

    def action_see_package_histories(self):
        self.ensure_one()
        return {
            "name": self.env._("Packages"),
            "res_model": "stock.package.history",
            "view_mode": "list",
            "views": [(False, "list")],
            "type": "ir.actions.act_window",
            "domain": [("picking_ids", "=", self.id)],
            "context": {
                "search_default_main_packages": 1,
            },
        }

    def action_picking_move_tree(self):
        action = self.env["ir.actions.actions"]._for_xml_id("stock.stock_move_action")
        action["views"] = [
            (self.env.ref("stock.view_picking_move_tree").id, "list"),
        ]
        action["context"] = self.env.context
        action["domain"] = [("picking_id", "in", self.ids)]
        return action

    def action_view_reception_report(self):
        return self.env["ir.actions.actions"]._for_xml_id(
            "stock.stock_reception_action",
        )

    def action_open_label_layout(self):
        view = self.env.ref("stock.product_label_layout_form_picking")
        return {
            "name": _("Choose Labels Layout"),
            "type": "ir.actions.act_window",
            "res_model": "product.label.layout",
            "views": [(view.id, "form")],
            "target": "new",
            "context": {
                "default_product_ids": self.move_ids.product_id.ids,
                "default_move_ids": self.move_ids.ids,
                "default_move_quantity": "move",
            },
        }

    def action_open_label_type(self):
        if (
            self.env.user.has_group("stock.group_production_lot")
            and self.move_line_ids.lot_id
        ):
            view = self.env.ref("stock.picking_label_type_form")
            return {
                "name": _("Choose Type of Labels To Print"),
                "type": "ir.actions.act_window",
                "res_model": "picking.label.type",
                "views": [(view.id, "form")],
                "target": "new",
                "context": {"default_picking_ids": self.ids},
            }
        return self.action_open_label_layout()

    def action_see_returns(self):
        self.ensure_one()
        if len(self.return_ids) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "stock.picking",
                "views": [[False, "form"]],
                "res_id": self.return_ids.id,
            }
        return {
            "name": _("Returns"),
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "views": [[False, "list"], [False, "form"]],
            "domain": [("id", "in", self.return_ids.ids)],
        }

    def _add_reference(self, reference=False):
        """Link the given references to the list of references."""
        self.ensure_one()
        self.move_ids.reference_ids = [
            Command.link(stock_reference.id) for stock_reference in reference
        ]

    def _attach_sign(self):
        """Render the delivery report in pdf and attach it to the picking in `self`."""
        self.ensure_one()
        report = self.env["ir.actions.report"]._render_qweb_pdf(
            "stock.action_report_delivery",
            self.id,
        )
        filename = "%s_signed_delivery_slip" % self.name
        if self.partner_id:
            message = _("Order signed by %s", self.partner_id.name)
        else:
            message = _("Order signed")
        self.message_post(
            attachments=[("%s.pdf" % filename, report[0])],
            body=message,
        )
        return True

    def _autoconfirm_picking(self):
        """Automatically run `action_confirm` on `self` if one of the
        picking's move was added after the initial
        call to `action_confirm`. Note that `action_confirm` will only work on draft moves.
        """
        for picking in self:
            if picking.state in ("done", "cancel"):
                continue
            if not picking.move_ids:
                continue
            if any(move.additional for move in picking.move_ids):
                picking.action_confirm()
        to_confirm = self.move_ids.filtered(lambda m: m.state == "draft" and m.quantity)
        to_confirm._action_confirm()

    @api.model
    def calculate_date_category(self, datetime):
        """
        Assigns given datetime to one of the following categories:
        - "before"
        - "yesterday"
        - "today"
        - "day_1" (tomorrow)
        - "day_2" (the day after tomorrow)
        - "after"

        The categories are based on current user's timezone (e.g. "today" will last
        between 00:00 and 23:59 local time). The datetime itself is assumed to be
        in UTC. If the datetime is falsy, this function returns "".
        """
        start_today = fields.Datetime.context_timestamp(
            self.env.user,
            fields.Datetime.now(),
        ).replace(hour=0, minute=0, second=0, microsecond=0)

        start_yesterday = start_today + timedelta(days=-1)
        start_day_1 = start_today + timedelta(days=1)
        start_day_2 = start_today + timedelta(days=2)
        start_day_3 = start_today + timedelta(days=3)

        date_category = ""

        if datetime:
            datetime = datetime.astimezone(pytz.UTC)
            if datetime < start_yesterday:
                date_category = "before"
            elif datetime >= start_yesterday and datetime < start_today:
                date_category = "yesterday"
            elif datetime >= start_today and datetime < start_day_1:
                date_category = "today"
            elif datetime >= start_day_1 and datetime < start_day_2:
                date_category = "day_1"
            elif datetime >= start_day_2 and datetime < start_day_3:
                date_category = "day_2"
            else:
                date_category = "after"

        return date_category

    def _create_backorder_picking(self):
        self.ensure_one()
        return self.copy(
            {
                "name": "/",
                "move_ids": [],
                "move_line_ids": [],
                "backorder_id": self.id,
            },
        )

    def _create_backorder(self, backorder_moves=None):
        """This method is called when the user chose to create a backorder. It will create a new
        picking, the backorder, and move the stock.moves that are not `done` or `cancel` into it.
        """
        backorders = self.env["stock.picking"]
        bo_to_assign = self.env["stock.picking"]
        for picking in self:
            if backorder_moves:
                moves_to_backorder = backorder_moves.filtered(
                    lambda m: m.picking_id == picking,
                )
            else:
                moves_to_backorder = picking._get_moves_to_backorder()
            moves_to_backorder._recompute_state()
            if moves_to_backorder:
                backorder_picking = picking._create_backorder_picking()
                moves_to_backorder.write(
                    {"picking_id": backorder_picking.id, "picked": False},
                )
                moves_to_backorder.mapped("move_line_ids").write(
                    {"picking_id": backorder_picking.id},
                )
                backorders |= backorder_picking
                backorder_picking.user_id = False
                picking.message_post(
                    body=_(
                        "The backorder %s has been created.",
                        backorder_picking._get_html_link(),
                    ),
                )
                if backorder_picking.picking_type_id.reservation_method == "at_confirm":
                    bo_to_assign |= backorder_picking
        if bo_to_assign:
            bo_to_assign.action_assign()
        return backorders

    @api.model
    def get_action_click_graph(self):
        return self._get_action("stock.action_picking_tree_graph")

    def _get_action(self, action_xmlid):
        action = self.env["ir.actions.actions"]._for_xml_id(action_xmlid)
        context = dict(self.env.context)
        context.update(literal_eval(action["context"]))
        action["context"] = context

        action["help"] = self.env["ir.ui.view"]._render_template(
            "stock.help_message_template",
            {
                "picking_type_code": context.get("restricted_picking_type_code")
                or self.picking_type_code,
            },
        )

        return action

    @api.model
    def get_action_picking_tree_incoming(self):
        return self._get_action("stock.action_picking_tree_incoming")

    @api.model
    def get_action_picking_tree_outgoing(self):
        return self._get_action("stock.action_picking_tree_outgoing")

    @api.model
    def get_action_picking_tree_internal(self):
        return self._get_action("stock.action_picking_tree_internal")

    def _get_autoprint_report_actions(self):
        report_actions = []
        pickings_to_print = self.filtered(
            lambda p: p.picking_type_id.auto_print_delivery_slip,
        )
        if pickings_to_print:
            action = self.env.ref("stock.action_report_delivery").report_action(
                pickings_to_print.ids,
                config=False,
            )
            clean_action(action, self.env)
            report_actions.append(action)
        pickings_print_return_slip = self.filtered(
            lambda p: p.picking_type_id.auto_print_return_slip,
        )
        if pickings_print_return_slip:
            action = self.env.ref("stock.return_label_report").report_action(
                pickings_print_return_slip.ids,
                config=False,
            )
            clean_action(action, self.env)
            report_actions.append(action)

        if self.env.user.has_group("stock.group_reception_report"):
            reception_reports_to_print = self.filtered(
                lambda p: p.picking_type_id.auto_print_reception_report
                and p.picking_type_id.code != "outgoing"
                and p.move_ids.move_dest_ids,
            )
            if reception_reports_to_print:
                action = self.env.ref(
                    "stock.stock_reception_report_action",
                ).report_action(reception_reports_to_print, config=False)
                clean_action(action, self.env)
                report_actions.append(action)
            reception_labels_to_print = self.filtered(
                lambda p: p.picking_type_id.auto_print_reception_report_labels
                and p.picking_type_id.code != "outgoing",
            )
            if reception_labels_to_print:
                moves_to_print = reception_labels_to_print.move_ids.move_dest_ids
                if moves_to_print:
                    # needs to be string to support python + js calls to report
                    quantities = ",".join(
                        str(qty)
                        for qty in moves_to_print.mapped(
                            lambda m: math.ceil(m.product_uom_qty),
                        )
                    )
                    data = {
                        "docids": moves_to_print.ids,
                        "quantity": quantities,
                    }
                    action = self.env.ref("stock.label_picking").report_action(
                        moves_to_print,
                        data=data,
                        config=False,
                    )
                    clean_action(action, self.env)
                    report_actions.append(action)
        pickings_print_product_label = self.filtered(
            lambda p: p.picking_type_id.auto_print_product_labels,
        )
        pickings_by_print_formats = pickings_print_product_label.grouped(
            lambda p: p.picking_type_id.product_label_format,
        )
        for print_format in pickings_print_product_label.picking_type_id.mapped(
            "product_label_format",
        ):
            pickings = pickings_by_print_formats.get(print_format)
            wizard = self.env["product.label.layout"].create(
                {
                    "product_ids": pickings.move_ids.product_id.ids,
                    "move_ids": pickings.move_ids.ids,
                    "move_quantity": "move",
                    "print_format": pickings.picking_type_id.product_label_format,
                },
            )
            action = wizard.process()
            if action:
                clean_action(action, self.env)
                report_actions.append(action)
        if self.env.user.has_group("stock.group_production_lot"):
            pickings_print_lot_label = self.filtered(
                lambda p: p.picking_type_id.auto_print_lot_labels
                and p.move_line_ids.lot_id,
            )
            pickings_by_print_formats = pickings_print_lot_label.grouped(
                lambda p: p.picking_type_id.lot_label_format,
            )
            for print_format in pickings_print_lot_label.picking_type_id.mapped(
                "lot_label_format",
            ):
                pickings = pickings_by_print_formats.get(print_format)
                wizard = self.env["lot.label.layout"].create(
                    {
                        "move_line_ids": pickings.move_line_ids.ids,
                        "label_quantity": (
                            "lots" if "_lots" in print_format else "units"
                        ),
                        "print_format": "4x12" if "4x12" in print_format else "zpl",
                    },
                )
                action = wizard.process()
                if action:
                    clean_action(action, self.env)
                    report_actions.append(action)
        if self.env.user.has_group("stock.group_tracking_lot"):
            pickings_print_packages = self.filtered(
                lambda p: p.picking_type_id.auto_print_packages
                and p.move_line_ids.result_package_id,
            )
            if pickings_print_packages:
                action = self.env.ref(
                    "stock.action_report_picking_packages",
                ).report_action(pickings_print_packages.ids, config=False)
                clean_action(action, self.env)
                report_actions.append(action)
        return report_actions

    def _get_impacted_pickings(self, moves):
        """This function is used in _log_less_quantities_than_expected
        the purpose is to notify a user with all the pickings that are
        impacted by an action on a chained move.
        param: 'moves' contain moves that belong to a common picking.
        return: all the pickings that contain a destination moves
        (direct and indirect) from the moves given as arguments.
        """

        def _explore(impacted_pickings, explored_moves, moves_to_explore):
            for move in moves_to_explore:
                if move not in explored_moves:
                    impacted_pickings |= move.picking_id
                    explored_moves |= move
                    moves_to_explore |= move.move_dest_ids
            moves_to_explore = moves_to_explore - explored_moves
            if moves_to_explore:
                return _explore(impacted_pickings, explored_moves, moves_to_explore)
            return impacted_pickings

        return _explore(self.env["stock.picking"], self.env["stock.move"], moves)

    def _get_moves_to_backorder(self):
        self.ensure_one()
        return self.move_ids.filtered(lambda x: x.state not in ("done", "cancel"))

    def _get_packages_for_print(self):
        package_ids = OrderedSet()
        for picking in self:
            if picking.state == "done":
                package_ids.update(picking.package_history_ids.package_id.ids)
            else:
                package_ids.update(
                    picking.move_line_ids.result_package_id._get_all_package_dest_ids(),
                )
        return self.env["stock.package"].browse(package_ids)

    def _get_report_lang(self):
        return (
            (self.move_ids and self.move_ids[0].partner_id.lang)
            or self.partner_id.lang
            or self.env.lang
        )

    def _get_without_quantities_error_message(self):
        """Returns the error message raised in validation if no quantities are reserved.
        The purpose of this method is to be overridden in case we want to adapt this message.

        :return: Translated error message
        :rtype: str
        """
        return _(
            "Transfer trouble alert! Validating a zero quantity transfer? You're not moving invisible goods around are you?\n"
            "Set some quantities and let's get moving!",
        )

    def _less_quantities_than_expected_add_documents(self, moves, documents):
        return documents

    def _log_activity_get_documents(
        self,
        orig_obj_changes,
        stream_field,
        stream,
        groupby_method=False,
    ):
        """Generic method to log activity. To use with
        _log_activity method. It either log on uppermost
        ongoing documents or following documents. This method
        find all the documents and responsible for which a note
        has to be log. It also generate a rendering_context in
        order to render a specific note by documents containing
        only the information relative to the document it. For example
        we don't want to notify a picking on move that it doesn't
        contain.

        :param dict orig_obj_changes: contain a record as key and the
            change on this record as value.
            eg: {'move_id': (new product_uom_qty, old product_uom_qty)}
        :param str stream_field: It has to be a field of the
            records that are register in the key of 'orig_obj_changes'
            eg: 'move_dest_ids' if we use move as record (previous example)
                - 'UP' if we want to log on the upper most ongoing
                documents.
                - 'DOWN' if we want to log on following documents.
        :param str stream: ``'UP'`` or ``'DOWN'``
        :param groupby_method: Only need when
            stream is 'DOWN', it should group by tuple(object on
            which the activity is log, the responsible for this object)
        """
        if self.env.context.get("skip_activity"):
            return {}
        move_to_orig_object_rel = {
            co: ooc for ooc in orig_obj_changes.keys() for co in ooc[stream_field]
        }
        origin_objects = self.env[list(orig_obj_changes.keys())[0]._name].concat(
            *list(orig_obj_changes.keys()),
        )
        # The purpose here is to group each destination object by
        # (document to log, responsible) no matter the stream direction.
        # example:
        # {'(delivery_picking_1, admin)': stock.move(1, 2)
        #  '(delivery_picking_2, admin)': stock.move(3)}
        visited_documents = {}
        if stream == "DOWN":
            if groupby_method:
                grouped_moves = groupby(
                    origin_objects.mapped(stream_field),
                    key=groupby_method,
                )
            else:
                raise AssertionError(
                    "You have to define a groupby method and pass them as arguments.",
                )
        elif stream == "UP":
            # When using upstream document it is required to define
            # _get_upstream_documents_and_responsibles on
            # destination objects in order to ascend documents.
            grouped_moves = {}
            for visited_move in origin_objects.mapped(stream_field):
                for (
                    document,
                    responsible,
                    visited,
                ) in visited_move._get_upstream_documents_and_responsibles(
                    self.env[visited_move._name],
                ):
                    if grouped_moves.get((document, responsible)):
                        grouped_moves[document, responsible] |= visited_move
                        visited_documents[document, responsible] |= visited
                    else:
                        grouped_moves[document, responsible] = visited_move
                        visited_documents[document, responsible] = visited
            grouped_moves = grouped_moves.items()
        else:
            raise AssertionError("Unknown stream.")

        documents = {}
        for (parent, responsible), moves in grouped_moves:
            if not parent:
                continue
            moves = self.env[moves[0]._name].concat(*moves)
            # Get the note
            rendering_context = {
                move: (orig_object, orig_obj_changes[orig_object])
                for move in moves
                for orig_object in move_to_orig_object_rel[move]
            }
            if visited_documents:
                documents[parent, responsible] = (
                    rendering_context,
                    visited_documents.values(),
                )
            else:
                documents[parent, responsible] = rendering_context
        return documents

    def _log_activity(self, render_method, documents):
        """Log a note for each documents, responsible pair in
        documents passed as argument. The render_method is then
        call in order to use a template and render it with a
        rendering_context.

        :param dict documents: A tuple (document, responsible) as key.
            An activity will be log by key. A rendering_context as value.
            If used with _log_activity_get_documents. In 'DOWN' stream
            cases the rendering_context will be a dict with format:
            {'stream_object': ('orig_object', new_qty, old_qty)}
            'UP' stream will add all the documents browsed in order to
            get the final/upstream document present in the key.
        :param callable render_method: a static function that will generate
            the html note to log on the activity. The render_method should
            use the args:
                - rendering_context dict: value of the documents argument
            the render_method should return a string with an html format
        """
        for (parent, responsible), rendering_context in documents.items():
            note = render_method(rendering_context)
            parent.sudo().activity_schedule(
                "mail.mail_activity_data_warning",
                date.today(),
                note=note,
                user_id=responsible.id,
            )

    def _log_less_quantities_than_expected(self, moves):
        """Log an activity on picking that follow moves. The note
        contains the moves changes and all the impacted picking.

        :param dict moves: a dict with a move as key and tuple with
        new and old quantity as value. eg: {move_1 : (4, 5)}
        """

        def _keys_in_groupby(move):
            """Group by picking and the responsible for the product the
            move.
            """
            return (move.picking_id, move.product_id.responsible_id)

        def _render_note_exception_quantity(rendering_context):
            """:param rendering_context:
            {'move_dest': (move_orig, (new_qty, old_qty))}
            """
            origin_moves = self.env["stock.move"].browse(
                [
                    move.id
                    for move_orig in rendering_context.values()
                    for move in move_orig[0]
                ],
            )
            origin_picking = origin_moves.mapped("picking_id")
            move_dest_ids = self.env["stock.move"].concat(*rendering_context.keys())
            impacted_pickings = origin_picking._get_impacted_pickings(
                move_dest_ids,
            ) - move_dest_ids.mapped("picking_id")
            values = {
                "origin_picking": origin_picking,
                "moves_information": rendering_context.values(),
                "impacted_pickings": impacted_pickings,
            }
            return self.env["ir.qweb"]._render("stock.exception_on_picking", values)

        documents = self._log_activity_get_documents(
            moves,
            "move_dest_ids",
            "DOWN",
            _keys_in_groupby,
        )
        documents = self._less_quantities_than_expected_add_documents(moves, documents)
        self._log_activity(_render_note_exception_quantity, documents)

    def _prepare_entire_pack_move_line_vals(self, packages):
        """Prepares the move line values for every packages within packages and their children that contain products."""
        self.ensure_one()
        move_line_vals = []
        for package_quant in packages.quant_ids:
            move_line_vals.append(
                {
                    "product_id": package_quant.product_id.id,
                    "quantity": package_quant.quantity,
                    "product_uom_id": package_quant.product_uom_id.id,
                    "location_id": package_quant.location_id.id,
                    "location_dest_id": self.location_dest_id.id,
                    "picking_id": self.id,
                    "company_id": self.id,
                    "package_id": package_quant.package_id.id,
                    "result_package_id": package_quant.package_id.id,
                    "lot_id": package_quant.lot_id.id,
                    "owner_id": package_quant.owner_id.id,
                    "is_entire_pack": True,
                },
            )
        return move_line_vals

    def _remove_reference(self, reference):
        """Remove the given references from the list of references."""
        self.ensure_one()
        self.move_ids.reference_ids = [
            Command.unlink(stock_reference.id) for stock_reference in reference
        ]

    def _can_return(self):
        self.ensure_one()
        return self.state == "done"

    def _check_backorder(self):
        prec = self.env["decimal.precision"].precision_get("Product Unit")
        backorder_pickings = self.browse()
        for picking in self:
            if picking.picking_type_id.create_backorder != "ask":
                continue
            if any(
                (move.product_uom_qty and not move.picked)
                or float_compare(
                    move._get_picked_quantity(),
                    move.product_uom_qty,
                    precision_digits=prec,
                )
                < 0
                for move in picking.move_ids
                if move.state != "cancel"
            ):
                backorder_pickings |= picking
        return backorder_pickings

    def _check_entire_pack(self):
        """This function check if entire packs are moved in the picking"""
        for package in self.move_line_ids.package_id:
            pickings = self.move_line_ids.filtered(
                lambda ml: ml.package_id == package,
            ).picking_id
            if (
                pickings._is_single_transfer()
                and pickings._check_move_lines_map_quant_package(package)
            ):
                move_lines_to_pack = pickings.move_line_ids.filtered(
                    lambda ml: ml.package_id == package
                    and not ml.result_package_id
                    and ml.state not in ("done", "cancel"),
                )
                if package.package_type_id.package_use != "reusable":
                    move_lines_to_pack.write(
                        {
                            "result_package_id": package.id,
                            "is_entire_pack": True,
                        },
                    )
        # If we move all packages within a package, we can consider that they keep their container as well
        self.move_line_ids.result_package_id._apply_package_dest_for_entire_packs()

    def _check_move_lines_map_quant_package(self, package):
        return package._check_move_lines_map_quant(
            self.move_line_ids.filtered(
                lambda ml: ml.product_id.is_storable
                and (
                    ml.package_id == package
                    or ml.package_id in package.all_children_package_ids
                ),
            ),
        )

    def _is_single_transfer(self):
        # Overriden for batches.
        return len(self) == 1

    def _is_to_external_location(self):
        self.ensure_one()
        return self.picking_type_code == "outgoing"

    def _should_ignore_backorders(self):
        """Checks if the `create_backorder` setting from the picking type should be ignored."""
        return bool(self.return_id)

    def should_print_delivery_address(self):
        self.ensure_one()
        return (
            self.move_ids
            and (self.move_ids[0].partner_id or self.partner_id)
            and self._is_to_external_location()
        )

    def _should_show_transfers(self):
        """Whether the different transfers should be displayed on the pre action done wizards."""
        return len(self) > 1
