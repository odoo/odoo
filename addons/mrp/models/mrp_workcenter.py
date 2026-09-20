import json
from collections import defaultdict
from datetime import timedelta

from babel.dates import format_date
from dateutil import relativedelta

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.libs.intervals import Intervals
from odoo.libs.numbers import float_compare, float_is_zero, float_round
from odoo.tools.date_utils import end_of, localized, start_of, to_timezone
from odoo.tools.misc import get_lang

_debug = DebugLog(__name__)


class MrpWorkcenter(models.Model):
    _name = "mrp.workcenter"
    _description = "Work Center"
    _order = "sequence, id"
    _inherit = ["mixin.mail.thread", "mixin.resource"]
    _check_company_auto = True

    name = fields.Char(
        related="resource_id.name",
        string="Work Center",
        readonly=False,
    )
    time_efficiency = fields.Float(
        related="resource_id.time_efficiency",
        string="Time Efficiency",
        default=100,
        readonly=False,
    )
    active = fields.Boolean(
        related="resource_id.active",
        string="Active",
        default=True,
        readonly=False,
    )

    code = fields.Char(copy=False)
    note = fields.Html(string="Description")
    sequence = fields.Integer(
        default=1,
        required=True,
        help="Gives the sequence order when displaying a list of work centers.",
    )
    color = fields.Integer()
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="Currency",
        readonly=True,
        required=True,
    )
    costs_hour = fields.Float(
        string="Cost per hour",
        default=0.0,
        tracking=True,
        help="Hourly processing cost.",
    )
    time_start = fields.Float(string="Setup Time")
    time_stop = fields.Float(string="Cleanup Time")
    routing_line_ids = fields.One2many(
        comodel_name="mrp.routing.workcenter",
        inverse_name="workcenter_id",
        string="Routing Lines",
    )
    has_routing_lines = fields.Boolean(
        compute="_compute_has_routing_lines",
        help="Technical field for workcenter views",
    )
    order_ids = fields.One2many(
        comodel_name="mrp.workorder",
        inverse_name="workcenter_id",
        string="Orders",
    )
    workorder_count = fields.Integer(
        string="# Work Orders",
        compute="_compute_workorder_counts_and_load",
    )
    workorder_ready_count = fields.Integer(
        string="# To Do Work Orders",
        compute="_compute_workorder_counts_and_load",
    )
    workorder_progress_count = fields.Integer(
        string="Total Running Orders",
        compute="_compute_workorder_counts_and_load",
    )
    workorder_blocked_count = fields.Integer(
        string="Total Pending Orders",
        compute="_compute_workorder_counts_and_load",
    )
    workorder_late_count = fields.Integer(
        string="Total Late Orders",
        compute="_compute_workorder_counts_and_load",
    )

    time_ids = fields.One2many(
        comodel_name="mrp.workcenter.productivity",
        inverse_name="workcenter_id",
        string="Time Logs",
    )
    working_state = fields.Selection(
        selection=[
            ("normal", "Normal"),
            ("blocked", "Blocked"),
            ("done", "In Progress"),
        ],
        string="Workcenter Status",
        compute="_compute_working_state",
        store=True,
    )
    blocked_time = fields.Float(
        digits=(16, 2),
        compute="_compute_effectiveness_times",
        help="Blocked hours over the last month",
    )
    productive_time = fields.Float(
        digits=(16, 2),
        compute="_compute_effectiveness_times",
        help="Productive hours over the last month",
    )
    oee = fields.Float(
        string="OEE",
        digits=(16, 2),
        compute="_compute_effectiveness_times",
        help="Overall Equipment Effectiveness, based on the last month",
    )
    oee_target = fields.Float(
        string="OEE Target",
        default=90,
        help="Overall Effective Efficiency Target in percentage",
    )
    performance = fields.Integer(
        compute="_compute_performance",
        help="Performance over the last month",
    )
    workcenter_load = fields.Float(
        string="Work Center Load",
        compute="_compute_workorder_counts_and_load",
    )
    alternative_workcenter_ids = fields.Many2many(
        comodel_name="mrp.workcenter",
        relation="mrp_workcenter_alternative_rel",
        column1="workcenter_id",
        column2="alternative_workcenter_id",
        string="Alternative Workcenters",
        domain="[('id', '!=', id), '|', ('company_id', '=', company_id), ('company_id', '=', False)]",
        check_company=True,
        help="Alternative workcenters that can be substituted to this one in order to dispatch production",
    )
    tag_ids = fields.Many2many(comodel_name="mrp.workcenter.tag")
    capacity_ids = fields.One2many(
        comodel_name="mrp.workcenter.capacity",
        inverse_name="workcenter_id",
        string="Product Capacities",
        copy=True,
        help="Specific number of pieces that can be produced in parallel per product.",
    )
    kanban_dashboard_graph = fields.Text(compute="_compute_kanban_dashboard_graph")
    resource_calendar_id = fields.Many2one(
        default=lambda self: self.env.company.resource_calendar_id,
        check_company=True,
    )

    @api.depends("working_state")
    @api.depends_context("group_by", "show_workcenter_status")
    def _compute_display_name(self):
        super()._compute_display_name()
        for workcenter in self:
            if (
                self.env.context.get("group_by")
                and self.env.context.get("show_workcenter_status")
                and workcenter.working_state == "blocked"
            ):
                workcenter.display_name = f"{workcenter.display_name}\u00a0\u00a0🔴"

    @api.constrains("alternative_workcenter_ids")
    def _check_alternative_workcenter(self):
        for workcenter in self:
            if workcenter in workcenter.alternative_workcenter_ids:
                raise ValidationError(
                    _(
                        "Workcenter %s cannot be an alternative of itself.",
                        workcenter.name,
                    )
                )

    @api.depends_context("lang", "uid")
    def _compute_kanban_dashboard_graph(self):
        week_range, date_start, date_stop = self._get_week_range_and_first_last_days()
        has_workorder = self._has_workorder()
        load_data = self._get_workcenter_load_per_week(
            week_range, date_start, date_stop, has_workorder=has_workorder
        )
        load_graph_data = self._prepare_graph_data(
            load_data, week_range, has_workorder=has_workorder
        )
        for wc in self:
            wc.kanban_dashboard_graph = json.dumps(load_graph_data[wc.id])

    def _get_week_range_and_first_last_days(self):
        week_range = {}
        locale = get_lang(self.env).code
        today = fields.Datetime.now()
        delta_from_monday_to_today = (today - start_of(today, "week")).days
        first_week_day = int(get_lang(self.env).week_start) - 1
        day_offset = ((7 - first_week_day) + delta_from_monday_to_today) % 7

        for delta in range(-7, 28, 7):
            week_start = start_of(
                today + relativedelta.relativedelta(days=delta - day_offset), "day"
            )
            week_end = week_start + relativedelta.relativedelta(days=6)
            short_name = format_date(week_start, "d - ", locale=locale) + format_date(
                week_end, "d MMM", locale=locale
            )
            if not delta:
                short_name = _("This Week")
            week_range[week_start] = short_name
        date_start = start_of(
            today + relativedelta.relativedelta(days=-7 - day_offset), "day"
        )
        date_stop = end_of(
            today + relativedelta.relativedelta(days=27 - day_offset), "day"
        )
        return week_range, date_start, date_stop

    def _has_workorder(self):
        return bool(
            self.env["mrp.workorder"].search_count(
                [("workcenter_id", "in", self.ids)], limit=1
            )
        )

    def _get_workcenter_load_per_week(
        self, week_range, date_start, date_stop, has_workorder=None
    ):
        load_data = {rec: {} for rec in self}
        if has_workorder is None:
            has_workorder = self._has_workorder()
        if not has_workorder:
            for wc in self:
                load_data[wc] = {
                    week_start: wc._get_sample_week_load(index)
                    for index, week_start in enumerate(week_range)
                }
            return load_data

        result = self.env["mrp.workorder"]._read_group(
            [
                ("workcenter_id", "in", self.ids),
                ("state", "in", ("blocked", "ready", "progress")),
                ("production_date", ">=", date_start),
                ("production_date", "<=", date_stop),
            ],
            ["workcenter_id", "production_date:week"],
            ["duration_expected:sum"],
        )
        for r in result:
            load_in_hours = round(r[2] / 60, 1)
            load_data[r[0]].update({r[1]: load_in_hours})
        return load_data

    SAMPLE_WEEK_LOAD_SHAPE = (0.35, 0.8, 1.25, 0.6, 1.0)

    def _get_sample_week_load(self, week_index):
        self.check_singleton()
        shape = self.SAMPLE_WEEK_LOAD_SHAPE
        capacity = self.resource_calendar_id.hours_per_week or 40.0
        return round(capacity * shape[(week_index + (self.id or 0)) % len(shape)], 1)

    def _prepare_graph_data(self, load_data, week_range, has_workorder=None):
        graph_data = {wid: [] for wid in self._ids}
        if has_workorder is None:
            has_workorder = self._has_workorder()
        for workcenter in self:
            load_limit = workcenter.resource_calendar_id.hours_per_week
            wc_data = {
                "is_sample_data": not has_workorder,
                "labels": list(week_range.values()),
            }
            load_bar = []
            excess_bar = []
            for week_start in week_range:
                load_bar.append(
                    min(load_data[workcenter].get(week_start, 0), load_limit)
                )
                excess_bar.append(
                    max(
                        float_round(
                            load_data[workcenter].get(week_start, 0) - load_limit,
                            precision_digits=1,
                            rounding_method="HALF-UP",
                        ),
                        0,
                    )
                )
            wc_data["values"] = [load_bar, load_limit, excess_bar]
            graph_data[workcenter.id].append(wc_data)
        return graph_data

    @api.depends(
        "order_ids.duration_expected",
        "order_ids.workcenter_id",
        "order_ids.state",
        "order_ids.date_start",
    )
    def _compute_workorder_counts_and_load(self):
        MrpWorkorder = self.env["mrp.workorder"]
        counts = {wid: {} for wid in self._ids}
        load = dict.fromkeys(self._ids, 0)
        for workcenter, state, duration_sum, count in MrpWorkorder._read_group(
            [
                ("workcenter_id", "in", self.ids),
                ("state", "in", MrpWorkorder.OPEN_STATES),
            ],
            ["workcenter_id", "state"],
            ["duration_expected:sum", "__count"],
        ):
            counts[workcenter.id][state] = count
            load[workcenter.id] += duration_sum
        late = dict(
            MrpWorkorder._read_group(
                Domain("workcenter_id", "in", self.ids)
                & MrpWorkorder._get_domain_late(),
                ["workcenter_id"],
                ["__count"],
            )
        )
        for workcenter in self:
            workcenter.workorder_count = sum(counts[workcenter.id].values())
            workcenter.workorder_blocked_count = counts[workcenter.id].get("blocked", 0)
            workcenter.workcenter_load = load[workcenter.id]
            workcenter.workorder_ready_count = counts[workcenter.id].get("ready", 0)
            workcenter.workorder_progress_count = counts[workcenter.id].get(
                "progress", 0
            )
            workcenter.workorder_late_count = late.get(workcenter, 0)

    @api.depends("time_ids", "time_ids.date_end", "time_ids.loss_type")
    def _compute_working_state(self):
        wall_clock = self.env["mrp.workcenter.productivity.loss"].WALL_CLOCK_LOSS_TYPES
        state_by_workcenter = {}
        for workcenter, loss_type in self.env[
            "mrp.workcenter.productivity"
        ]._read_group(
            [("workcenter_id", "in", self.ids), ("date_end", "=", False)],
            ["workcenter_id", "loss_type"],
        ):
            state = "done" if loss_type in wall_clock else "blocked"
            if state_by_workcenter.get(workcenter) != "blocked":
                state_by_workcenter[workcenter] = state
        for workcenter in self:
            workcenter.working_state = state_by_workcenter.get(
                workcenter._origin, "normal"
            )

    OEE_WINDOW_MONTHS = 1

    def _get_oee_window_start(self):
        return fields.Datetime.to_string(
            fields.Datetime.now()
            - relativedelta.relativedelta(months=self.OEE_WINDOW_MONTHS)
        )

    @api.depends(
        "time_ids.duration",
        "time_ids.loss_type",
        "time_ids.date_start",
        "time_ids.date_end",
    )
    def _compute_effectiveness_times(self):
        wall_clock = self.env["mrp.workcenter.productivity.loss"].WALL_CLOCK_LOSS_TYPES
        time_by_workcenter = defaultdict(lambda: {"blocked": 0.0, "productive": 0.0})
        for workcenter, loss_type, duration in self.env[
            "mrp.workcenter.productivity"
        ]._read_group(
            [
                ("date_start", ">=", self._get_oee_window_start()),
                ("workcenter_id", "in", self.ids),
                ("date_end", "!=", False),
            ],
            ["workcenter_id", "loss_type"],
            ["duration:sum"],
        ):
            bucket = "productive" if loss_type in wall_clock else "blocked"
            time_by_workcenter[workcenter.id][bucket] += duration
        for workcenter in self:
            measured = time_by_workcenter[workcenter.id]
            blocked, productive = measured["blocked"], measured["productive"]
            workcenter.blocked_time = blocked / 60.0
            workcenter.productive_time = productive / 60.0
            workcenter.oee = (
                float_round(
                    productive * 100.0 / (productive + blocked), precision_digits=2
                )
                if productive
                else 0.0
            )

    @api.depends("order_ids.duration", "order_ids.duration_expected", "order_ids.state")
    def _compute_performance(self):
        by_workcenter = {
            workcenter.id: (expected, spent)
            for workcenter, expected, spent in self.env["mrp.workorder"]._read_group(
                [
                    ("date_start", ">=", self._get_oee_window_start()),
                    ("workcenter_id", "in", self.ids),
                    ("state", "=", "done"),
                ],
                ["workcenter_id"],
                ["duration_expected:sum", "duration:sum"],
            )
        }
        for workcenter in self:
            expected, spent = by_workcenter.get(workcenter.id, (0.0, 0.0))
            workcenter.performance = 100 * expected / spent if spent else 0.0

    @api.depends("routing_line_ids")
    def _compute_has_routing_lines(self):
        for workcenter in self:
            workcenter.has_routing_lines = bool(workcenter.routing_line_ids)

    def action_unblock(self):
        self.check_singleton()
        if self.working_state != "blocked":
            _debug.logic("workcenter_refused", reason="not_blocked", workcenter=self.id)
            raise UserError(_("It has already been unblocked."))
        blocking = self.env["mrp.workcenter.productivity"].search(
            [
                ("workcenter_id", "=", self.id),
                ("date_end", "=", False),
                (
                    "loss_type",
                    "not in",
                    list(
                        self.env[
                            "mrp.workcenter.productivity.loss"
                        ].WALL_CLOCK_LOSS_TYPES
                    ),
                ),
            ]
        )
        _debug.lifecycle(
            "workcenter_unblocked", workcenter=self.id, entries=len(blocking)
        )
        blocking.write({"date_end": fields.Datetime.now()})
        return True

    @api.model_create_multi
    def create(self, vals_list):
        self = self.with_context(default_resource_type="material")
        return super().create(vals_list)

    def action_show_operations(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "mrp.mrp_routing_action"
        )
        action["domain"] = [("workcenter_id", "=", self.id)]
        action["context"] = {
            "default_workcenter_id": self.id,
        }
        return action

    def action_work_order(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "mrp.action_work_orders"
        )
        action["context"] = dict(self.env.context, search_default_workcenter_id=self.id)
        return action

    def action_work_order_alternatives(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "mrp.mrp_workorder_todo"
        )
        action["domain"] = [
            ("workcenter_id.alternative_workcenter_ids", "in", self.ids)
        ]
        return action

    def _get_working_minutes_batch(self, spans):
        self.check_singleton()
        if not spans:
            return []
        resource = self.resource_id
        _debug.perf.count(
            "workcenter_working_minutes", workcenter=self.id, spans=len(spans)
        )
        work_intervals = self.resource_calendar_id._work_intervals_batch(
            localized(min(start for start, _stop in spans)),
            localized(max(stop for _start, stop in spans)),
            resources=resource,
        ).get(resource.id, Intervals())
        minutes = []
        for start, stop in spans:
            worked = work_intervals & Intervals(
                [
                    (
                        localized(start),
                        localized(stop),
                        self.env["resource.calendar.attendance"],
                    )
                ]
            )
            minutes.append(
                round(
                    sum(
                        (interval_stop - interval_start).total_seconds()
                        for interval_start, interval_stop, _records in worked
                    )
                    / 60.0,
                    2,
                )
            )
        return minutes

    def _get_unavailability_intervals(self, start_datetime, end_datetime):
        unavailable_per_resource = self.resource_id._get_unavailable_intervals(
            start_datetime, end_datetime
        )
        return {
            wc.id: unavailable_per_resource.get(wc.resource_id.id, []) for wc in self
        }

    def _get_planning_horizon(self):
        iterations = max(
            int(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("mrp.workcenter_max_planning_iterations", "50")
            ),
            1,
        )
        return iterations, timedelta(days=14)

    def _get_first_available_slot(
        self,
        start_datetime,
        duration,
        forward=True,
        reservations_to_ignore=False,
        extra_leaves_slots=None,
    ):
        self.check_singleton()
        iterations, step = self._get_planning_horizon()
        revert = to_timezone(start_datetime.tzinfo)
        start_datetime = localized(start_datetime)
        duration = max(duration, 1 / 60)
        blocked = Intervals(
            [
                (
                    localized(start),
                    localized(stop),
                    self.env["resource.calendar.attendance"],
                )
                for start, stop in extra_leaves_slots or []
            ]
        )
        walk = self._get_slot_forward if forward else self._get_slot_backward
        slot = walk(
            start_datetime, duration, iterations, step, blocked, reservations_to_ignore
        )
        _debug.logic(
            "workcenter_slot_walked",
            workcenter=self.id,
            duration=duration,
            forward=forward,
            iterations=iterations,
            blocked=len(blocked),
            found=slot is not None,
        )
        if slot is None:
            _debug.logic(
                "workcenter_no_slot",
                workcenter=self.id,
                duration=duration,
                horizon_days=iterations * step.days,
            )
            return False, _(
                "No available slot within %(days)s days of the planned start",
                days=iterations * step.days,
            )
        return revert(slot[0]), revert(slot[1])

    def _get_earliest_slot_and_reasons(
        self,
        date_start,
        duration_by_workcenter,
        reservations_to_ignore=False,
        extra_leaves_by_workcenter=None,
    ):
        best = None
        reasons = []
        extra_leaves_by_workcenter = extra_leaves_by_workcenter or {}
        for workcenter in self:
            if not workcenter.resource_calendar_id:
                _debug.logic(
                    "workcenter_refused",
                    reason="no_calendar",
                    workcenter=workcenter.id,
                )
                raise UserError(
                    _("There is no defined calendar on workcenter %s.", workcenter.name)
                )
            duration = duration_by_workcenter[workcenter]
            with _debug.perf(
                "workcenter_slot_search",
                cr=self.env.cr,
                workcenter=workcenter.id,
                duration=duration,
            ):
                from_date, to_date = workcenter._get_first_available_slot(
                    date_start,
                    duration,
                    reservations_to_ignore=reservations_to_ignore,
                    extra_leaves_slots=extra_leaves_by_workcenter.get(workcenter),
                )
            if not from_date:
                reasons.append((workcenter, to_date))
                continue
            if to_date and (best is None or to_date < best[2]):
                best = (workcenter, from_date, to_date, duration)
        _debug.logic(
            "workcenter_earliest_slot",
            candidates=self,
            chosen=best[0].id if best else False,
            refused=len(reasons),
        )
        return best, reasons

    @api.model
    def _prepare_unplannable_error(self, subject, reasons):
        if not reasons:
            return _(
                "%(subject)s cannot be planned: it has no work center to run on.",
                subject=subject,
            )
        return _(
            "%(subject)s cannot be planned on any of its work centers:\n%(reasons)s",
            subject=subject,
            reasons="\n".join(
                f"- {workcenter.display_name}: {why}" for workcenter, why in reasons
            ),
        )

    def _get_intervals_available_and_occupied(
        self, date_start, date_stop, reservations_to_ignore
    ):
        resource = self.resource_id
        available = self.resource_calendar_id._work_intervals_batch(
            date_start,
            date_stop,
            resources=resource,
        )[resource.id]
        occupied = (
            self.env["resource.reservation"]
            ._reservation_intervals_batch(
                date_start,
                date_stop,
                resource,
                domain=[("id", "not in", reservations_to_ignore.ids)]
                if reservations_to_ignore
                else [],
            )
            .get(resource.id, Intervals())
        )
        return available, occupied

    @staticmethod
    def _get_first_conflict(interval, occupied, blocked):
        conflict = interval & occupied or interval & blocked
        return next(iter(conflict), None)

    def _get_slot_forward(
        self,
        start_datetime,
        duration,
        iterations,
        step,
        blocked,
        reservations_to_ignore,
    ):
        remaining = duration
        start_interval = None
        for n in range(iterations):
            date_start = start_datetime + step * n
            available, occupied = self._get_intervals_available_and_occupied(
                date_start, date_start + step, reservations_to_ignore
            )
            for start, stop, records in available:
                start_interval = start_interval or start
                interval_minutes = (stop - start).total_seconds() / 60
                while conflict := self._get_first_conflict(
                    Intervals(
                        [
                            (
                                start_interval or start,
                                start
                                + timedelta(minutes=min(remaining, interval_minutes)),
                                records,
                            )
                        ]
                    ),
                    occupied,
                    blocked,
                ):
                    start = conflict[1]
                    interval_minutes = (stop - start).total_seconds() / 60
                    start_interval, remaining = (
                        start if interval_minutes else None,
                        duration,
                    )
                if float_compare(interval_minutes, remaining, precision_digits=3) >= 0:
                    return start_interval, start + timedelta(minutes=remaining)
                remaining -= interval_minutes
        return None

    def _get_slot_backward(
        self,
        start_datetime,
        duration,
        iterations,
        step,
        blocked,
        reservations_to_ignore,
    ):
        remaining = duration
        stop_interval = None
        now = localized(fields.Datetime.now())
        for n in range(iterations):
            date_stop = start_datetime - step * n
            available, occupied = self._get_intervals_available_and_occupied(
                date_stop - step, date_stop, reservations_to_ignore
            )
            for start, stop, records in reversed(available):
                stop_interval = stop_interval or stop
                interval_minutes = (stop - start).total_seconds() / 60
                while conflict := self._get_first_conflict(
                    Intervals(
                        [
                            (
                                stop
                                - timedelta(minutes=min(remaining, interval_minutes)),
                                stop_interval or stop,
                                records,
                            )
                        ]
                    ),
                    occupied,
                    blocked,
                ):
                    stop = conflict[0]
                    interval_minutes = (stop - start).total_seconds() / 60
                    stop_interval, remaining = (
                        stop if interval_minutes else None,
                        duration,
                    )
                if float_compare(interval_minutes, remaining, precision_digits=3) >= 0:
                    return stop - timedelta(minutes=remaining), stop_interval
                remaining -= interval_minutes
            if date_stop - step <= now:
                break
        return None

    def action_view_schedule(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": _("Schedule: %s", self.display_name),
            "res_model": "resource.reservation",
            "view_mode": "calendar,list,form",
            "domain": [("resource_id", "=", self.resource_id.id)],
        }

    def action_archive(self):
        res = super().action_archive()
        filtered_workcenters = ", ".join(
            workcenter.name for workcenter in self.filtered("routing_line_ids")
        )
        if filtered_workcenters:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _(
                        "Note that archived work center(s): '%s' is/are still linked to active Bill of Materials, which means that operations can still be planned on it/them. "
                        "To prevent this, deletion of the work center is recommended instead.",
                        filtered_workcenters,
                    ),
                    "type": "warning",
                    "sticky": True,
                    "next": {"type": "ir.actions.act_window_close"},
                },
            }
        return res

    def _get_capacity(self, product, unit, default_capacity=1):
        self.check_singleton()
        ranked = [
            (product, product.uom_id),
            (self.env["product.product"], unit),
            (self.env["product.product"], product.uom_id),
            (product, unit),
        ]
        rank = -1  # debuglog
        for wanted_product, wanted_unit in ranked:
            rank += 1  # debuglog
            capacity = self.capacity_ids.filtered(
                lambda c, p=wanted_product, u=wanted_unit: (
                    c.product_id == p and c.product_uom_id == u
                )
            )[:1]
            if not capacity:
                continue
            if float_is_zero(
                capacity.capacity, precision_rounding=capacity.product_uom_id.rounding
            ):
                _debug.logic(
                    "workcenter_capacity",
                    workcenter=self.id,
                    by="zero_capacity_default",
                    rank=rank,
                )
                return (default_capacity, capacity.time_start, capacity.time_stop)
            _debug.logic(
                "workcenter_capacity", workcenter=self.id, by="matched", rank=rank
            )
            return (
                capacity.product_uom_id._get_quantity_in_unit(capacity.capacity, unit),
                capacity.time_start,
                capacity.time_stop,
            )
        _debug.logic("workcenter_capacity", workcenter=self.id, by="default", rank=-1)
        return (default_capacity, self.time_start, self.time_stop)


