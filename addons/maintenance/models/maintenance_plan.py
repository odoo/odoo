from datetime import UTC, datetime
from itertools import count, islice, takewhile

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.date_utils import get_timedelta, occurrences_after


class MaintenancePlan(models.Model):
    _name = "maintenance.plan"
    _inherit = ["mixin.mail.thread", "mixin.mail.activity", "mixin.recurrence.rule"]
    _description = "Maintenance Plan"
    _order = "date_next, id"
    _check_company_auto = True

    name = fields.Char(
        required=True,
        tracking=True,
    )
    active = fields.Boolean(
        default=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    equipment_id = fields.Many2one(
        comodel_name="maintenance.equipment",
        index="btree_not_null",
        ondelete="restrict",
        check_company=True,
        tracking=True,
    )
    maintenance_team_id = fields.Many2one(
        comodel_name="team.team",
        string="Team",
        domain=[("use_maintenance", "=", True)],
        check_company=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Technician",
        tracking=True,
    )
    duration = fields.Float(
        default=1.0,
        help="Duration in hours.",
    )
    priority = fields.Selection(
        selection=[("0", "Very Low"), ("1", "Low"), ("2", "Normal"), ("3", "High")]
    )
    description = fields.Html()
    repeat_unit = fields.Selection(default="month")
    repeat_until = fields.Date(string="End Date")
    repeat_anchor = fields.Selection(
        selection=[
            ("fixed", "Fixed Dates"),
            ("completion", "After Completion"),
        ],
        string="Count From",
        default="fixed",
        required=True,
        tracking=True,
        help="Fixed Dates: every occurrence falls on the series' own dates, and a late "
        "completion skips the dates it missed. After Completion: the next occurrence "
        "is one interval after the day the last one was done.",
    )
    date_start = fields.Datetime(
        string="First Occurrence",
        default=fields.Datetime.now,
        required=True,
        tracking=True,
    )
    request_ids = fields.One2many(
        comodel_name="maintenance.request",
        inverse_name="plan_id",
    )
    request_count = fields.Count(count_of="request_ids")
    date_next = fields.Datetime(
        string="Next Occurrence",
        compute="_compute_dates",
        store=True,
    )
    date_last_done = fields.Date(
        string="Last Done",
        compute="_compute_dates",
        store=True,
    )

    @api.constrains("repeat_type", "repeat_until")
    def _check_until_has_end_date(self):
        if self.filtered(
            lambda plan: plan.repeat_type == "until" and not plan.repeat_until
        ):
            raise ValidationError(
                self.env._("A plan repeated until a date needs its end date.")
            )

    @api.depends(
        "request_ids.schedule_date",
        "request_ids.stage_id.done",
        "request_ids.archive",
        "request_ids.close_date",
    )
    def _compute_dates(self):
        for plan in self:
            requests = plan.request_ids
            plan.date_next = plan._get_open_request().schedule_date
            plan.date_last_done = max(
                requests.filtered("stage_id.done").mapped("close_date"),
                default=False,
            )

    @api.model_create_multi
    def create(self, vals_list):
        plans = super().create(vals_list)
        for plan in plans.filtered(
            lambda plan: plan.active and not plan._get_open_request()
        ):
            plan._create_request(plan.date_start)
        return plans

    def write(self, vals):
        res = super().write(vals)
        if vals.get("active"):
            for plan in self.filtered(lambda plan: not plan._get_open_request()):
                if occurrence := plan._resolve_resumed_occurrence():
                    plan._create_request(occurrence)
        return res

    def _get_open_request(self):
        self.check_singleton()
        return self.request_ids.filtered(
            lambda request: not request.stage_id.done and not request.archive
        ).sorted("schedule_date")[:1]

    def _prepare_request_vals(self, schedule_date):
        self.check_singleton()
        vals = {
            "name": self.name,
            "plan_id": self.id,
            "company_id": self.company_id.id,
            "maintenance_type": "preventive",
            "schedule_date": schedule_date,
            "duration": self.duration,
            "description": self.description,
            "priority": self.priority,
        }
        if self.equipment_id:
            vals["equipment_id"] = self.equipment_id.id
        if self.maintenance_team_id:
            vals["maintenance_team_id"] = self.maintenance_team_id.id
        if self.user_id:
            vals["user_id"] = self.user_id.id
        return vals

    def _create_request(self, schedule_date):
        self.check_singleton()
        return self.env["maintenance.request"].create(
            self._prepare_request_vals(schedule_date)
        )

    def _schedule_after(self, request):
        self.check_singleton()
        if not self.active or self._get_open_request():
            return self.env["maintenance.request"]
        now = fields.Datetime.now()
        planned = request.schedule_date or now
        done_at = now if request.stage_id.done else planned
        occurrence = self._resolve_occurrence_after(planned, done_at)
        if not occurrence:
            return self.env["maintenance.request"]
        if missed := self._count_missed_occurrences(planned, occurrence):
            self.message_post(
                body=self.env._(
                    "%(count)s occurrence(s) skipped: %(request)s was done after them.",
                    count=missed,
                    request=request._get_html_link(),
                )
            )
        return self._create_request(occurrence)

    def _resolve_occurrence_after(self, planned, done_at):
        self.check_singleton()
        if self.repeat_anchor == "completion":
            occurrence = self._get_completion_occurrence(done_at)
        else:
            occurrence = next(self._get_grid_occurrences(max(planned, done_at)))
        return occurrence if self._is_within_until(occurrence) else None

    def _resolve_resumed_occurrence(self):
        self.check_singleton()
        now = fields.Datetime.now()
        if self.repeat_anchor == "fixed":
            occurrence = (
                self.date_start
                if self.date_start > now
                else next(self._get_grid_occurrences(now))
            )
        elif self.date_last_done:
            done_at = datetime.combine(self.date_last_done, self.date_start.time())
            occurrence = max(now, self._get_completion_occurrence(done_at))
        else:
            occurrence = max(now, self.date_start)
        return occurrence if self._is_within_until(occurrence) else None

    def _count_missed_occurrences(self, planned, occurrence):
        if self.repeat_anchor != "fixed":
            return 0
        return sum(
            1
            for _date in takewhile(
                lambda date: date < occurrence, self._get_grid_occurrences(planned)
            )
        )

    def _get_grid_occurrences(self, after):
        return occurrences_after(
            self.date_start, after, self.repeat_interval, self.repeat_unit, self.env.tz
        )

    def _get_completion_occurrence(self, done_at):
        tz = self.env.tz
        local_start = self.date_start.replace(tzinfo=UTC).astimezone(tz)
        local_done = done_at.replace(tzinfo=UTC).astimezone(tz)
        local = datetime.combine(local_done.date(), local_start.timetz())
        occurrence = local + get_timedelta(self.repeat_interval, self.repeat_unit)
        return occurrence.astimezone(UTC).replace(tzinfo=None)

    def _is_within_until(self, occurrence):
        return self.repeat_type != "until" or (
            self.repeat_until
            and fields.Datetime.context_timestamp(self, occurrence).date()
            <= self.repeat_until
        )

    def _get_occurrences_after(self, after, stop=None, limit=None):
        self.check_singleton()
        if self.repeat_anchor == "fixed":
            candidates = self._get_grid_occurrences(after)
        else:
            delta = get_timedelta(self.repeat_interval, self.repeat_unit)
            candidates = (after + delta * k for k in count(1))
        occurrences = takewhile(
            lambda date: (stop is None or date <= stop) and self._is_within_until(date),
            candidates,
        )
        return list(islice(occurrences, limit))

    def action_view_requests(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "maintenance.hr_equipment_request_action"
        )
        action["domain"] = [("plan_id", "=", self.id)]
        action["context"] = {
            "default_plan_id": self.id,
            "default_company_id": self.company_id.id,
        }
        return action
