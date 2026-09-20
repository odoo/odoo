from contextlib import contextmanager
from datetime import UTC, datetime, time
from itertools import chain

from psycopg import OperationalError

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.libs.intervals import Intervals
from odoo.tools import float_compare

CLOSED_STATES = ("validated", "cancelled")
FIELDS_TRIGGERING_CHECK = frozenset(
    {"date", "duration", "employee_id", "work_entry_type_id", "active"}
)

_debug = DebugLog(__name__)


class HrWorkEntry(models.Model):
    _name = "hr.work.entry"
    _description = "HR Work Entry"
    _order = "date, id"

    name = fields.Char()
    active = fields.Boolean(default=True)
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        index=True,
        required=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    version_id = fields.Many2one(
        comodel_name="hr.version",
        string="Employee Record",
        index=True,
        required=True,
    )
    work_entry_source = fields.Selection(related="version_id.work_entry_source")
    date = fields.Date(required=True)
    duration = fields.Float(default=8)
    work_entry_type_id = fields.Many2one(
        comodel_name="hr.work.entry.type",
        default=lambda self: self.env.ref(
            "hr_work_entry.work_entry_type_attendance", raise_if_not_found=False
        ),
        index=True,
        domain=lambda self: self._get_domain_work_entry_type(),
    )
    display_code = fields.Char(related="work_entry_type_id.display_code")
    code = fields.Char(related="work_entry_type_id.code")
    external_code = fields.Char(related="work_entry_type_id.external_code")
    color = fields.Integer(
        related="work_entry_type_id.color",
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "New"),
            ("conflict", "In Conflict"),
            ("validated", "In Payslip"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        readonly=True,
        required=True,
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        related="employee_id.department_id",
    )
    amount_rate = fields.Float(
        string="Pay rate",
        compute="_compute_amount_rate",
        store=True,
        readonly=False,
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        related="employee_id.company_id.country_id",
    )

    _contract_date_start_stop_idx = models.Index(
        "(version_id, date) WHERE state IN ('draft', 'validated')"
    )
    _employee_date_active_idx = models.Index("(employee_id, date) WHERE active")

    @api.constrains("duration")
    def _check_duration(self):
        for work_entry in self:
            if (
                float_compare(work_entry.duration, 0, 3) <= 0
                or float_compare(work_entry.duration, 24, 3) > 0
            ):
                _debug.logic(
                    "duration_refused",
                    entry=work_entry,
                    duration=work_entry.duration,
                )
                raise ValidationError(
                    self.env._("Duration must be positive and cannot exceed 24 hours.")
                )

    @api.depends("work_entry_type_id.name", "duration")
    def _compute_display_name(self):
        for work_entry in self:
            hours, minutes = divmod(round(work_entry.duration * 60), 60)
            work_entry.display_name = "%s - %dh%02d" % (
                work_entry.work_entry_type_id.name or self.env._("Undefined Type"),
                hours,
                minutes,
            )

    @api.depends("work_entry_type_id")
    def _compute_amount_rate(self):
        for work_entry in self:
            work_entry.amount_rate = work_entry.work_entry_type_id.amount_rate

    @api.onchange("employee_id", "date")
    def _onchange_employee_id_date(self):
        if self.employee_id and self.date:
            self.version_id = self.employee_id._get_version(self.date)

    @api.model
    def _complete_version_id(self, vals):
        if not vals.get("version_id") and vals.get("date") and vals.get("employee_id"):
            employee = self.env["hr.employee"].browse(vals["employee_id"])
            vals["version_id"] = employee._get_version(vals["date"]).id
        return vals

    @api.model
    def get_unusual_days(self, date_from, date_to):
        employee = self.env["hr.employee"].browse(
            self.env.context.get("default_employee_id")
        )
        calendar = (
            employee.resource_calendar_id or self.env.company.resource_calendar_id
        )
        return calendar._get_unusual_days(
            datetime.combine(fields.Date.from_string(date_from), time.min, UTC),
            datetime.combine(fields.Date.from_string(date_to), time.max, UTC),
            self.env.company,
        )

    def action_validate(self):
        work_entries = self.filtered(lambda w: w.state not in CLOSED_STATES)
        if work_entries._check_if_error():
            _debug.logic("validate_refused", reason="conflicts", entries=work_entries)
            return False
        _debug.lifecycle("validate", entries=work_entries)
        work_entries.write({"state": "validated"})
        return True

    def action_set_to_draft(self):
        return self.write({"state": "draft"})

    def action_split(self, vals):
        self.check_singleton()
        if self.state == "validated":
            raise UserError(self.env._("You can't split a validated work entry."))
        if self.duration < 1:
            raise UserError(
                self.env._("You can't split a work entry with less than 1 hour.")
            )
        split_duration = vals["duration"]
        if not 0 < split_duration < self.duration:
            raise UserError(
                self.env._(
                    "Split work entry duration has to be less than the existing work entry duration."
                )
            )
        self.write({"duration": self.duration - split_duration})
        split_work_entry = self.copy()
        split_work_entry.write({**vals, "state": "draft"})
        _debug.lifecycle(
            "split", origin=self, split=split_work_entry, duration=split_duration
        )
        return split_work_entry.id

    def _check_if_error(self):
        open_entries = self.filtered(lambda w: w.state not in CLOSED_STATES)
        if not open_entries:
            return False
        undefined_type = open_entries.filtered(lambda w: not w.work_entry_type_id)
        undefined_type.write({"state": "conflict"})
        dates = open_entries.mapped("date")
        with _debug.perf("error_check", cr=self.env.cr, entries=open_entries) as span:
            excessive = open_entries._mark_conflicting_work_entries(
                min(dates), max(dates)
            )
            outside_schedule = open_entries._mark_leaves_outside_schedule()
            validated_days = open_entries._mark_already_validated_days()
            span.set(
                undefined_type=len(undefined_type),
                excessive=excessive,
                outside_schedule=outside_schedule,
                validated_days=validated_days,
            )
        return bool(undefined_type) or excessive or outside_schedule or validated_days

    def _mark_conflicting_work_entries(self, start, stop):
        self.flush_model(["date", "duration", "employee_id", "active", "state"])
        query = """
            WITH excessive_days AS (
                SELECT employee_id, date
                FROM hr_work_entry
                WHERE active = TRUE
                  AND date BETWEEN %(start)s AND %(stop)s
                  AND employee_id = ANY(%(employee_ids)s)
                GROUP BY employee_id, date
                HAVING SUM(duration) > 24
            )
            SELECT we.id
            FROM hr_work_entry we
            JOIN excessive_days ed
              ON we.employee_id = ed.employee_id
             AND we.date = ed.date
            WHERE we.active = TRUE
              AND we.state NOT IN ('validated', 'cancelled')
        """
        self.env.cr.execute(
            query,
            {"start": start, "stop": stop, "employee_ids": self.employee_id.ids},
        )
        conflict_ids = [row[0] for row in self.env.cr.fetchall()]
        _debug.logic(
            "conflicts_over_24h",
            entries=self.browse(conflict_ids),
            employees=self.employee_id,
        )
        self.browse(conflict_ids).write({"state": "conflict"})
        return bool(conflict_ids)

    def _filtered_leaves_outside_schedule(self):
        return self.filtered(
            lambda w: w.work_entry_type_id.is_leave and w.state not in CLOSED_STATES
        )

    def _mark_leaves_outside_schedule(self):
        entries_by_calendar = self._filtered_leaves_outside_schedule().grouped(
            lambda w: w.version_id.resource_calendar_id
        )
        outside_entries = self.env["hr.work.entry"]
        for calendar, entries in entries_by_calendar.items():
            if not calendar or calendar.flexible_hours:
                continue
            dates = entries.mapped("date")
            attendances = calendar._attendance_intervals_batch(
                datetime.combine(min(dates), time.min, UTC),
                datetime.combine(max(dates), time.max, UTC),
                tz=UTC,
            )[False]
            working_days = [start.date() for start, _stop, _records in attendances]
            outside_entries |= entries.filtered_domain(
                [("date", "not in", working_days)]
            )
        _debug.logic(
            "conflicts_outside_schedule",
            entries=outside_entries,
            calendars=len(entries_by_calendar),
        )
        outside_entries.write({"state": "conflict"})
        return bool(outside_entries)

    def _mark_already_validated_days(self):
        dates = self.mapped("date")
        validated = (
            self.env["hr.work.entry"]
            .sudo()
            .search_fetch(
                [
                    ("state", "=", "validated"),
                    ("employee_id", "in", self.employee_id.ids),
                    ("date", ">=", min(dates)),
                    ("date", "<=", max(dates)),
                ],
                ["employee_id", "date"],
            )
        )
        validated_days = {(w.employee_id.id, w.date) for w in validated}
        invalid_entries = self.filtered(
            lambda w: (w.employee_id.id, w.date) in validated_days
        )
        _debug.logic(
            "conflicts_already_validated",
            entries=invalid_entries,
            validated_days=len(validated_days),
        )
        invalid_entries.write({"state": "conflict"})
        return bool(invalid_entries)

    def _to_intervals(self):
        return Intervals(
            (
                (
                    datetime.combine(w.date, time.min, UTC),
                    datetime.combine(w.date, time.max, UTC),
                    w,
                )
                for w in self
            ),
            keep_distinct=True,
        )

    @api.model
    def _from_intervals(self, intervals):
        return self.browse(
            chain.from_iterable(records.ids for _start, _stop, records in intervals)
        )

    @api.model
    def _get_fields_to_nullify_on_regeneration(self):
        return ["active"]

    @api.model
    def _sync_state_and_active(self, vals):
        if "state" in vals:
            vals["active"] = vals["state"] != "cancelled"
        elif vals.get("active") is False:
            vals["state"] = "cancelled"
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [
            self._sync_state_and_active(self._complete_version_id(dict(vals)))
            for vals in vals_list
        ]
        employee_ids = {
            vals["employee_id"]
            for vals in vals_list
            if not vals.get("company_id") and vals.get("employee_id")
        }
        if employee_ids:
            company_by_employee_id = {
                employee.id: employee.company_id.id
                for employee in self.env["hr.employee"].browse(employee_ids)
            }
            for vals in vals_list:
                if not vals.get("company_id") and vals.get("employee_id"):
                    vals["company_id"] = company_by_employee_id[vals["employee_id"]]
        work_entries = super().create(vals_list)
        _debug.lifecycle("create", entries=work_entries, count=len(vals_list))
        work_entries.employee_id.invalidate_recordset(["has_work_entries"])
        work_entries._check_if_error()
        return work_entries

    def _write_needs_check(self, vals):
        if self.env.context.get("hr_work_entry_no_check"):
            return False
        if vals.keys() & FIELDS_TRIGGERING_CHECK:
            return True
        if vals.get("state") == "draft":
            return any(w.state != "draft" for w in self)
        if vals.get("state") == "cancelled":
            return any(w.state == "conflict" for w in self)
        return False

    def write(self, vals):
        if vals.get("active") is True and "state" not in vals:
            self.filtered(lambda w: w.state == "cancelled").with_context(
                hr_work_entry_no_check=True
            ).write({"state": "draft"})
        vals = self._sync_state_and_active(vals)
        _debug.lifecycle("write", entries=self, fields=list(vals))
        if not self._write_needs_check(vals):
            _debug.logic("write_skips_check", entries=self, fields=list(vals))
            return super().write(vals)
        employee_ids = set(self.employee_id.ids)
        if vals.get("employee_id"):
            employee_ids.add(vals["employee_id"])
        siblings = self._reset_conflicts(employee_ids)
        _debug.pipeline("write_rechecks", entries=self, siblings=siblings)
        result = super().write(vals)
        (siblings | siblings.browse(self.ids)).exists()._check_if_error()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_except_validated_work_entries(self):
        if any(w.state == "validated" for w in self):
            _debug.logic("unlink_refused", reason="validated", entries=self)
            raise UserError(
                self.env._("This work entry is validated. You can't delete it.")
            )

    def unlink(self):
        employees = self.employee_id
        _debug.lifecycle("unlink", entries=self, employees=employees)
        siblings = self._reset_conflicts(employees.ids)
        result = super().unlink()
        siblings.exists()._check_if_error()
        employees.invalidate_recordset(["has_work_entries"])
        return result

    def _reset_conflicting_state(self):
        _debug.pipeline("conflicts_reset", entries=self)
        self.filtered(lambda w: w.state == "conflict").write({"state": "draft"})

    def _reset_conflicts(self, employee_ids):
        dates = self.mapped("date")
        if not dates:
            return self.browse()
        return self._reset_conflicts_between(min(dates), max(dates), employee_ids)

    def _reset_conflicts_between(self, start, stop, employee_ids):
        if self.env.context.get("hr_work_entry_no_check"):
            return self.browse()
        siblings = (
            self.sudo()
            .with_context(hr_work_entry_no_check=True)
            .search(
                Domain("employee_id", "in", list(employee_ids))
                & Domain("date", ">=", start)
                & Domain("date", "<=", stop)
                & Domain("state", "not in", CLOSED_STATES)
            )
        )
        siblings._reset_conflicting_state()
        return siblings

    @contextmanager
    def _error_checking(self, start=None, stop=None, skip=False, *, employee_ids):
        siblings = self.browse()
        if not skip and start and stop:
            siblings = self._reset_conflicts_between(start, stop, employee_ids)
        try:
            yield
        except OperationalError:
            siblings = self.browse()
            raise
        finally:
            siblings.exists()._check_if_error()

    def _get_domain_work_entry_type(self):
        if len(self.env.companies.country_id.ids) > 1:
            _debug.logic("work_entry_types", by="multi_country")
            return [("country_id", "=", False)]
        return [
            "|",
            ("country_id", "=", False),
            ("country_id", "in", self.env.companies.country_id.ids),
        ]