class MrpWorkcenterTag(models.Model):
    _name = "mrp.workcenter.tag"
    _description = "Work Center Tag"
    _inherit = ["mixin.tag"]


class MrpWorkcenterProductivityLossType(models.Model):
    _name = "mrp.workcenter.productivity.loss.type"
    _description = "MRP Workorder productivity losses"
    _rec_name = "loss_type"

    @api.depends("loss_type")
    @api.depends_context("lang")
    def _compute_display_name(self):
        labels = dict(self._fields["loss_type"]._description_selection(self.env))
        for rec in self:
            rec.display_name = labels.get(rec.loss_type, "")

    loss_type = fields.Selection(
        selection=[
            ("availability", "Availability"),
            ("performance", "Performance"),
            ("quality", "Quality"),
            ("productive", "Productive"),
        ],
        string="Category",
        default="availability",
        required=True,
    )


class MrpWorkcenterProductivityLoss(models.Model):
    _name = "mrp.workcenter.productivity.loss"
    _description = "Workcenter Productivity Losses"
    _order = "sequence, id"

    name = fields.Char(
        string="Blocking Reason",
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=1)
    manual = fields.Boolean(
        string="Is a Blocking Reason",
        default=True,
    )
    loss_id = fields.Many2one(
        comodel_name="mrp.workcenter.productivity.loss.type",
        string="Category",
        domain=[("loss_type", "in", ["quality", "availability"])],
    )
    loss_type = fields.Selection(
        related="loss_id.loss_type",
        string="Effectiveness Category",
        readonly=False,
    )

    WALL_CLOCK_LOSS_TYPES = ("productive", "performance")

    def _is_measured_on_working_time(self):
        self.check_singleton()
        return self.loss_type not in self.WALL_CLOCK_LOSS_TYPES

    @api.model
    @tools.ormcache("loss_type")
    def _get_loss_of_type_id(self, loss_type):
        loss = self.sudo().search([("loss_type", "=", loss_type)], limit=1)
        return loss.id

    def _get_loss_of_type(self, loss_type):
        loss = self.browse(self._get_loss_of_type_id(loss_type))
        if not loss:
            labels = dict(self._fields["loss_type"]._description_selection(self.env))
            raise UserError(
                _(
                    "You need to define at least one productivity loss in the "
                    "category '%s'. Create one from the Manufacturing app, menu: "
                    "Configuration / Productivity Losses.",
                    labels.get(loss_type, loss_type),
                )
            )
        return loss

    @api.model
    def _get_durations_batch(self, spans):
        durations = [0.0] * len(spans)
        spans_per_workcenter = defaultdict(list)
        for index, (loss, workcenter, date_start, date_stop) in enumerate(spans):
            if not loss:
                continue
            if (
                loss._is_measured_on_working_time()
                and workcenter
                and workcenter.resource_calendar_id
            ):
                spans_per_workcenter[workcenter].append((index, date_start, date_stop))
            else:
                durations[index] = round(
                    (date_stop - date_start).total_seconds() / 60.0, 2
                )
        for workcenter, workcenter_spans in spans_per_workcenter.items():
            minutes = workcenter._get_working_minutes_batch(
                [(start, stop) for _index, start, stop in workcenter_spans]
            )
            for (index, _start, _stop), duration in zip(
                workcenter_spans, minutes, strict=True
            ):
                durations[index] = duration
        return durations

    @api.model_create_multi
    def create(self, vals_list):
        self.env.registry.clear_cache()
        return super().create(vals_list)

    def write(self, vals):
        if "loss_id" in vals or "loss_type" in vals:
            self.env.registry.clear_cache()
        return super().write(vals)

    def unlink(self):
        self.env.registry.clear_cache()
        return super().unlink()


