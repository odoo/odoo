import json
from collections import defaultdict
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.libs.intervals import Intervals
from odoo.tools import float_round, format_datetime
from odoo.tools.date_utils import get_intervals_hours

_debug = DebugLog(__name__)


class MrpWorkorder(models.Model):
    _name = "mrp.workorder"
    _description = "Work Order"
    _inherit = ["mixin.resource.scheduling"]
    _order = "sequence, date_start, id"

    OPEN_STATES = ("blocked", "ready", "progress")
    LATE_STATES = ("blocked", "ready")

    @api.model
    def _get_domain_late(self):
        return Domain("state", "in", self.LATE_STATES) & Domain(
            "date_start", "<", fields.Datetime.now()
        )

    def _search_is_late(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        return [("id", operator, self._get_domain_late())]

    @api.depends("state", "date_start")
    def _compute_is_late(self):
        now = fields.Datetime.now()
        for workorder in self:
            workorder.is_late = bool(
                workorder.state in self.LATE_STATES
                and workorder.date_start
                and workorder.date_start < now
            )

    def _default_sequence(self):
        return self.operation_id.sequence or 100

    def _sorted_by_routing(self):
        return self.sorted(lambda workorder: (workorder.sequence, workorder.id))

    def _read_group_workcenter_id(self, workcenters, domain):
        workcenter_ids = self.env.context.get("default_workcenter_id")
        if not workcenter_ids:
            search_domain = self.env["ir.rule"]._get_domain_accessible_records(
                workcenters._name
            )
            workcenter_ids = workcenters.sudo()._search(
                search_domain, order=workcenters._order
            )
        return workcenters.browse(workcenter_ids)

    is_late = fields.Boolean(
        string="Late",
        compute="_compute_is_late",
        search="_search_is_late",
        help="Should have started already.",
    )
    name = fields.Char(
        string="Work Order",
        required=True,
    )
    sequence = fields.Integer(default=_default_sequence)
    barcode = fields.Char(
        compute="_compute_barcode",
        store=True,
    )
    workcenter_id = fields.Many2one(
        comodel_name="mrp.workcenter",
        string="Work Center",
        index=True,
        required=True,
        group_expand="_read_group_workcenter_id",
        check_company=True,
    )
    working_state = fields.Selection(
        related="workcenter_id.working_state",
        string="Workcenter Status",
    )
    product_id = fields.Many2one(related="production_id.product_id")
    product_tracking = fields.Selection(related="product_id.tracking")
    product_uom_id = fields.Many2one(related="production_id.product_uom_id")
    product_variant_attributes = fields.Many2many(
        comodel_name="product.template.attribute.value",
        related="product_id.product_template_attribute_value_ids",
    )
    production_id = fields.Many2one(
        comodel_name="mrp.production",
        string="Manufacturing Order",
        index="btree",
        readonly=True,
        required=True,
        check_company=True,
    )
    production_availability = fields.Selection(
        related="production_id.reservation_state",
        string="Stock Availability",
        readonly=True,
    )
    production_state = fields.Selection(
        related="production_id.state",
        string="Production State",
        readonly=True,
    )
    production_bom_id = fields.Many2one(
        comodel_name="mrp.bom",
        related="production_id.bom_id",
    )
    qty_production = fields.Float(
        related="production_id.product_qty",
        string="Original Production Quantity",
        readonly=True,
    )
    company_id = fields.Many2one(related="production_id.company_id")
    qty_producing = fields.Float(
        string="Currently Produced Quantity",
        digits="Product Unit",
        compute="_compute_qty_producing",
        inverse="_inverse_qty_producing",
    )
    qty_remaining = fields.Float(
        string="Quantity To Be Produced",
        digits="Product Unit",
        compute="_compute_qty_remaining",
    )
    qty_produced = fields.Float(
        string="Quantity Done",
        digits="Product Unit",
        default=0.0,
        copy=False,
        help="The number of products already handled by this work order",
    )
    qty_ready = fields.Float(
        string="Quantity Ready",
        digits="Product Unit",
        compute="_compute_qty_ready",
    )
    is_produced = fields.Boolean(
        string="Has Been Produced",
        compute="_compute_is_produced",
    )
    state = fields.Selection(
        selection=[
            ("blocked", "Blocked"),
            ("ready", "To Do"),
            ("progress", "In Progress"),
            ("done", "Finished"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        compute="_compute_state",
        recursive=True,
        default="ready",
        store=True,
        index=True,
        copy=False,
    )
    reservation_id = fields.Many2one(
        comodel_name="resource.reservation",
        compute="_compute_reservation_id",
        help="Resource reservation booking this workcenter time slot.",
    )
    date_start = fields.Datetime(
        string="Start",
        copy=False,
    )
    date_end = fields.Datetime(
        string="End",
        copy=False,
    )
    duration_expected = fields.Float(
        string="Expected Duration",
        digits=(16, 2),
        compute="_compute_duration_expected",
        store=True,
        readonly=False,
    )
    duration = fields.Float(
        string="Real Duration",
        compute="_compute_durations",
        inverse="_inverse_duration",
        store=True,
        copy=False,
        readonly=False,
        help="Time logged against this work order, in minutes. A timer that is"
        " still running counts for nothing until it is stopped, so this is a"
        " function of the timer lines alone and does not move with the clock.",
    )
    duration_live = fields.Float(
        string="Live Duration",
        compute="_compute_duration_live",
        help="Real duration plus the time accrued so far on a running timer."
        " Equal to Real Duration whenever no timer is running. Technical: read"
        " by the timer widget.",
    )
    duration_unit = fields.Float(
        string="Duration Per Unit",
        compute="_compute_durations",
        store=True,
        readonly=True,
        aggregator="avg",
    )
    duration_percent = fields.Integer(
        string="Duration Deviation (%)",
        compute="_compute_durations",
        store=True,
        readonly=True,
        aggregator="avg",
    )
    progress = fields.Float(
        string="Progress Done (%)",
        digits=(16, 2),
        compute="_compute_progress",
    )

    operation_id = fields.Many2one(
        comodel_name="mrp.routing.workcenter",
        index="btree_not_null",
        check_company=True,
    )
    move_raw_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="workorder_id",
        string="Raw Moves",
        domain=[
            ("raw_material_production_id", "!=", False),
            ("production_id", "=", False),
        ],
    )
    move_finished_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="workorder_id",
        string="Finished Moves",
        domain=[
            ("raw_material_production_id", "=", False),
            ("production_id", "!=", False),
        ],
    )
    move_line_ids = fields.One2many(
        comodel_name="stock.move.line",
        inverse_name="workorder_id",
        string="Moves to Track",
        help="Inventory moves for which you must scan a lot number at this work order",
    )
    finished_lot_ids = fields.Many2many(
        comodel_name="stock.lot",
        related="production_id.lot_producing_ids",
        string="Lot/Serial Numbers",
        readonly=False,
        domain="[('product_id', '=', product_id), ('company_id', '=', company_id)]",
        check_company=True,
    )
    time_ids = fields.One2many(
        comodel_name="mrp.workcenter.productivity",
        inverse_name="workorder_id",
        copy=False,
    )
    is_user_working = fields.Boolean(
        string="Is the Current User Working",
        compute="_compute_working_users",
    )
    working_user_ids = fields.One2many(
        comodel_name="res.users",
        string="Working user on this work order.",
        compute="_compute_working_users",
    )
    last_working_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Last user that worked on this work order.",
        compute="_compute_working_users",
    )
    costs_hour = fields.Float(
        string="Cost per hour",
        default=0.0,
        aggregator="avg",
    )
    cost_mode = fields.Selection(
        selection=[("actual", "Actual"), ("estimated", "Estimated")],
        default="actual",
    )

    scrap_ids = fields.One2many(
        comodel_name="stock.scrap",
        inverse_name="workorder_id",
    )
    scrap_count = fields.Integer(
        string="Scrap Move",
        compute="_compute_scrap_count",
    )
    production_date = fields.Datetime(
        compute="_compute_production_date",
        store=True,
    )
    json_popover = fields.Char(
        string="Popover Data JSON",
        compute="_compute_popover",
    )
    show_json_popover = fields.Boolean(
        string="Show Popover?",
        compute="_compute_popover",
    )
    consumption = fields.Selection(related="production_id.consumption")
    qty_reported_from_previous_wo = fields.Float(
        string="Carried Quantity",
        digits="Product Unit",
        copy=False,
        help="The quantity already produced awaiting allocation in the backorders chain.",
    )
    is_planned = fields.Boolean(related="production_id.is_planned")
    allow_workorder_dependencies = fields.Boolean(
        related="production_id.allow_workorder_dependencies"
    )
    blocked_by_workorder_ids = fields.Many2many(
        comodel_name="mrp.workorder",
        relation="mrp_workorder_dependencies_rel",
        column1="workorder_id",
        column2="blocked_by_id",
        string="Blocked By",
        copy=False,
        domain="[('allow_workorder_dependencies', '=', True), ('id', '!=', id), ('production_id', '=', production_id)]",
    )
    needed_by_workorder_ids = fields.Many2many(
        comodel_name="mrp.workorder",
        relation="mrp_workorder_dependencies_rel",
        column1="blocked_by_id",
        column2="workorder_id",
        string="Blocks",
        copy=False,
        domain="[('allow_workorder_dependencies', '=', True), ('id', '!=', id), ('production_id', '=', production_id)]",
    )

    def _get_qty_ready(self):
        self.check_singleton()
        blockers = self.blocked_by_workorder_ids.filtered(
            lambda wo: wo.state != "cancel"
        )
        if not blockers:
            return self.qty_remaining
        carried = self.qty_produced + self.qty_reported_from_previous_wo
        available = self.qty_remaining + self.qty_produced
        for blocker in blockers:
            available = min(
                available, blocker.qty_produced + blocker.qty_reported_from_previous_wo
            )
        return available - carried

    @api.depends(
        "product_uom_id",
        "blocked_by_workorder_ids.qty_produced",
        "blocked_by_workorder_ids.qty_reported_from_previous_wo",
        "blocked_by_workorder_ids.state",
        "qty_remaining",
        "qty_produced",
        "qty_reported_from_previous_wo",
    )
    def _compute_state(self):
        for workorder in self:
            if not workorder.product_uom_id or workorder.state not in (
                "blocked",
                "ready",
            ):
                continue
            has_qty_ready = (
                workorder.product_uom_id.compare(workorder._get_qty_ready(), 0) > 0
            )
            workorder.state = "ready" if has_qty_ready else "blocked"
            _debug.logic(
                "workorder_state",
                workorder=workorder.id,
                state=workorder.state,
                by="qty_ready" if has_qty_ready else "no_qty_ready",
            )

    DERIVED_STATES = ("blocked",)

    def set_state(self, state):
        if state in self.DERIVED_STATES:
            _debug.logic(
                "workorder_refused",
                reason="derived_state_set",
                state=state,
                workorders=self,
            )
            raise UserError(
                _(
                    "A work order is blocked when the work orders it waits on "
                    "have not produced enough for it to start. It is not a "
                    "status you can set."
                )
            )
        ids_to_update = []
        for wo in self:
            if wo.state == state or "done" in (wo.state, wo.production_state):
                continue
            if wo.state == "progress":
                wo.button_pending()
            elif wo.state == "cancel" and state == "progress":
                wo.write({"state": "ready"})
            ids_to_update.append(wo.id)

        wo_to_update = self.browse(ids_to_update)
        _debug.pipeline(
            "workorder_set_state",
            requested=state,
            workorders=self,
            applied=len(wo_to_update),
        )
        if state == "cancel":
            wo_to_update.action_cancel()
        elif state == "done":
            wo_to_update.action_mark_as_done()
        elif state == "progress":
            wo_to_update.button_start()
        else:
            wo_to_update.write({"state": state})

    @api.depends("production_id.date_start", "date_start")
    def _compute_production_date(self):
        for workorder in self:
            workorder.production_date = (
                workorder.date_start or workorder.production_id.date_start
            )

    @api.depends(
        "production_state",
        "state",
        "date_start",
        "date_end",
        "workcenter_id",
        "reservation_ids.schedule_overlap_count",
        "blocked_by_workorder_ids.date_start",
        "blocked_by_workorder_ids.date_end",
    )
    @api.depends_context("lang")
    def _compute_popover(self):
        conflicted_dict = {}
        occupied_by_id = {}
        if self.ids:
            conflicted_dict = self._get_conflicted_workorder_ids()
            occupied_by_id = self._get_schedule_conflicts_batch()
        for wo in self:
            infos = []
            if not wo.date_start or not wo.date_end or not wo.ids:
                wo.show_json_popover = False
                wo.json_popover = False
                continue
            if wo.state in ("blocked", "ready"):
                previous_wos = wo.blocked_by_workorder_ids
                previous_starts = previous_wos.filtered("date_start").mapped(
                    "date_start"
                )
                previous_finished = previous_wos.filtered("date_end").mapped("date_end")
                prev_start = min(previous_starts) if previous_starts else False
                prev_finished = max(previous_finished) if previous_finished else False
                if (
                    wo.state == "blocked"
                    and prev_start
                    and not (prev_start > wo.date_start)
                ):
                    infos.append(
                        {
                            "color": "text-primary",
                            "msg": _(
                                "Waiting the previous work order, planned from %(start)s to %(end)s",
                                start=format_datetime(
                                    self.env, prev_start, dt_format=False
                                ),
                                end=format_datetime(
                                    self.env, prev_finished, dt_format=False
                                ),
                            ),
                        }
                    )
                if wo.date_end < fields.Datetime.now():
                    infos.append(
                        {
                            "color": "text-warning",
                            "msg": _(
                                "The work order should have already been processed."
                            ),
                        }
                    )
                if prev_start and prev_start > wo.date_start:
                    infos.append(
                        {
                            "color": "text-danger",
                            "msg": _(
                                "Scheduled before the previous work order, planned from %(start)s to %(end)s",
                                start=format_datetime(
                                    self.env, prev_start, dt_format=False
                                ),
                                end=format_datetime(
                                    self.env, prev_finished, dt_format=False
                                ),
                            ),
                        }
                    )
                if conflicted_dict.get(wo.id):
                    infos.append(
                        {
                            "color": "text-danger",
                            "msg": _(
                                "Planned at the same time as other workorder(s) at %s",
                                wo.workcenter_id.display_name,
                            ),
                        }
                    )
                elif occupied_by_id.get(wo.id):
                    infos.append(
                        {
                            "color": "text-danger",
                            "msg": _(
                                "%s is already booked for that time slot.",
                                wo.workcenter_id.display_name,
                            ),
                        }
                    )
            color_icon = (infos and infos[-1]["color"]) or False
            wo.show_json_popover = bool(color_icon)
            wo.json_popover = json.dumps(
                {
                    "popoverTemplate": "mrp.workorderPopover",
                    "infos": infos,
                    "color": color_icon,
                    "icon": "fa-exclamation-triangle"
                    if color_icon in ["text-warning", "text-danger"]
                    else "fa-info-circle",
                    "replan": color_icon not in [False, "text-primary"],
                }
            )

    @api.depends("production_id.qty_producing")
    def _compute_qty_producing(self):
        for workorder in self:
            workorder.qty_producing = workorder.production_id.qty_producing

    def _inverse_qty_producing(self):
        self._update_production_qty_producing()

    def _update_production_qty_producing(self):
        for workorder in self:
            if workorder.qty_producing not in (
                0,
                workorder.production_id.qty_producing,
            ):
                workorder.production_id.qty_producing = workorder.qty_producing
                workorder.production_id._update_moves_from_qty_producing(False)

    @api.depends(
        "state",
        "blocked_by_workorder_ids",
        "blocked_by_workorder_ids.qty_produced",
        "blocked_by_workorder_ids.qty_reported_from_previous_wo",
        "blocked_by_workorder_ids.state",
        "qty_remaining",
        "qty_produced",
        "qty_reported_from_previous_wo",
    )
    def _compute_qty_ready(self):
        for workorder in self:
            if workorder.state in ("cancel", "done"):
                workorder.qty_ready = 0
            else:
                workorder.qty_ready = workorder._get_qty_ready()

    @api.depends("reservation_ids")
    def _compute_reservation_id(self):
        for workorder in self:
            workorder.reservation_id = workorder.reservation_ids[:1]

    def _get_fields_reservation_date(self):
        return ("date_start", "date_end")

    def _prepare_reservation_vals_list(self):
        self.check_singleton()
        resource = self.workcenter_id.resource_id
        if not self.date_start or not self.date_end or not resource:
            return []
        if self.state == "cancel":
            return []
        return [
            {
                "name": self.display_name,
                "date_start": self.date_start,
                "date_end": self.date_end,
                "resource_id": resource.id,
                "allocated_percentage": 100.0,
                "enforcement_mode": "soft",
            }
        ]

    def _get_fields_sync_trigger(self):
        return super()._get_fields_sync_trigger() | {"workcenter_id", "state"}

    @api.constrains("blocked_by_workorder_ids")
    def _check_no_cyclic_dependencies(self):
        if self._has_cycle("blocked_by_workorder_ids"):
            raise ValidationError(_("You cannot create cyclic dependency."))

    @api.depends("production_id.name")
    def _compute_barcode(self):
        for wo in self:
            wo.barcode = f"{wo.production_id.name}/{wo.id}"

    @api.depends("production_id", "product_id")
    @api.depends_context("prefix_product")
    def _compute_display_name(self):
        for wo in self:
            wo.display_name = f"{wo.production_id.name} - {wo.name}"
            if self.env.context.get("prefix_product"):
                wo.display_name = (
                    f"{wo.product_id.name} - {wo.production_id.name} - {wo.name}"
                )

    def unlink(self):
        (self.move_raw_ids | self.move_finished_ids).write({"workorder_id": False})
        mo_dirty = self.production_id.filtered(
            lambda mo: mo.state in ("confirmed", "progress", "to_close")
        )

        for workorder in self:
            workorder.blocked_by_workorder_ids.needed_by_workorder_ids = [
                Command.link(needed_by.id)
                for needed_by in workorder.needed_by_workorder_ids
            ]

        _debug.lifecycle("unlink", workorders=self, reconfirm=mo_dirty)
        self.end_all()
        res = super().unlink()
        mo_dirty.workorder_ids._action_confirm()
        return res

    @api.depends(
        "production_id.product_qty", "qty_produced", "production_id.product_uom_id"
    )
    def _compute_is_produced(self):
        self.is_produced = False
        for order in self.filtered(
            lambda p: p.production_id and p.production_id.product_uom_id
        ):
            order.is_produced = (
                order.production_id.product_uom_id.compare(
                    order.qty_produced, order.qty_production
                )
                >= 0
            )

    @api.depends(
        "operation_id", "workcenter_id", "qty_producing", "qty_production", "product_id"
    )
    def _compute_duration_expected(self):
        for workorder in self:
            if workorder.state in ("done", "cancel"):
                continue
            qty_changed = workorder.qty_producing != workorder.qty_production or (
                workorder._origin != workorder
                and workorder._origin.qty_producing
                and workorder.qty_producing != workorder._origin.qty_producing
            )
            product_changed = (
                workorder._origin
                and workorder._origin.product_id != workorder.product_id
            )
            if qty_changed or product_changed:
                workorder.duration_expected = workorder._get_duration_expected()

    @api.depends(
        "time_ids.duration", "time_ids.loss_type", "qty_produced", "duration_expected"
    )
    def _compute_durations(self):
        for order in self:
            order.duration = order._get_duration()
            order.duration_unit = (
                round(order.duration / order.qty_produced, 2)
                if order.qty_produced
                else 0.0
            )
            if order.duration_expected:
                order.duration_percent = max(
                    -2147483648,
                    min(
                        2147483647,
                        100
                        * (order.duration_expected - order.duration)
                        / order.duration_expected,
                    ),
                )
            else:
                order.duration_percent = 0

    @api.depends("time_ids.date_start", "time_ids.date_end", "duration")
    def _compute_duration_live(self):
        now = fields.Datetime.now()
        for workorder in self:
            workorder.duration_live = workorder._get_duration(until=now)

    def _inverse_duration(self):

        def _float_duration_to_seconds(duration):
            minutes = duration // 1
            seconds = (duration % 1) * 60
            return minutes * 60 + seconds

        for order in self:
            old_order_duration = order._get_duration()
            new_order_duration = order.duration
            if new_order_duration == old_order_duration:
                continue

            delta_duration = new_order_duration - old_order_duration

            if delta_duration > 0:
                if order.state not in ("progress", "done", "cancel"):
                    order.state = "progress"
                enddate = fields.Datetime.now()
                date_start = enddate - timedelta(
                    seconds=_float_duration_to_seconds(delta_duration)
                )
                end_dates = order.time_ids.filtered("date_end").mapped("date_end")
                if end_dates:
                    latest_end = max(end_dates)
                    if latest_end > date_start:
                        date_start = latest_end
                        enddate = latest_end + timedelta(
                            seconds=_float_duration_to_seconds(delta_duration)
                        )
                if (
                    order.duration_expected >= new_order_duration
                    or old_order_duration >= order.duration_expected
                ):
                    self.env["mrp.workcenter.productivity"].create(
                        order._prepare_timeline_vals(
                            new_order_duration, date_start, enddate
                        )
                    )
                else:
                    maxdate = fields.Datetime.from_string(enddate) - relativedelta(
                        minutes=new_order_duration - order.duration_expected
                    )
                    self.env["mrp.workcenter.productivity"].create(
                        [
                            order._prepare_timeline_vals(
                                order.duration_expected, date_start, maxdate
                            ),
                            order._prepare_timeline_vals(
                                new_order_duration, maxdate, enddate
                            ),
                        ]
                    )
            else:
                duration_to_remove = abs(delta_duration)
                timelines_to_unlink = self.env["mrp.workcenter.productivity"]
                for timeline in order.time_ids.sorted():
                    if duration_to_remove <= 0.0:
                        break
                    if timeline.duration <= duration_to_remove:
                        duration_to_remove -= timeline.duration
                        timelines_to_unlink |= timeline
                    else:
                        new_time_line_duration = timeline.duration - duration_to_remove
                        timeline.date_start = timeline.date_end - timedelta(
                            seconds=_float_duration_to_seconds(new_time_line_duration)
                        )
                        break
                timelines_to_unlink.unlink()

    @api.depends("duration", "duration_expected", "state")
    def _compute_progress(self):
        for order in self:
            if order.state == "done":
                order.progress = 100
            elif order.duration_expected:
                order.progress = order.duration * 100 / order.duration_expected
            else:
                order.progress = 0

    @api.depends("time_ids.date_end", "time_ids.user_id", "time_ids.loss_type")
    @api.depends_context("uid")
    def _compute_working_users(self):
        for order in self:
            no_date_end_times = order.time_ids.filtered(
                lambda time: not time.date_end
            ).sorted("date_start")
            order.working_user_ids = [
                Command.link(user.id) for user in no_date_end_times.user_id
            ]
            if order.working_user_ids:
                order.last_working_user_id = order.working_user_ids[-1]
            elif order.time_ids:
                times_with_date_end = order.time_ids.filtered("date_end").sorted(
                    "date_end"
                )
                order.last_working_user_id = (
                    times_with_date_end[-1].user_id
                    if times_with_date_end
                    else order.time_ids[-1].user_id
                )
            else:
                order.last_working_user_id = False
            if no_date_end_times.filtered(
                lambda x: (
                    (x.user_id.id == self.env.user.id)
                    and (x.loss_type in ("productive", "performance"))
                )
            ):
                order.is_user_working = True
            else:
                order.is_user_working = False

    @api.depends("scrap_ids")
    def _compute_scrap_count(self):
        data = self.env["stock.scrap"]._read_group(
            [("workorder_id", "in", self.ids)], ["workorder_id"], ["__count"]
        )
        count_data = {workorder.id: count for workorder, count in data}
        for workorder in self:
            workorder.scrap_count = count_data.get(workorder.id, 0)

    @api.onchange("operation_id")
    def _onchange_operation_id(self):
        if self.operation_id:
            self.name = self.operation_id.name
            self.workcenter_id = self.operation_id.workcenter_id.id

    @api.onchange("date_start", "duration_expected", "workcenter_id")
    def _onchange_date_start(self):
        if self.date_start and self.workcenter_id:
            self.date_end = self._get_date_end()

    def _get_date_end(self, date_start=False, new_workcenter=False):
        workcenter = new_workcenter or self.workcenter_id
        if not workcenter.resource_calendar_id:
            duration_in_seconds = self.duration_expected * 60
            return (date_start or self.date_start) + timedelta(
                seconds=duration_in_seconds
            )
        return workcenter.resource_calendar_id.plan_hours(
            self.duration_expected / 60.0,
            date_start or self.date_start,
            compute_leaves=True,
            domain=[("time_type_id", "!=", False)],
        )

    @api.onchange("date_end")
    def _onchange_date_finished(self):
        if self.date_start and self.date_end and self.workcenter_id:
            self.duration_expected = self._get_duration_expected_from_dates()
        if not self.date_end and self.date_start:
            raise UserError(
                _(
                    "It is not possible to unplan one single Work Order. "
                    "You should unplan the Manufacturing Order instead in order to unplan all the linked operations."
                )
            )

    def _get_duration_expected_from_dates(self, date_start=False, date_end=False):
        if not self.workcenter_id.resource_calendar_id:
            return (
                (date_end or self.date_end) - (date_start or self.date_start)
            ).total_seconds() / 60
        interval = self.workcenter_id.resource_calendar_id.get_work_duration_data(
            date_start or self.date_start,
            date_end or self.date_end,
            domain=[("time_type_id", "!=", False)],
        )
        return interval["hours"] * 60

    @api.onchange("finished_lot_ids")
    def _onchange_finished_lot_ids(self):
        if self.production_id:
            return self.production_id._get_serial_numbers_warning(
                sns=self.finished_lot_ids
            )
        return None

    def write(self, vals):
        values = dict(vals)
        self._check_write_qty_produced(values)
        self._check_write_production_id(values)
        new_workcenter, previous_workcenter_by_id = self._pre_write_workcenter(values)
        derived_vals = self._prepare_derived_date_vals_by_workorder(
            values, new_workcenter
        )
        res = self._write_grouped_by_derived_vals(values, derived_vals)
        _debug.lifecycle(
            "write",
            workorders=self,
            fields=list(values),
            new_workcenter=new_workcenter.id if new_workcenter else False,
            derived=len(derived_vals),
        )
        self._post_write_qty_produced(values)
        self._post_write_workcenter(previous_workcenter_by_id, new_workcenter)
        return res

    def _check_write_qty_produced(self, values):
        if "qty_produced" not in values:
            return
        for workorder in self:
            if workorder.state in ("done", "cancel"):
                raise UserError(
                    _(
                        "You cannot change the quantity produced of a work order that is in done or cancel state."
                    )
                )
            if workorder.product_uom_id.compare(values["qty_produced"], 0) < 0:
                raise UserError(_("The quantity produced must be positive."))

    def _check_write_production_id(self, values):
        if "production_id" in values and any(
            values["production_id"] != workorder.production_id.id for workorder in self
        ):
            raise UserError(
                _("You cannot link this work order to another manufacturing order.")
            )

    def _pre_write_workcenter(self, values):
        if "workcenter_id" not in values:
            return False, {}
        new_workcenter = self.env["mrp.workcenter"].browse(values["workcenter_id"])
        previous_workcenter_by_id = {}
        for workorder in self:
            if workorder.workcenter_id.id == values["workcenter_id"]:
                continue
            if workorder.state in ("done", "cancel"):
                raise UserError(
                    _("You cannot change the workcenter of a work order that is done.")
                )
            workorder.reservation_id.resource_id = new_workcenter.resource_id
            if workorder.state != "progress":
                previous_workcenter_by_id[workorder.id] = workorder.workcenter_id
            else:
                workorder.time_ids.filtered(
                    lambda time: not time.date_end
                ).workcenter_id = new_workcenter
        return new_workcenter, previous_workcenter_by_id

    def _prepare_derived_date_vals_by_workorder(self, values, new_workcenter):
        if "date_start" not in values and "date_end" not in values:
            return {}
        derived_vals = {}
        for workorder in self:
            date_start = fields.Datetime.to_datetime(
                values.get("date_start", workorder.date_start)
            )
            date_end = fields.Datetime.to_datetime(
                values.get("date_end", workorder.date_end)
            )
            if date_start and date_end and date_start > date_end:
                raise UserError(
                    _(
                        "The planned end date of the work order cannot be prior to the planned start date, please correct this to save the work order."
                    )
                )
            derived = workorder._prepare_derived_date_vals(
                values, date_start, date_end, new_workcenter
            )
            if derived:
                derived_vals[workorder.id] = derived
            workorder._update_production_dates(values, derived)
        return derived_vals

    def _prepare_derived_date_vals(self, values, date_start, date_end, new_workcenter):
        self.check_singleton()
        if "duration_expected" in values or self.env.context.get(
            "bypass_duration_calculation"
        ):
            return {}
        if values.get("date_start") and values.get("date_end"):
            return {
                "date_end": self._get_date_end(
                    date_start=date_start, new_workcenter=new_workcenter
                )
            }
        if date_start and not date_end:
            return {
                "date_end": self._get_date_end(
                    date_start=date_start, new_workcenter=new_workcenter
                )
            }
        if date_start and date_end:
            return {
                "duration_expected": self._get_duration_expected_from_dates(
                    date_start=date_start, date_end=date_end
                )
            }
        return {}

    def _update_production_dates(self, values, derived):
        self.check_singleton()
        workorders = self.production_id.workorder_ids
        if self == workorders[:1] and values.get("date_start"):
            self.production_id.with_context(force_date=True).write(
                {"date_start": fields.Datetime.to_datetime(values["date_start"])}
            )
        if self == workorders[-1:] and "date_end" in values:
            propagated_end = derived.get("date_end", values["date_end"])
            if propagated_end:
                self.production_id.with_context(force_date=True).write(
                    {"date_end": fields.Datetime.to_datetime(propagated_end)}
                )

    def _write_grouped_by_derived_vals(self, values, derived_vals):
        if not derived_vals:
            return super().write(values)
        groups = defaultdict(self.browse)
        for workorder in self:
            derived = derived_vals.get(workorder.id) or {}
            groups[tuple(sorted(derived.items()))] |= workorder
        res = True
        for derived_items, workorders in groups.items():
            res = (
                super(MrpWorkorder, workorders).write({**values, **dict(derived_items)})
                and res
            )
        return res

    def _post_write_qty_produced(self, values):
        if "qty_produced" not in values:
            return
        productions = self.production_id.filtered(
            lambda p: p.product_uom_id.compare(values["qty_produced"], 0) > 0
        )
        if not productions:
            return
        for production in productions:
            min_workorder_qty = min(production.workorder_ids.mapped("qty_produced"))
            if production.product_uom_id.compare(min_workorder_qty, 0) > 0:
                production.workorder_ids.filtered(
                    lambda w: w.state != "done"
                ).qty_producing = min_workorder_qty
        self._update_production_qty_producing()

    def _post_write_workcenter(self, previous_workcenter_by_id, new_workcenter):
        for workorder in self.browse(previous_workcenter_by_id):
            workorder.duration_expected = workorder._get_duration_expected(
                previous_workcenter=previous_workcenter_by_id[workorder.id]
            )
            if workorder.date_start:
                workorder.date_end = workorder._get_date_end(
                    new_workcenter=new_workcenter
                )

    @api.model_create_multi
    def create(self, vals_list):
        operations = self.env["mrp.routing.workcenter"].browse(
            {
                values["operation_id"]
                for values in vals_list
                if values.get("operation_id") and not values.get("sequence")
            }
        )
        sequence_by_operation = {
            operation.id: operation.sequence for operation in operations
        }
        for values in vals_list:
            sequence = sequence_by_operation.get(values.get("operation_id"))
            if sequence:
                values["sequence"] = sequence

        res = super().create(vals_list)
        _debug.lifecycle(
            "create", count=len(res), workorders=res, operations=len(operations)
        )

        for workorder in res:
            if workorder.date_start and not workorder.date_end:
                workorder.date_end = workorder._get_date_end()

        for mo in res.mapped("production_id"):
            if len(set(mo.workorder_ids.mapped("sequence"))) != len(mo.workorder_ids):
                mo._resequence_workorders()

        if self.env.context.get("skip_confirm"):
            _debug.logic("workorder_confirm_skipped", by="context", workorders=res)
            return res
        to_confirm = res.filtered(
            lambda wo: wo.production_id.state in ("confirmed", "progress", "to_close")
        )
        to_confirm = to_confirm.production_id.workorder_ids
        to_confirm._action_confirm()
        return res

    def _action_confirm(self):
        for production in self.mapped("production_id"):
            production._link_workorders_and_moves()

    def _get_byproduct_move_to_update(self):
        return self.production_id.move_finished_ids.filtered(
            lambda x: (
                (x.product_id.id != self.production_id.product_id.id)
                and (x.state not in ("done", "cancel"))
            )
        )

    def _plan_workorder(self, replan=False, planned=None):
        self.check_singleton()
        if planned is None:
            planned = set()
        elif self.id in planned:
            return
        planned.add(self.id)
        date_start = fields.Datetime.now()
        if self.production_id.date_start and self.production_id.date_start > date_start:
            date_start = self.production_id.date_start
        for workorder in self.blocked_by_workorder_ids:
            workorder._plan_workorder(replan, planned)
            if workorder.date_end and workorder.date_end > date_start:
                date_start = workorder.date_end
        if self.state not in ["blocked", "ready"]:
            _debug.logic(
                "workorder_plan_skipped",
                workorder=self.id,
                reason="state",
                state=self.state,
            )
            return
        if self.date_start and not replan:
            _debug.logic(
                "workorder_plan_skipped", workorder=self.id, reason="already_dated"
            )
            return
        workcenters = self.workcenter_id | self.workcenter_id.alternative_workcenter_ids
        best, reasons = workcenters._get_earliest_slot_and_reasons(
            date_start,
            {
                workcenter: (
                    self.duration_expected
                    if workcenter == self.workcenter_id
                    else self._get_duration_expected(alternative_workcenter=workcenter)
                )
                for workcenter in workcenters
            },
            reservations_to_ignore=self.reservation_ids,
        )
        if best is None:
            _debug.logic(
                "workorder_unplannable",
                workorder=self.id,
                workcenters=workcenters,
                reasons=len(reasons),
            )
            raise UserError(
                workcenters._prepare_unplannable_error(self.display_name, reasons)
            )
        workcenter, date_start, date_end, duration_expected = best
        _debug.lifecycle(
            "workorder_planned",
            workorder=self.id,
            workcenter=workcenter.id,
            alternatives=len(workcenters),
            duration=duration_expected,
        )
        self.write(
            {
                "workcenter_id": workcenter.id,
                "duration_expected": duration_expected,
                "date_start": date_start,
                "date_end": date_end,
            }
        )

    def _get_costs_hour(self):
        self.check_singleton()
        return self.costs_hour or self.workcenter_id.costs_hour

    def _get_cost(self, date=False):
        total = 0
        for workorder in self:
            if workorder._is_cost_estimate_required():
                duration = workorder.duration_expected / 60
            else:
                intervals = Intervals(
                    [
                        [t.date_start, t.date_end, t]
                        for t in workorder.time_ids
                        if t.date_end and (not date or t.date_end <= date)
                    ]
                )
                duration = get_intervals_hours(intervals)
            total += duration * workorder._get_costs_hour()
        return total

    def button_start(self, skip_invalid_state=False):
        if any(wo.working_state == "blocked" for wo in self):
            _debug.logic(
                "workorder_refused", reason="workcenter_blocked", workorders=self
            )
            raise UserError(
                _("Please unblock the work center to start the work order.")
            )
        for wo in self:
            if any(
                not time.date_end
                for time in wo.time_ids.filtered(
                    lambda t: t.user_id.id == self.env.user.id
                )
            ):
                continue
            if wo.state in ("done", "cancel"):
                if skip_invalid_state:
                    continue
                _debug.logic(
                    "workorder_refused",
                    reason="start_closed",
                    workorder=wo.id,
                    state=wo.state,
                )
                raise UserError(
                    _("You cannot start a work order that is already done or cancelled")
                )

            if wo.qty_producing == 0:
                wo.qty_producing = wo.qty_remaining

            if wo._is_timer_start_required():
                self.env["mrp.workcenter.productivity"].create(
                    wo._prepare_timeline_vals(wo.duration, fields.Datetime.now())
                )

            if wo.production_id.state != "progress":
                wo.production_id.write({"date_start": fields.Datetime.now()})
            if wo.state == "progress":
                continue
            date_start = fields.Datetime.now()
            vals = {
                "state": "progress",
                "date_start": date_start,
            }
            _debug.lifecycle(
                "workorder_started",
                workorder=wo.id,
                production=wo.production_id.id,
                workcenter=wo.workcenter_id.id,
                qty_producing=wo.qty_producing,
                reserved=len(wo.reservation_ids),
            )
            if not wo.reservation_ids:
                vals["date_end"] = date_start + relativedelta(
                    minutes=wo.duration_expected
                )
                wo.with_context(bypass_duration_calculation=True).write(vals)
            else:
                if not wo.date_start or wo.date_start > date_start:
                    vals["date_end"] = wo._get_date_end(date_start)
                if wo.date_end and wo.date_end < date_start:
                    vals["date_end"] = date_start
                wo.with_context(bypass_duration_calculation=True).write(vals)

    def button_finish(self):
        date_end = fields.Datetime.now()
        all_vals_dict = defaultdict(lambda: self.env["mrp.workorder"])
        workorders_to_end = self.filtered(
            lambda workorder: workorder.state not in ("done", "cancel")
        )
        operations = workorders_to_end.operation_id
        moves_to_pick = workorders_to_end.move_raw_ids.filtered(
            lambda move: not move.picked
        )
        moves_to_pick += workorders_to_end.production_id.move_byproduct_ids.filtered(
            lambda move: not move.picked and move.operation_id in operations
        )

        for move in moves_to_pick:
            production_id = move.raw_material_production_id or move.production_id
            if production_id.product_uom_id.is_zero(production_id.qty_producing):
                qty_available = production_id.product_qty
            else:
                qty_available = production_id.qty_producing
            new_qty = move.product_uom_id.round(qty_available * move.unit_factor)
            move._update_quantity_done(new_qty)

        _debug.pipeline(
            "workorder_finish",
            workorders=self,
            to_end=len(workorders_to_end),
            moves_picked=len(moves_to_pick),
        )
        moves_to_pick.picked = True
        workorders_to_end.end_all()
        workorders_to_end.flush_recordset(["duration_expected"])
        for workorder in workorders_to_end:
            vals = {
                "qty_produced": workorder.qty_produced
                or workorder.qty_producing
                or workorder.qty_production,
                "state": "done",
                "date_end": date_end,
                "costs_hour": workorder.workcenter_id.costs_hour,
            }
            if not workorder.date_start or date_end < workorder.date_start:
                vals["date_start"] = date_end
            all_vals_dict[frozenset(vals.items())] |= workorder
        _debug.lifecycle(
            "workorder_done", workorders=workorders_to_end, groups=len(all_vals_dict)
        )
        for frozen_vals, workorders in all_vals_dict.items():
            workorders.with_context(bypass_duration_calculation=True).write(
                dict(frozen_vals)
            )
        return True

    def end_previous(self, doall=False):
        domain = [("workorder_id", "in", self.ids), ("date_end", "=", False)]
        if not doall:
            domain.append(("user_id", "=", self.env.user.id))
        self.env["mrp.workcenter.productivity"].search(domain)._close()
        return True

    def end_all(self):
        return self.end_previous(doall=True)

    def button_pending(self):
        self.end_previous()

    def button_unblock(self):
        for order in self:
            order.workcenter_id.action_unblock()
        return True

    def action_cancel(self):
        self.end_all()
        return self.filtered(lambda wo: wo.state != "cancel").write({"state": "cancel"})

    def action_replan(self):
        for production in self.production_id:
            production._plan_workorders(replan=True)
        self.invalidate_model(["show_json_popover", "json_popover"])
        return True

    def button_scrap(self):
        self.check_singleton()
        return {
            "name": _("Scrap Products"),
            "view_mode": "form",
            "res_model": "stock.scrap",
            "views": [(self.env.ref("stock.view_stock_scrap_form2").id, "form")],
            "type": "ir.actions.act_window",
            "context": {
                "default_company_id": self.production_id.company_id.id,
                "default_workorder_id": self.id,
                "default_production_id": self.production_id.id,
                "product_ids": (
                    self.production_id.move_raw_ids.filtered(
                        lambda x: x.state not in ("done", "cancel")
                    )
                    | self.production_id.move_finished_ids.filtered(
                        lambda x: x.state == "done"
                    )
                )
                .mapped("product_id")
                .ids,
            },
            "target": "new",
        }

    def action_view_move_scrap(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.action_stock_scrap"
        )
        action["domain"] = [("workorder_id", "=", self.id)]
        return action

    def action_view_wizard(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "mrp.mrp_workorder_mrp_production_form"
        )
        action["res_id"] = self.id
        return action

    @api.depends(
        "qty_production",
        "qty_reported_from_previous_wo",
        "qty_produced",
        "production_id.product_uom_id",
    )
    def _compute_qty_remaining(self):
        for wo in self:
            if wo.production_id.product_uom_id:
                wo.qty_remaining = max(
                    wo.production_id.product_uom_id.round(
                        wo.qty_production
                        - wo.qty_reported_from_previous_wo
                        - wo.qty_produced
                    ),
                    0,
                )
            else:
                wo.qty_remaining = 0

    def _get_duration_expected(
        self, alternative_workcenter=False, ratio=1, previous_workcenter=False
    ):
        self.check_singleton()
        if not self.workcenter_id:
            return self.duration_expected
        capacity, setup, cleanup = self.workcenter_id._get_capacity(
            self.product_id,
            self.product_uom_id,
            self.production_bom_id.product_qty or 1,
        )
        if not self.operation_id:
            previous_record = self._origin if self._origin.workcenter_id else self
            previous = previous_workcenter or previous_record.workcenter_id
            _capacity, old_setup, old_cleanup = previous._get_capacity(
                previous_record.product_id,
                previous_record.product_uom_id,
                previous_record.production_bom_id.product_qty or 1,
            )
            working_minutes = max(
                (self.duration_expected - old_setup - old_cleanup)
                * previous.time_efficiency
                / 100.0,
                0,
            )
            if self.qty_producing not in (
                0,
                self.qty_production,
                self._origin.qty_producing,
            ):
                qty_ratio = self.qty_producing / (
                    self._origin.qty_producing or self.qty_production
                )
            else:
                qty_ratio = 1
            return (
                setup
                + cleanup
                + working_minutes
                * qty_ratio
                * ratio
                * 100.0
                / self.workcenter_id.time_efficiency
            )
        qty_production = self.qty_producing or self.qty_production
        cycle_number = float_round(
            qty_production / capacity, precision_digits=0, rounding_method="UP"
        )
        if alternative_workcenter:
            duration_expected_working = (
                (self.duration_expected - setup - cleanup)
                * self.workcenter_id.time_efficiency
                / (100.0 * cycle_number)
            )
            duration_expected_working = max(duration_expected_working, 0)
            capacity, setup, cleanup = alternative_workcenter._get_capacity(
                self.product_id,
                self.product_uom_id,
                self.production_bom_id.product_qty or 1,
            )
            cycle_number = float_round(
                qty_production / capacity, precision_digits=0, rounding_method="UP"
            )
            return (
                setup
                + cleanup
                + cycle_number
                * duration_expected_working
                * 100.0
                / alternative_workcenter.time_efficiency
            )
        time_cycle = self.operation_id.time_cycle
        return (
            setup
            + cleanup
            + cycle_number * time_cycle * 100.0 / self.workcenter_id.time_efficiency
        )

    def _get_conflicted_workorder_ids(self):
        self.flush_model(["state", "date_start", "date_end", "workcenter_id"])
        sql = """
            SELECT wo1.id, wo2.id
            FROM mrp_workorder wo1, mrp_workorder wo2
            WHERE
                wo1.id = ANY(%s)
                AND wo1.state IN ('blocked', 'ready')
                AND wo2.state IN ('blocked', 'ready')
                AND wo1.id != wo2.id
                AND wo1.workcenter_id = wo2.workcenter_id
                AND (DATE_TRUNC('second', wo2.date_start), DATE_TRUNC('second', wo2.date_end))
                    OVERLAPS (DATE_TRUNC('second', wo1.date_start), DATE_TRUNC('second', wo1.date_end))
        """
        self.env.cr.execute(sql, [list(self.ids)])
        res = defaultdict(list)
        for wo1, wo2 in self.env.cr.fetchall():
            res[wo1].append(wo2)
        return res

    def _prepare_operation_vals(self):
        self.check_singleton()
        ratio = 1 / self.qty_production
        if self.operation_id.bom_id:
            ratio = self.production_id._get_ratio_between_mo_and_bom_quantities(
                self.operation_id.bom_id
            )
        return {
            "company_id": self.company_id.id,
            "name": self.name,
            "time_cycle_manual": self.duration_expected * ratio,
            "workcenter_id": self.workcenter_id.id,
        }

    def _prepare_timeline_vals(self, duration, date_start, date_end=False):
        loss_type = (
            "productive"
            if not self.duration_expected or duration <= self.duration_expected
            else "performance"
        )
        loss_id = self.env["mrp.workcenter.productivity.loss"]._get_loss_of_type(
            loss_type
        )
        return {
            "workorder_id": self.id,
            "workcenter_id": self.workcenter_id.id,
            "description": _("Time Tracking: %(user)s", user=self.env.user.name),
            "loss_id": loss_id.id,
            "date_start": date_start.replace(microsecond=0),
            "date_end": date_end.replace(microsecond=0) if date_end else date_end,
            "user_id": self.env.user.id,
            "company_id": self.company_id.id,
        }

    def _is_timer_start_required(self):
        return True

    def _is_cost_estimate_required(self):
        self.check_singleton()
        return bool(
            self.state in ("progress", "done")
            and self.duration_expected
            and self.cost_mode == "estimated"
        )

    def _update_qty_producing(self, quantity):
        self.check_singleton()
        if self.qty_producing:
            self.qty_producing = quantity

    def _get_duration_of_intervals(self, intervals):
        """Measure `(date_start, date_end, timer)` triples, overlaps counted once.

        A timer may span several intervals; that is not a problem, because what
        the split is for is telling employee time from blocking time.
        """
        if not intervals:
            return 0.0
        spans = [
            (timer.loss_id, timer.workcenter_id, date_start, date_stop)
            for date_start, date_stop, timer in Intervals(intervals)
        ]
        return sum(
            self.env["mrp.workcenter.productivity.loss"]._get_durations_batch(spans)
        )

    def _get_duration(self, until=None):
        """Measure the timer lines against the work center's working calendar.

        `until` closes off a timer that is still running. With no bound a
        running timer contributes nothing, which is what the stored `duration`
        wants: a value that is a function of the timer rows and of nothing
        else. `duration_live` passes the wall clock -- the same clock
        `button_start` stamped `date_start` with. Never the cursor's clock:
        `cr.now()` is PostgreSQL's `now()`, the transaction's start, so a timer
        opened a second into the transaction spans backwards and `Intervals`
        drops it.
        """
        self.check_singleton()
        loss_type_times = defaultdict(lambda: self.env["mrp.workcenter.productivity"])
        for time in self.time_ids:
            loss_type_times[time.loss_id.loss_type] |= time
        duration = 0
        for times in loss_type_times.values():
            duration += self._get_duration_of_intervals(
                [
                    (time.date_start, time.date_end or until, time)
                    for time in times
                    if time.date_start and (time.date_end or until)
                ]
            )
        return duration

    def get_duration(self):
        return self._get_duration(until=fields.Datetime.now())

    def action_mark_as_done(self):
        for wo in self:
            if wo.working_state == "blocked":
                raise UserError(
                    _("Please unblock the work center to validate the work order")
                )
            wo.button_finish()
            if not wo.duration:
                wo.duration = wo.duration_expected
                wo.duration_percent = 100

    def _get_machine_cost(self, minutes):
        self.check_singleton()
        return (minutes / 60.0) * self._get_costs_hour()

    def _get_expected_operation_cost(self, without_employee_cost=False):
        return self._get_machine_cost(self.duration_expected)

    def _get_current_operation_cost(self):
        return self._get_machine_cost(self.get_duration())

    def _get_theoretical_operation_cost(self, without_employee_cost=False):
        return self._get_machine_cost(self.get_duration())

    def _update_cost_mode(self):
        for workorder in self:
            workorder.cost_mode = workorder.operation_id.cost_mode or "actual"
