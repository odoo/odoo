from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from itertools import chain

from dateutil.relativedelta import relativedelta

from odoo import SUPERUSER_ID, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command, Domain
from odoo.libs.datetime import timezone
from odoo.libs.debug_log import DebugLog
from odoo.libs.intervals import Intervals
from odoo.tools import float_is_zero, ormcache

CRON_BATCH_SIZE = 100

_debug = DebugLog(__name__)


def _default_date_generated(model):
    return datetime.combine(fields.Date.today(), time.min)


class HrVersion(models.Model):
    _inherit = "hr.version"

    date_generated_from = fields.Datetime(
        string="Generated From",
        default=_default_date_generated,
        copy=False,
        readonly=True,
        required=True,
        tracking=True,
        groups="hr.group_hr_user",
    )
    date_generated_to = fields.Datetime(
        string="Generated To",
        default=_default_date_generated,
        copy=False,
        readonly=True,
        required=True,
        tracking=True,
        groups="hr.group_hr_user",
    )
    last_generation_date = fields.Date(
        copy=False,
        readonly=True,
        tracking=True,
        groups="hr.group_hr_user",
    )
    work_entry_source = fields.Selection(
        selection=[("calendar", "Working Schedule")],
        default="calendar",
        required=True,
        tracking=True,
        groups="hr.group_hr_manager",
        help="""
        Defines the source for work entries generation

        Working Schedule: Work entries will be generated from the working hours below.
        Attendances: Work entries will be generated from the employee's attendances. (requires Attendance app)
        Planning: Work entries will be generated from the employee's planning. (requires Planning app)
    """,
    )

    @ormcache()
    def _get_default_work_entry_type_id(self):
        attendance = self.env.ref(
            "hr_work_entry.work_entry_type_attendance", raise_if_not_found=False
        )
        return attendance.id if attendance else False

    @ormcache()
    def _get_default_work_entry_type_overtime_id(self):
        overtime = self.env.ref(
            "hr_work_entry.work_entry_type_overtime", raise_if_not_found=False
        )
        return overtime.id if overtime else False

    def _get_leave_work_entry_type_dates(self, leave, date_from, date_to, employee):
        return self._get_leave_work_entry_type(leave)

    def _get_leave_work_entry_type(self, leave):
        return leave.work_entry_type_id

    def _get_more_vals_attendance_interval(self, interval):
        return []

    def _get_more_vals_leave_interval(self, interval, leaves):
        return []

    def _get_bypassing_work_entry_type_codes(self):
        return []

    def _get_interval_leave_work_entry_type(self, interval, leaves, bypassing_codes):
        self.check_singleton()
        for leave in leaves:
            if interval[0] >= leave[0] and interval[1] <= leave[1] and leave[2]:
                interval_start = interval[0].astimezone(UTC).replace(tzinfo=None)
                interval_stop = interval[1].astimezone(UTC).replace(tzinfo=None)
                return self._get_leave_work_entry_type_dates(
                    leave[2], interval_start, interval_stop, self.employee_id
                )
        return self.env.ref("hr_work_entry.work_entry_type_leave")

    def _get_domain_sub_leave(self):
        return Domain("calendar_id", "in", [False] + self.resource_calendar_id.ids)

    def _get_domain_leave(self, start_dt, end_dt):
        domain = Domain(
            [
                ("resource_id", "in", [False] + self.employee_id.resource_id.ids),
                ("date_from", "<=", end_dt.replace(tzinfo=None)),
                ("date_to", ">=", start_dt.replace(tzinfo=None)),
                ("company_id", "in", [False] + self.company_id.ids),
            ]
        )
        return domain & self._get_domain_sub_leave()

    def _get_schedule_exceptions(self, start_dt, end_dt):
        return self.env["resource.schedule.exception"].search(
            self._get_domain_leave(start_dt, end_dt)
        )

    def _get_attendance_intervals(self, start_dt, end_dt):
        assert start_dt.tzinfo and end_dt.tzinfo, "function expects localized date"
        employees_by_calendar = defaultdict(lambda: self.env["hr.employee"])
        for version in self:
            if version.work_entry_source == "calendar":
                employees_by_calendar[version.resource_calendar_id] |= (
                    version.employee_id
                )
        result = {}
        _debug.perf.count(
            "attendance_intervals", versions=self, calendars=len(employees_by_calendar)
        )
        for calendar, employees in employees_by_calendar.items():
            if not calendar:
                no_attendance = self.env["resource.calendar.attendance"]
                for employee in employees:
                    result[employee.resource_id.id] = Intervals(
                        [(start_dt, end_dt, no_attendance)]
                    )
            else:
                result.update(
                    calendar._attendance_intervals_batch(
                        start_dt,
                        end_dt,
                        resources=employees.resource_id,
                    )
                )
        return result

    def _get_interval_work_entry_type(self, interval):
        self.check_singleton()
        if "work_entry_type_id" in interval[2] and interval[2].work_entry_type_id[:1]:
            return interval[2].work_entry_type_id[:1]
        return self.env["hr.work.entry.type"].browse(
            self._get_default_work_entry_type_id()
        )

    def _get_valid_leave_intervals(self, attendances, interval):
        self.check_singleton()
        return [interval]

    @api.model
    def _get_whitelist_fields_from_template(self):
        return super()._get_whitelist_fields_from_template() + ["work_entry_source"]

    def _prepare_real_attendance_work_entry_vals(self, intervals):
        self.check_singleton()
        vals = []
        for interval in intervals:
            work_entry_type = self._get_interval_work_entry_type(interval)
            vals.append(
                {
                    **self._prepare_work_entry_vals(
                        "%s: %s" % (work_entry_type.name, self.employee_id.name),
                        interval[0],
                        interval[1],
                        work_entry_type,
                    ),
                    **dict(self._get_more_vals_attendance_interval(interval)),
                }
            )
        return vals

    @api.model
    def _split_intervals_per_record(self, intervals):
        split = []
        for start, stop, records in intervals:
            if records and len(records) > 1:
                split += [(start, stop, record) for record in records]
            else:
                split.append((start, stop, records))
        return split

    def _prepare_work_entry_vals(
        self, name, interval_start, interval_stop, work_entry_type
    ):
        self.check_singleton()
        return {
            "name": name,
            "date_start": interval_start.astimezone(UTC).replace(tzinfo=None),
            "date_stop": interval_stop.astimezone(UTC).replace(tzinfo=None),
            "work_entry_type_id": work_entry_type.id,
            "employee_id": self.employee_id.id,
            "version_id": self.id,
            "company_id": self.company_id.id,
        }

    def _get_version_leave_intervals(
        self, leaves_by_resource, attendances, start_dt, end_dt
    ):
        self.check_singleton()
        calendar = self.resource_calendar_id
        resource = self.employee_id.resource_id
        tz = start_dt.tzinfo
        leave_intervals = []
        work_intervals = []
        for leave in chain(leaves_by_resource[False], leaves_by_resource[resource.id]):
            if (
                leave.calendar_id
                and leave.calendar_id != calendar
                and not leave.resource_id
            ):
                continue
            interval = (
                max(start_dt, leave.date_from.replace(tzinfo=UTC).astimezone(tz)),
                min(end_dt, leave.date_to.replace(tzinfo=UTC).astimezone(tz)),
                leave,
            )
            target = work_intervals if leave.time_type_id.is_work else leave_intervals
            target += self._get_valid_leave_intervals(attendances, interval)
        return (
            Intervals(leave_intervals, keep_distinct=True),
            Intervals(work_intervals, keep_distinct=True),
        )

    def _get_real_leave_intervals(
        self, attendances, leaves, worked_leaves, start_dt, end_dt
    ):
        self.check_singleton()
        calendar = self.resource_calendar_id
        if not calendar:
            return leaves, worked_leaves

        if calendar.flexible_hours:
            one_day_leaves = Intervals(
                [l for l in leaves if l[0].date() == l[1].date()], keep_distinct=True
            )
            one_day_worked_leaves = Intervals(
                [l for l in worked_leaves if l[0].date() == l[1].date()],
                keep_distinct=True,
            )
            static_attendances = self._get_static_attendances(start_dt, end_dt)
            return (
                (static_attendances & (leaves - one_day_leaves)) | one_day_leaves,
                (static_attendances & (worked_leaves - one_day_worked_leaves))
                | one_day_worked_leaves,
            )

        if self._has_static_work_entries() or not leaves:
            plain_attendances = attendances - leaves - worked_leaves
            real_worked_leaves = attendances - plain_attendances - leaves
            return (
                attendances - plain_attendances - real_worked_leaves,
                real_worked_leaves,
            )

        static_attendances = self._get_static_attendances(start_dt, end_dt)
        return static_attendances & leaves, static_attendances & worked_leaves

    def _get_static_attendances(self, start_dt, end_dt):
        self.check_singleton()
        resource = self.employee_id.resource_id
        return self.resource_calendar_id._attendance_intervals_batch(
            start_dt, end_dt, resources=resource, tz=start_dt.tzinfo
        )[resource.id]

    def _prepare_worked_leave_work_entry_vals(
        self, intervals, worked_leaves, bypassing_codes
    ):
        self.check_singleton()
        vals = []
        for interval in intervals:
            work_entry_type = self._get_interval_leave_work_entry_type(
                interval, worked_leaves, bypassing_codes
            )
            vals.append(
                {
                    **self._prepare_work_entry_vals(
                        "%s: %s" % (work_entry_type.name, self.employee_id.name),
                        interval[0],
                        interval[1],
                        work_entry_type,
                    ),
                    "state": "draft",
                    **dict(self._get_more_vals_leave_interval(interval, worked_leaves)),
                }
            )
        return vals

    def _prepare_leave_work_entry_vals(self, real_leaves, leaves, bypassing_codes):
        self.check_singleton()
        vals = []
        leaves_over_attendances = Intervals(leaves, keep_distinct=True) & real_leaves
        for interval in real_leaves:
            if interval[0] == interval[1]:
                continue
            leaves_over_interval = [
                (l[0], l[1], interval[2])
                for l in leaves_over_attendances
                if l[0] >= interval[0] and l[1] <= interval[1]
            ]
            for leave_interval in leaves_over_interval:
                leave_entry_type = self._get_interval_leave_work_entry_type(
                    leave_interval, leaves, bypassing_codes
                )
                interval_leaves = [
                    leave
                    for leave in leaves
                    if leave[2].work_entry_type_id.id == leave_entry_type.id
                ] or leaves
                name = self.employee_id.name
                if leave_entry_type:
                    name = "%s: %s" % (leave_entry_type.name, name)
                vals.append(
                    {
                        **self._prepare_work_entry_vals(
                            name, leave_interval[0], leave_interval[1], leave_entry_type
                        ),
                        **dict(
                            self._get_more_vals_leave_interval(
                                interval, interval_leaves
                            )
                        ),
                    }
                )
        return vals

    def _prepare_version_work_entries_values(self, date_start, date_stop):
        start_dt = self._as_utc(date_start)
        end_dt = self._as_utc(date_stop)
        version_vals = []
        bypassing_codes = self._get_bypassing_work_entry_type_codes()

        attendances_by_resource = self.sudo()._get_attendance_intervals(
            start_dt, end_dt
        )

        leaves_by_resource = defaultdict(
            lambda: self.env["resource.schedule.exception"]
        )
        for leave in self._get_schedule_exceptions(start_dt, end_dt):
            leaves_by_resource[leave.resource_id.id] |= leave

        for version in self:
            tz = timezone(version._get_schedule_tz())
            local_start = start_dt.astimezone(tz)
            local_end = end_dt.astimezone(tz)
            resource = version.employee_id.resource_id
            attendances = attendances_by_resource.get(resource.id, Intervals([]))

            leaves, worked_leaves = version._get_version_leave_intervals(
                leaves_by_resource, attendances, local_start, local_end
            )
            real_leaves, real_worked_leaves = version._get_real_leave_intervals(
                attendances, leaves, worked_leaves, local_start, local_end
            )
            real_attendances = self._get_real_attendances(
                attendances, leaves, worked_leaves
            )

            if not version._has_static_work_entries():
                real_attendances = self._split_intervals_per_record(real_attendances)
            leaves = self._split_intervals_per_record(leaves)
            real_worked_leaves = self._split_intervals_per_record(real_worked_leaves)

            version_vals += version._prepare_real_attendance_work_entry_vals(
                real_attendances
            )
            version_vals += version._prepare_worked_leave_work_entry_vals(
                real_worked_leaves, worked_leaves, bypassing_codes
            )
            version_vals += version._prepare_leave_work_entry_vals(
                real_leaves, leaves, bypassing_codes
            )
        return version_vals

    def _get_real_attendances(self, attendances, leaves, worked_leaves):
        return attendances - leaves - worked_leaves

    def _prepare_work_entries_values(self, date_start, date_stop):
        version_vals = self._prepare_version_work_entries_values(date_start, date_stop)
        starts = defaultdict(list)
        stops = defaultdict(list)
        for vals in version_vals:
            starts[vals["version_id"]].append(vals["date_start"])
            stops[vals["version_id"]].append(vals["date_stop"])
        for version in self:
            if version.id not in starts:
                continue
            version.date_generated_from = min(
                version.date_generated_from, *starts[version.id]
            )
            version.date_generated_to = max(
                version.date_generated_to, *stops[version.id]
            )
        return version_vals

    def _has_static_work_entries(self):
        self.check_singleton()
        return self.work_entry_source == "calendar"

    def generate_work_entries(self, date_start, date_stop, force=False):
        date_start = datetime.combine(fields.Date.to_date(date_start), time.min)
        date_stop = datetime.combine(fields.Date.to_date(date_stop), time.max)
        new_work_entries = self.env["hr.work.entry"]
        versions_by_company_tz = self.grouped(
            lambda v: (v.company_id, timezone(v._get_schedule_tz()))
        )
        _debug.pipeline(
            "generate_start",
            versions=self,
            groups=len(versions_by_company_tz),
            start=str(date_start),
            stop=str(date_stop),
            force=force,
        )
        for (company, tz), versions in versions_by_company_tz.items():
            new_work_entries += (
                versions.with_user(SUPERUSER_ID)
                .with_company(company)
                ._generate_work_entries(
                    self._to_naive_utc(date_start, tz),
                    self._to_naive_utc(date_stop, tz),
                    force=force,
                )
            )
        _debug.lifecycle("generate_done", versions=self, entries=new_work_entries)
        return new_work_entries

    @staticmethod
    def _to_naive_utc(local_naive, tz):
        return local_naive.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)

    def _get_version_utc_bounds(self, tz, date_stop):
        self.check_singleton()
        version_start = self._to_naive_utc(
            datetime.combine(self.date_start, time.min), tz
        )
        version_stop = (
            self._to_naive_utc(datetime.combine(self.date_end, time.max), tz)
            if self.date_end
            else date_stop
        )
        return version_start, version_stop

    def _get_domain_expired_work_entries(self, tz, version_stop, date_stop):
        self.check_singleton()
        if version_stop >= date_stop or (
            self.date_generated_from == self.date_generated_to
        ):
            return Domain(False)
        return Domain(
            [
                ("version_id", "=", self.id),
                ("date", ">", version_stop.replace(tzinfo=UTC).astimezone(tz).date()),
                ("date", "<=", date_stop.replace(tzinfo=UTC).astimezone(tz).date()),
                ("state", "!=", "validated"),
            ]
        )

    def _get_domain_forced_work_entries(self, tz, date_from, date_to):
        self.check_singleton()
        return Domain(
            [
                ("version_id", "=", self.id),
                ("date", ">=", date_from.replace(tzinfo=UTC).astimezone(tz).date()),
                ("date", "<=", date_to.replace(tzinfo=UTC).astimezone(tz).date()),
                ("state", "!=", "validated"),
            ]
        )

    def _plan_work_entry_generation(self, date_start, date_stop, force):
        intervals_to_generate = defaultdict(lambda: self.env["hr.version"])
        domain_to_nullify = Domain(False)
        for version in self:
            tz = timezone(version._get_schedule_tz())
            version_start, version_stop = version._get_version_utc_bounds(tz, date_stop)
            domain_to_nullify |= version._get_domain_expired_work_entries(
                tz, version_stop, date_stop
            )
            if date_start > version_stop or date_stop < version_start:
                continue
            date_from = max(date_start, version_start)
            date_to = min(date_stop, version_stop)

            if force:
                domain_to_nullify |= version._get_domain_forced_work_entries(
                    tz, date_from, date_to
                )
                intervals_to_generate[date_from, date_to] |= version
                continue

            last_generated_from = min(version.date_generated_from, version_stop)
            if last_generated_from > date_from:
                version.date_generated_from = date_from
                intervals_to_generate[date_from, last_generated_from] |= version

            last_generated_to = max(version.date_generated_to, version_start)
            if last_generated_to < date_to:
                version.date_generated_to = date_to
                intervals_to_generate[last_generated_to, date_to] |= version
        return intervals_to_generate, domain_to_nullify

    def _generate_work_entries(self, date_start, date_stop, force=False):
        assert isinstance(date_start, datetime)
        assert isinstance(date_stop, datetime)
        self = self.with_context(tracking_disable=True)
        today = fields.Date.today()
        self.filtered(lambda v: v.last_generation_date != today).write(
            {"last_generation_date": today}
        )
        self.filtered(lambda v: v.date_generated_from == v.date_generated_to).write(
            {"date_generated_from": date_start, "date_generated_to": date_start}
        )

        with _debug.perf("plan_generation", cr=self.env.cr, versions=self) as span:
            intervals_to_generate, domain_to_nullify = self._plan_work_entry_generation(
                date_start, date_stop, force
            )
            span.set(intervals=len(intervals_to_generate))

        vals_list = []
        with _debug.perf("build_work_entry_vals", cr=self.env.cr) as span:
            for (date_from, date_to), versions in intervals_to_generate.items():
                vals_list.extend(
                    versions._prepare_work_entries_values(date_from, date_to)
                )
            span.set(rows=len(vals_list))

        if not domain_to_nullify.is_false():
            work_entries = self.env["hr.work.entry"]
            if _debug.lifecycle.enabled:
                _debug.lifecycle(
                    "expired_entries_nullified",
                    entries=work_entries.search(domain_to_nullify),
                )
            work_entries.search(domain_to_nullify).write(
                dict.fromkeys(
                    work_entries._get_fields_to_nullify_on_regeneration(), False
                )
            )

        if not vals_list:
            _debug.logic("generate_nothing", versions=self)
            return self.env["hr.work.entry"]

        return self.env["hr.work.entry"].create(
            self._generate_work_entries_postprocess(vals_list)
        )

    @api.model
    def _generate_work_entries_postprocess_adapt_to_calendar(self, vals):
        if "work_entry_type_id" not in vals:
            return False
        return (
            self.env["hr.work.entry.type"].browse(vals["work_entry_type_id"]).is_leave
        )

    @api.model
    def _split_work_entry_vals_on_local_midnight(self, vals_list, tz_by_version):
        split_vals_list = []
        for vals in vals_list:
            vals = vals.copy()
            if not vals.get("date_start") or not vals.get("date_stop"):
                vals.pop("date_start", False)
                vals.pop("date_stop", False)
                if "duration" not in vals or "date" not in vals:
                    raise UserError(
                        self.env._("Missing date or duration on work entry")
                    )
                split_vals_list.append(vals)
                continue

            tz = tz_by_version[vals["version_id"]]
            local_start = self._as_utc(vals["date_start"]).astimezone(tz)
            local_stop = self._as_utc(vals["date_stop"]).astimezone(tz)

            current = (
                local_start + timedelta(microseconds=1)
                if local_start.time() == time.max
                else local_start
            )
            while current < local_stop:
                next_local_midnight = (
                    datetime.combine(current.date() + timedelta(days=1), time.min)
                    - timedelta(microseconds=1)
                ).replace(tzinfo=tz)
                segment_end = min(local_stop, next_local_midnight)
                split_vals_list.append(
                    {
                        **vals,
                        "date_start": current.astimezone(UTC),
                        "date_stop": segment_end.astimezone(UTC),
                    }
                )
                current = segment_end + timedelta(microseconds=1)
        return split_vals_list

    @staticmethod
    def _as_utc(dt):
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)

    @api.model
    def _resolve_work_entry_vals_duration(self, vals_list, tz_by_version):
        cached_periods = {}
        mapped_periods = defaultdict(
            lambda: defaultdict(lambda: self.env["hr.employee"])
        )
        for vals in vals_list:
            if not vals.get("date_start") or not vals.get("date_stop"):
                continue
            period = (vals["date_start"], vals["date_stop"])
            tz = tz_by_version[vals["version_id"]]
            vals["date"] = period[0].astimezone(tz).date()
            version = self.env["hr.version"].browse(vals["version_id"])
            if not self._generate_work_entries_postprocess_adapt_to_calendar(vals):
                if "duration" in vals:
                    continue
                if period not in cached_periods:
                    cached_periods[period] = (
                        round((period[1] - period[0]).total_seconds()) / 3600
                    )
                vals["duration"] = cached_periods[period]
            elif not version.resource_calendar_id:
                vals["duration"] = 0.0
            else:
                mapped_periods[period][version.resource_calendar_id] |= (
                    version.employee_id
                )

        mapped_version_data = defaultdict(lambda: defaultdict(lambda: {"hours": 0.0}))
        for period, employees_by_calendar in mapped_periods.items():
            for calendar, employees in employees_by_calendar.items():
                mapped_version_data[period][calendar] = (
                    employees._get_work_days_data_batch(
                        period[0], period[1], compute_leaves=False, calendar=calendar
                    )
                )

        for vals in vals_list:
            if "duration" not in vals:
                period = (vals["date_start"], vals["date_stop"])
                version = self.env["hr.version"].browse(vals["version_id"])
                calendar = version.resource_calendar_id
                vals["duration"] = (
                    mapped_version_data[period][calendar][version.employee_id.id][
                        "hours"
                    ]
                    if calendar
                    else 0.0
                )
            vals.pop("date_start", False)
            vals.pop("date_stop", False)
        return vals_list

    @api.model
    def _merge_work_entry_vals(self, vals_list):
        merged_vals = {}
        for vals in vals_list:
            if float_is_zero(vals["duration"], 3):
                continue
            key = (
                vals["date"],
                vals.get("work_entry_type_id", False),
                vals["employee_id"],
                vals["version_id"],
                vals.get("company_id", False),
            )
            if key in merged_vals:
                merged_vals[key]["duration"] += vals["duration"]
            else:
                merged_vals[key] = vals.copy()
        return list(merged_vals.values())

    @api.model
    def _generate_work_entries_postprocess(self, vals_list):
        versions = self.browse({vals["version_id"] for vals in vals_list})
        tz_by_version = {
            version.id: timezone(version._get_schedule_tz()) for version in versions
        }
        vals_list = self._split_work_entry_vals_on_local_midnight(
            vals_list, tz_by_version
        )
        vals_list = self._resolve_work_entry_vals_duration(vals_list, tz_by_version)
        return self._merge_work_entry_vals(vals_list)

    def _remove_work_entries(self):
        before_start = {}
        after_end = {}
        for version in self:
            date_start = fields.Datetime.to_datetime(version.date_start)
            if version.date_generated_from < date_start:
                before_start[version] = date_start
            if not version.date_end:
                continue
            date_end = datetime.combine(version.date_end, time.max)
            if version.date_generated_to > date_end:
                after_end[version] = date_end
        domains = [
            *(
                Domain("date", "<", version.date_start)
                & Domain("version_id", "=", version.id)
                for version in before_start
            ),
            *(
                Domain("date", ">", version.date_end)
                & Domain("version_id", "=", version.id)
                for version in after_end
            ),
        ]
        all_we_to_unlink = self.env["hr.work.entry"]
        if domains:
            all_we_to_unlink = self.env["hr.work.entry"].search(Domain.OR(domains))
        entries_by_version = all_we_to_unlink.grouped("version_id")
        for version, date_start in before_start.items():
            # `hr.work.entry.date` is a Date and the bounds here are Datetimes,
            # so both comparisons are made against the version's own Date fields
            # -- the same values the domains above selected on.
            if any(
                entry.date < version.date_start
                for entry in entries_by_version.get(version, ())
            ):
                version.date_generated_from = date_start
        for version, date_end in after_end.items():
            if any(
                entry.date > version.date_end
                for entry in entries_by_version.get(version, ())
            ):
                version.date_generated_to = date_end
        all_we_to_unlink.unlink()

    def _unlink_work_entries(self):
        if not self:
            return
        domains = []
        for version in self:
            version_domain = Domain("version_id", "=", version.id) & Domain(
                "date", ">=", version.date_start
            )
            if version.date_end:
                version_domain &= Domain("date", "<=", version.date_end)
            domains.append(version_domain)
        domain = Domain.OR(domains) & Domain("state", "!=", "validated")
        self.env["hr.work.entry"].sudo().search(domain).unlink()

    def write(self, vals):
        result = super().write(vals)
        if self.env.context.get("salary_simulation"):
            return result
        if (
            vals.get("contract_date_end")
            or vals.get("contract_date_start")
            or vals.get("date_version")
        ):
            self.sudo()._remove_work_entries()
        dependent_fields = self._get_fields_that_recompute_we()
        if any(key in dependent_fields for key in vals):
            for version_sudo in self.sudo():
                date_from = max(
                    version_sudo.date_start, version_sudo.date_generated_from.date()
                )
                date_to = min(
                    version_sudo.date_end or date.max,
                    version_sudo.date_generated_to.date(),
                )
                if date_from != date_to and version_sudo.employee_id:
                    version_sudo._recompute_work_entries(date_from, date_to)
        return result

    def unlink(self):
        self._unlink_work_entries()
        return super().unlink()

    def _recompute_work_entries(self, date_from, date_to):
        self.check_singleton()
        if self.employee_id:
            wizard = self.env["hr.work.entry.regeneration.wizard"].create(
                {
                    "employee_ids": [Command.set(self.employee_id.ids)],
                    "date_from": date_from,
                    "date_to": date_to,
                }
            )
            wizard.with_context(
                work_entry_skip_validation=True, active_test=False
            ).regenerate_work_entries()

    def _get_fields_that_recompute_we(self):
        return ["resource_calendar_id", "work_entry_source"]

    @api.model
    def _cron_generate_missing_work_entries(self):
        today = fields.Date.today()
        start = datetime.combine(today + relativedelta(day=1), time.min)
        stop = datetime.combine(today + relativedelta(months=1, day=31), time.max)
        versions_todo = self.search(
            [
                ("employee_id", "!=", False),
                ("contract_date_start", "!=", False),
                ("contract_date_start", "<=", stop.date()),
                "|",
                ("contract_date_end", ">=", start.date()),
                ("contract_date_end", "=", False),
                "|",
                ("date_generated_from", ">", start),
                ("date_generated_to", "<", stop),
                "|",
                ("last_generation_date", "=", False),
                ("last_generation_date", "<", today),
            ]
        )
        if not versions_todo:
            _debug.pipeline("cron_generate", versions=0)
            return
        version_todo_count = len(versions_todo)
        _debug.pipeline(
            "cron_generate", versions=version_todo_count, batch=CRON_BATCH_SIZE
        )
        versions_todo = versions_todo.filtered(
            lambda v: v.company_id == versions_todo[0].company_id
        ).sorted(key=lambda v: 1 if v._has_static_work_entries() else 100)
        versions_todo[:CRON_BATCH_SIZE].generate_work_entries(
            start.date(), stop.date(), False
        )
        if version_todo_count > CRON_BATCH_SIZE:
            _debug.logic("cron_retriggered", remaining=version_todo_count)
            self.env.ref(
                "hr_work_entry.ir_cron_generate_missing_work_entries"
            )._trigger()