class MrpWorkcenterProductivity(models.Model):
    _name = "mrp.workcenter.productivity"
    _description = "Workcenter Productivity Log"
    _order = "id desc"
    _rec_name = "loss_id"
    _check_company_auto = True

    def _default_company_id(self):
        context = self.env.context
        if context.get("default_company_id"):
            return self.env["res.company"].browse(context["default_company_id"])
        for field, model in (
            ("default_workorder_id", "mrp.workorder"),
            ("default_workcenter_id", "mrp.workcenter"),
        ):
            if context.get(field):
                company = self.env[model].browse(context[field]).company_id
                if company:
                    return company
        return self.env.company

    production_id = fields.Many2one(
        comodel_name="mrp.production",
        related="workorder_id.production_id",
        string="Manufacturing Order",
        readonly=True,
    )
    workcenter_id = fields.Many2one(
        comodel_name="mrp.workcenter",
        string="Work Center",
        index=True,
        required=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self._default_company_id(),
        index=True,
        required=True,
    )
    workorder_id = fields.Many2one(
        comodel_name="mrp.workorder",
        string="Work Order",
        index=True,
        check_company=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.uid,
    )
    loss_id = fields.Many2one(
        comodel_name="mrp.workcenter.productivity.loss",
        string="Loss Reason",
        required=True,
        ondelete="restrict",
    )
    loss_type = fields.Selection(
        related="loss_id.loss_type",
        string="Effectiveness",
        readonly=False,
    )
    description = fields.Text()
    date_start = fields.Datetime(
        string="Start Date",
        default=fields.Datetime.now,
        required=True,
    )
    date_end = fields.Datetime(string="End Date")
    duration = fields.Float(
        compute="_compute_duration",
        store=True,
    )

    @api.depends(
        "date_end",
        "date_start",
        "loss_id.loss_type",
        "workcenter_id.resource_calendar_id",
    )
    def _compute_duration(self):
        measured = []
        spans = []
        for blocktime in self:
            if blocktime.date_start and blocktime.date_end:
                measured.append(blocktime)
                spans.append(
                    (
                        blocktime.loss_id,
                        blocktime.workcenter_id,
                        blocktime.date_start.replace(microsecond=0),
                        blocktime.date_end.replace(microsecond=0),
                    )
                )
            else:
                blocktime.duration = 0.0
        durations = self.env["mrp.workcenter.productivity.loss"]._get_durations_batch(
            spans
        )
        for blocktime, duration in zip(measured, durations, strict=True):
            blocktime.duration = duration

    @api.model
    def _get_open_timer_groupby(self):
        return ["workorder_id", "user_id"]

    @api.constrains("workorder_id", "date_end", "user_id")
    def _check_open_time_ids(self):
        workorders = self.workorder_id
        if not workorders:
            return
        duplicated = self._read_group(
            [("workorder_id", "in", workorders.ids), ("date_end", "=", False)],
            self._get_open_timer_groupby(),
            having=[("__count", ">", 1)],
        )
        if duplicated:
            raise ValidationError(
                _(
                    "The Workorder (%s) cannot be started twice!",
                    duplicated[0][0].display_name,
                )
            )

    def button_block(self):
        self.check_singleton()
        self.workcenter_id.order_ids.end_all()

    def _close(self):
        now = fields.Datetime.now()
        underperformance_timers = self.browse()
        split_off = []
        # Every timer closes at the same instant, so it is one write, not one
        # per timer -- and the loop below reads `date_end` back, which is why it
        # is set before rather than inside.
        self.date_end = now
        for timer in self:
            wo = timer.workorder_id
            if wo.duration <= wo.duration_expected:
                continue
            productive_date_end = timer.date_end - timedelta(
                minutes=wo.duration - wo.duration_expected
            )
            if productive_date_end <= timer.date_start:
                underperformance_timers |= timer
            else:
                split_off.append((timer, productive_date_end))
        if split_off:
            copies = self.browse()
            for timer, productive_date_end in split_off:
                copies |= timer.copy({"date_start": productive_date_end})
                timer.date_end = productive_date_end
            underperformance_timers |= copies
        if underperformance_timers:
            underperformance_timers.write(
                {
                    "loss_id": self.env["mrp.workcenter.productivity.loss"]
                    ._get_loss_of_type("performance")
                    .id
                }
            )


