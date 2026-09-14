from datetime import UTC, datetime
from itertools import count, islice, takewhile

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.datetime import timezone
from odoo.tools.date_utils import get_timedelta, occurrences_after

from odoo.addons.base.models.res_partner import _selection_timezones

RESCHEDULING_FIELDS = frozenset(
    {"date_start", "repeat_anchor", "repeat_interval", "repeat_unit", "tz"}
)


def _occurrence_key(request):
    moment = request.date_occurrence or request.schedule_date
    return (not moment, moment or request.id)


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
    repeat_unit = fields.Selection(
        default="month",
        required=True,
    )
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
    tz = fields.Selection(
        selection=_selection_timezones,
        string="Timezone",
        default=lambda self: (
            self.env.company.partner_id.tz or self.env.user.tz or "UTC"
        ),
        required=True,
        help="The local time the series' dates and days are counted in, whoever closes its requests.",
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
        "request_ids.date_occurrence",
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
            self._ensure_open_request()
        if vals.keys() & RESCHEDULING_FIELDS:
            for plan in self.filtered("active"):
                plan._reschedule_open_request()
        return res

    def _get_open_requests(self):
        self.check_singleton()
        return (
            self.sudo()
            .request_ids.filtered(
                lambda request: not request.stage_id.done and not request.archive
            )
            .sorted(key=_occurrence_key)
            .with_env(self.env)
        )

    def _get_open_request(self):
        return self._get_open_requests()[:1]

    def _get_last_done_request(self):
        self.check_singleton()
        return (
            self.sudo()
            .request_ids.filtered("stage_id.done")
            .sorted(
                key=lambda request: (
                    bool(request.close_date),
                    request.close_date or request.id,
                    _occurrence_key(request),
                )
            )[-1:]
            .with_env(self.env)
        )

    def _get_tzinfo(self):
        self.check_singleton()
        return timezone(self.tz or "UTC")

    def _get_local_date(self, moment):
        return moment.replace(tzinfo=UTC).astimezone(self._get_tzinfo()).date()

    def _prepare_request_vals(self, occurrence, previous=None):
        self.check_singleton()
        vals = previous.copy_data()[0] if previous else {}
        vals.update(
            {
                "name": self.name,
                "plan_id": self.id,
                "company_id": self.company_id.id,
                "maintenance_type": "preventive",
                "schedule_date": occurrence,
                "date_occurrence": occurrence,
                "request_date": fields.Date.context_today(self),
                "duration": self.duration,
                "archive": False,
                "kanban_state": "normal",
            }
        )
        for fname in ("description", "priority"):
            if self[fname]:
                vals[fname] = self[fname]
        for fname in ("equipment_id", "maintenance_team_id", "user_id"):
            if self[fname]:
                vals[fname] = self[fname].id
        return vals

    def _create_request(self, occurrence, previous=None):
        self.check_singleton()
        return self.env["maintenance.request"].create(
            self._prepare_request_vals(occurrence, previous)
        )

    def _ensure_open_request(self):
        for plan in self.filtered(
            lambda plan: plan.active and not plan._get_open_request()
        ):
            if occurrence := plan._resolve_resumed_occurrence():
                plan._create_request(occurrence, plan._get_last_done_request())

    def _reschedule_open_request(self):
        self.check_singleton()
        first_stage = self.env["maintenance.request"]._default_stage_id()
        untouched = self._get_open_requests().filtered(
            lambda request: (
                request.stage_id == first_stage
                and request.date_occurrence
                and request.schedule_date == request.date_occurrence
            )
        )[:1]
        if untouched and (occurrence := self._resolve_resumed_occurrence()):
            untouched.write(
                {"schedule_date": occurrence, "date_occurrence": occurrence}
            )

    def _schedule_after(self, request):
        self.check_singleton()
        if not self.active or self._get_open_request():
            return self.env["maintenance.request"]
        now = fields.Datetime.now()
        planned = request.date_occurrence or request.schedule_date or now
        missed = 0
        if self.repeat_anchor == "completion":
            day = (
                request.close_date
                if request.stage_id.done and request.close_date
                else self._get_local_date(now)
            )
            occurrence = self._get_completion_occurrence(day)
        else:
            occurrence = next(self._get_grid_occurrences(max(planned, now)))
            missed = self._count_missed_occurrences(planned, occurrence)
        if not self._is_within_until(occurrence):
            return self.env["maintenance.request"]
        if missed:
            self.message_post(
                body=self.env._(
                    "%(count)s occurrence(s) skipped: %(request)s was done after them.",
                    count=missed,
                    request=request._get_html_link(),
                )
            )
        return self._create_request(occurrence, request)

    def _resolve_resumed_occurrence(self):
        self.check_singleton()
        now = fields.Datetime.now()
        last = self._get_last_done_request()
        if self.repeat_anchor == "fixed":
            after = max(now, last.date_occurrence or now)
            occurrence = (
                self.date_start
                if self.date_start > after
                else next(self._get_grid_occurrences(after))
            )
        elif last.close_date:
            occurrence = max(now, self._get_completion_occurrence(last.close_date))
        else:
            occurrence = max(now, self.date_start)
        return occurrence if self._is_within_until(occurrence) else None

    def _count_missed_occurrences(self, planned, occurrence):
        return sum(
            1
            for _date in takewhile(
                lambda moment: moment < occurrence, self._get_grid_occurrences(planned)
            )
        )

    def _get_grid_occurrences(self, after):
        return occurrences_after(
            self.date_start,
            after,
            self.repeat_interval,
            self.repeat_unit,
            self._get_tzinfo(),
        )

    def _get_completion_occurrence(self, day, steps=1):
        tz = self._get_tzinfo()
        start_time = self.date_start.replace(tzinfo=UTC).astimezone(tz).time()
        local = datetime.combine(day, start_time).replace(tzinfo=tz)
        delta = get_timedelta(self.repeat_interval, self.repeat_unit) * steps
        return (local + delta).astimezone(UTC).replace(tzinfo=None)

    def _is_within_until(self, occurrence):
        return self.repeat_type != "until" or bool(
            self.repeat_until and self._get_local_date(occurrence) <= self.repeat_until
        )

    def _get_occurrences_after(self, after, stop=None, limit=None):
        self.check_singleton()
        if self.repeat_anchor == "fixed":
            candidates = self._get_grid_occurrences(after)
        else:
            day = self._get_local_date(after)
            candidates = (
                self._get_completion_occurrence(day, steps) for steps in count(1)
            )
        occurrences = takewhile(
            lambda moment: (
                (stop is None or moment <= stop) and self._is_within_until(moment)
            ),
            candidates,
        )
        return list(islice(occurrences, limit))

    def _get_projection_base(self):
        self.check_singleton()
        latest = self._get_open_requests()[-1:]
        occurrence = latest.date_occurrence or latest.schedule_date
        if not occurrence:
            return None
        if self.repeat_anchor == "fixed":
            return max(occurrence, fields.Datetime.now())
        return occurrence

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
