from datetime import UTC, datetime
from itertools import count, islice, takewhile

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.libs.datetime import timezone
from odoo.tools.date_utils import get_timedelta, occurrences_after

from .maintenance_order import OPEN_STATES
from odoo.addons.base.models.res_partner import _selection_timezones

RESCHEDULING_FIELDS = frozenset(
    {"date_first_occurrence", "repeat_anchor", "repeat_interval", "repeat_unit", "tz"}
)
ORDER_FIELDS = ("resource_ids", "block_resource")
BOOKING_FIELDS = RESCHEDULING_FIELDS | {
    "active",
    "book_ahead_count",
    "repeat_type",
    "repeat_until",
}


def _occurrence_key(order):
    moment = order.date_plan_slot or order.date_scheduled_start
    return (not moment, moment or order.id)


class MaintenancePlan(models.Model):
    _name = "maintenance.plan"
    _inherit = ["mixin.mail.thread", "mixin.mail.activity", "mixin.recurrence.rule"]
    _description = "Maintenance Plan"
    _order = "date_next_scheduled, id"
    _check_company_auto = True

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
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
    name = fields.Char(
        required=True,
        tracking=True,
    )
    active = fields.Boolean(
        default=True,
        tracking=True,
    )
    priority = fields.Selection(
        selection=[("0", "Very Low"), ("1", "Low"), ("2", "Normal"), ("3", "High")]
    )
    resource_ids = fields.Many2many(
        comodel_name="resource.resource",
        relation="maintenance_plan_resource_rel",
        column1="plan_id",
        column2="resource_id",
        string="Maintained Resources",
        domain="[('resource_type', '=', 'material')]",
        check_company=True,
        tracking=True,
    )
    block_resource = fields.Boolean(
        default=True,
        help="Each order of this plan blocks its resources' time while it is confirmed or in progress.",
    )
    book_ahead_count = fields.Integer(
        string="Occurrences to Book Ahead",
        help="Block the resources for this many further occurrences in advance. Only a plan on fixed dates knows them.",
    )
    duration = fields.Float(
        default=1.0,
        help="Duration in hours.",
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
        help="The local time the series' dates and days are counted in, whoever closes its orders.",
    )
    date_first_occurrence = fields.Datetime(
        string="First Occurrence",
        default=fields.Datetime.now,
        required=True,
        tracking=True,
    )
    order_ids = fields.One2many(
        comodel_name="maintenance.order",
        inverse_name="plan_id",
    )
    order_count = fields.Count(count_of="order_ids")
    date_next_scheduled = fields.Datetime(
        string="Next Scheduled",
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

    @api.model_create_multi
    def create(self, vals_list):
        plans = super().create(vals_list)
        for plan in plans.filtered(
            lambda plan: plan.active and not plan._get_open_order()
        ):
            plan._create_order(plan.date_first_occurrence)
        return plans

    def write(self, vals):
        quiet = self.with_context(skip_maintenance_reservations=True)
        res = super(MaintenancePlan, quiet).write(vals)
        if vals.get("active"):
            self._create_missing_open_orders()
        if vals.keys() & RESCHEDULING_FIELDS:
            for plan in quiet.filtered("active"):
                plan._reschedule_open_order()
        order_vals = {fname: vals[fname] for fname in ORDER_FIELDS if fname in vals}
        if not order_vals and not vals.keys() & BOOKING_FIELDS:
            return res
        open_orders = self.env["maintenance.order"].concat(
            *(plan._get_open_orders() for plan in self)
        )
        if order_vals:
            open_orders.with_context(skip_maintenance_reservations=True).write(
                order_vals
            )
        open_orders._recreate_reservations(refuse_taken_window=False)
        return res

    @api.depends(
        "order_ids.date_scheduled_start",
        "order_ids.date_plan_slot",
        "order_ids.state",
        "order_ids.date_done",
    )
    def _compute_dates(self):
        for plan in self:
            orders = plan.order_ids
            plan.date_next_scheduled = plan._get_open_order().date_scheduled_start
            plan.date_last_done = max(
                orders.filtered(lambda order: order.state == "done").mapped(
                    "date_done"
                ),
                default=False,
            )

    def _get_open_orders(self):
        self.check_singleton()
        return (
            self.sudo()
            .order_ids.filtered(lambda order: order.state in OPEN_STATES)
            .sorted(key=_occurrence_key)
            .with_env(self.env)
        )

    def _get_open_order(self):
        return self._get_open_orders()[:1]

    def _get_last_done_order(self):
        self.check_singleton()
        return (
            self.sudo()
            .order_ids.filtered(lambda order: order.state == "done")
            .sorted(
                key=lambda order: (
                    bool(order.date_done),
                    order.date_done or order.id,
                    _occurrence_key(order),
                )
            )[-1:]
            .with_env(self.env)
        )

    def _get_tzinfo(self):
        self.check_singleton()
        return timezone(self.tz or "UTC")

    def _get_local_date(self, moment):
        return moment.replace(tzinfo=UTC).astimezone(self._get_tzinfo()).date()

    def _prepare_order_vals(self, occurrence, previous=None):
        self.check_singleton()
        vals = previous.copy_data()[0] if previous else {}
        vals.update(
            {
                "name": self.name,
                "plan_id": self.id,
                "company_id": self.company_id.id,
                "maintenance_type": "preventive",
                "date_scheduled_start": occurrence,
                "date_plan_slot": occurrence,
                "duration": self.duration,
                "state": "confirmed",
                "kanban_state": "normal",
            }
        )
        for fname in ("description", "priority"):
            if self[fname]:
                vals[fname] = self[fname]
        for fname in ("maintenance_team_id", "user_id"):
            if self[fname]:
                vals[fname] = self[fname].id
        vals["resource_ids"] = [Command.set(self.resource_ids.ids)]
        vals["block_resource"] = self.block_resource
        return vals

    def _create_order(self, occurrence, previous=None):
        self.check_singleton()
        return self.env["maintenance.order"].create(
            self._prepare_order_vals(occurrence, previous)
        )

    def _create_missing_open_orders(self):
        for plan in self.filtered(
            lambda plan: plan.active and not plan._get_open_order()
        ):
            if occurrence := plan._resolve_resumed_occurrence():
                plan._create_order(occurrence, plan._get_last_done_order())

    def _reschedule_open_order(self):
        self.check_singleton()
        untouched = self._get_open_orders().filtered(
            lambda order: (
                order.state == "confirmed"
                and order.date_plan_slot
                and order.date_scheduled_start == order.date_plan_slot
            )
        )[:1]
        if untouched and (occurrence := self._resolve_resumed_occurrence()):
            untouched.write(
                {"date_scheduled_start": occurrence, "date_plan_slot": occurrence}
            )

    def _schedule_after(self, order):
        self.check_singleton()
        if not self.active or self._get_open_order():
            return self.env["maintenance.order"]
        now = fields.Datetime.now()
        planned = order.date_plan_slot or order.date_scheduled_start or now
        missed = 0
        if self.repeat_anchor == "completion":
            day = (
                order.date_done
                if order.state == "done" and order.date_done
                else self._get_local_date(now)
            )
            occurrence = self._get_completion_occurrence(day)
        else:
            occurrence = next(self._get_grid_occurrences(max(planned, now)))
            missed = self._count_missed_occurrences(planned, occurrence)
        if not self._is_within_until(occurrence):
            return self.env["maintenance.order"]
        if missed:
            self.message_post(
                body=self.env._(
                    "%(count)s occurrence(s) skipped: %(order)s was done after them.",
                    count=missed,
                    order=order._get_html_link(),
                )
            )
        return self._create_order(occurrence, order)

    def _resolve_resumed_occurrence(self):
        self.check_singleton()
        now = fields.Datetime.now()
        last = self._get_last_done_order()
        if self.repeat_anchor == "fixed":
            after = max(now, last.date_plan_slot or now)
            occurrence = (
                self.date_first_occurrence
                if self.date_first_occurrence > after
                else next(self._get_grid_occurrences(after))
            )
        elif last.date_done:
            occurrence = max(now, self._get_completion_occurrence(last.date_done))
        else:
            occurrence = max(now, self.date_first_occurrence)
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
            self.date_first_occurrence,
            after,
            self.repeat_interval,
            self.repeat_unit,
            self._get_tzinfo(),
        )

    def _get_completion_occurrence(self, day, steps=1):
        tz = self._get_tzinfo()
        start_time = (
            self.date_first_occurrence.replace(tzinfo=UTC).astimezone(tz).time()
        )
        local = datetime.combine(day, start_time).replace(tzinfo=tz)
        delta = get_timedelta(self.repeat_interval, self.repeat_unit) * steps
        return (local + delta).astimezone(UTC).replace(tzinfo=None)

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
        latest = self._get_open_orders()[-1:]
        occurrence = latest.date_plan_slot or latest.date_scheduled_start
        if not occurrence:
            return None
        if self.repeat_anchor == "fixed":
            return max(occurrence, fields.Datetime.now())
        return occurrence

    def action_view_orders(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "maintenance.maintenance_order_action"
        )
        action["domain"] = [("plan_id", "=", self.id)]
        action["context"] = {
            "default_plan_id": self.id,
            "default_company_id": self.company_id.id,
        }
        return action

    def _is_within_until(self, occurrence):
        return self.repeat_type != "until" or bool(
            self.repeat_until and self._get_local_date(occurrence) <= self.repeat_until
        )