class MrpWorkcenterCapacity(models.Model):
    _name = "mrp.workcenter.capacity"
    _description = "Work Center Capacity"
    _check_company_auto = True

    workcenter_id = fields.Many2one(
        comodel_name="mrp.workcenter",
        string="Work Center",
        index=True,
        required=True,
    )
    product_id = fields.Many2one(comodel_name="product.product")
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit",
        compute="_compute_product_uom_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )
    capacity = fields.Float(
        help="Number of pieces that can be produced in parallel for this product or for all, depending on the unit."
    )
    time_start = fields.Float(
        string="Setup Time (minutes)",
        compute="_compute_times",
        precompute=True,
        store=True,
        readonly=False,
        help="Time in minutes for the setup.",
    )
    time_stop = fields.Float(
        string="Cleanup Time (minutes)",
        compute="_compute_times",
        precompute=True,
        store=True,
        readonly=False,
        help="Time in minutes for the cleaning.",
    )

    _positive_capacity = models.Constraint(
        "CHECK(capacity >= 0)",
        "Capacity should be a non-negative number.",
    )
    _workcenter_product_product_uom_unique = models.UniqueIndex(
        "(workcenter_id, COALESCE(product_id, 0), product_uom_id)",
        "Product/Unit capacity should be unique for each workcenter.",
    )

    @api.depends("workcenter_id")
    def _compute_times(self):
        for capacity in self:
            capacity.time_start = capacity.workcenter_id.time_start
            capacity.time_stop = capacity.workcenter_id.time_stop

    @api.depends("product_id")
    def _compute_product_uom_id(self):
        for capacity in self:
            capacity.product_uom_id = capacity.product_id.uom_id or self.env.ref(
                "uom.product_uom_unit"
            )
