import re
from datetime import UTC, datetime, time

from dateutil import rrule
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.datetime import localize_standard, timezone
from odoo.libs.debug_log import DebugLog

from odoo.addons.base.models.mixin_recurrence_anchored import WEEKDAY_SELECTION
from odoo.addons.base.models.mixin_recurrence_rule import (
    REPEAT_TYPE_COUNT,
    REPEAT_TYPE_SELECTION,
)
from odoo.addons.base.models.res_partner import _selection_timezones

_debug = DebugLog(__name__)

REPEAT_TYPE_SELECTION_RRULE = [*REPEAT_TYPE_SELECTION, REPEAT_TYPE_COUNT]

MAX_RECURRENT_OCCURRENCES = 720

SELECT_FREQ_TO_RRULE = {
    "day": rrule.DAILY,
    "week": rrule.WEEKLY,
    "month": rrule.MONTHLY,
    "year": rrule.YEARLY,
}

RRULE_FREQ_TO_SELECT = {v: k for k, v in SELECT_FREQ_TO_RRULE.items()}

RRULE_WEEKDAY_TO_FIELD = {
    rrule.MO.weekday: "mon",
    rrule.TU.weekday: "tue",
    rrule.WE.weekday: "wed",
    rrule.TH.weekday: "thu",
    rrule.FR.weekday: "fri",
    rrule.SA.weekday: "sat",
    rrule.SU.weekday: "sun",
}

RRULE_WEEKDAYS = {
    "SUN": "SU",
    "MON": "MO",
    "TUE": "TU",
    "WED": "WE",
    "THU": "TH",
    "FRI": "FR",
    "SAT": "SA",
}

MONTH_BY_SELECTION = [
    ("date", "Date of month"),
    ("day", "Day of month"),
]

BYDAY_SELECTION = [
    ("1", "First"),
    ("2", "Second"),
    ("3", "Third"),
    ("4", "Fourth"),
    ("-1", "Last"),
]


def freq_to_select(rrule_freq):
    return RRULE_FREQ_TO_SELECT[rrule_freq]


def freq_to_rrule(freq):
    return SELECT_FREQ_TO_RRULE[freq]


def weekday_to_field(weekday_index):
    return RRULE_WEEKDAY_TO_FIELD.get(weekday_index)


class MixinRecurrenceRrule(models.AbstractModel):
    _name = "mixin.recurrence.rrule"
    _description = "iCalendar Recurrence Rule Mixin"
    _inherit = ["mixin.recurrence.rule"]

    name = fields.Char(
        compute="_compute_name",
        store=True,
    )
    event_tz = fields.Selection(
        selection=_selection_timezones,
        string="Timezone",
        default=lambda self: self.env.context.get("tz") or self.env.user.tz,
    )
    rrule = fields.Char(
        compute="_compute_rrule",
        inverse="_inverse_rrule",
        store=True,
    )
    dtstart = fields.Datetime(compute="_compute_dtstart")
    repeat_type = fields.Selection(
        selection_add=[REPEAT_TYPE_COUNT],
        default="count",
        ondelete={REPEAT_TYPE_COUNT[0]: "set default"},
    )
    repeat_number = fields.Integer(
        string="Number of Repetitions",
        default=1,
    )
    mon = fields.Boolean()
    tue = fields.Boolean()
    wed = fields.Boolean()
    thu = fields.Boolean()
    fri = fields.Boolean()
    sat = fields.Boolean()
    sun = fields.Boolean()
    month_by = fields.Selection(
        selection=MONTH_BY_SELECTION,
        default="date",
    )
    day = fields.Integer(default=1)
    weekday = fields.Selection(selection=WEEKDAY_SELECTION)
    byday = fields.Selection(
        selection=BYDAY_SELECTION,
        string="By day",
    )
    repeat_until = fields.Date()

    _month_day = models.Constraint(
        """CHECK (
        repeat_unit != 'month'
        OR (month_by = 'date' AND day >= 1 AND day <= 31)
        OR (month_by = 'day'
            AND weekday IS NOT NULL AND weekday IN %s
            AND byday IS NOT NULL AND byday IN %s))"""
        % (
            tuple(wd[0] for wd in WEEKDAY_SELECTION),
            tuple(bd[0] for bd in BYDAY_SELECTION),
        ),
        "The day must be between 1 and 31",
    )

    def _compute_dtstart(self):
        self.dtstart = False

    def _is_allday(self):
        return False

    def _get_daily_recurrence_name(self):
        if self.repeat_type == "count":
            return _(
                "Every %(interval)s Days for %(count)s events",
                interval=self.repeat_interval,
                count=self.repeat_number,
            )
        if self.repeat_type == "until":
            return _(
                "Every %(interval)s Days until %(until)s",
                interval=self.repeat_interval,
                until=self.repeat_until,
            )
        return _("Every %(interval)s Days", interval=self.repeat_interval)

    def _get_weekly_recurrence_name(self):
        weekday_selection = dict(
            self._fields["weekday"]._description_selection(self.env)
        )
        weekdays = self._get_week_days()
        weekdays = [str(w) for w in weekdays]
        # We need to get the day full name from its three first letters.
        week_map = {v: k for k, v in RRULE_WEEKDAYS.items()}
        weekday_short = [week_map[w] for w in weekdays]
        day_strings = [weekday_selection[day] for day in weekday_short]
        days = ", ".join(day_strings)

        if self.repeat_type == "count":
            return _(
                "Every %(interval)s Weeks on %(days)s for %(count)s events",
                interval=self.repeat_interval,
                days=days,
                count=self.repeat_number,
            )
        if self.repeat_type == "until":
            return _(
                "Every %(interval)s Weeks on %(days)s until %(until)s",
                interval=self.repeat_interval,
                days=days,
                until=self.repeat_until,
            )
        return _(
            "Every %(interval)s Weeks on %(days)s",
            interval=self.repeat_interval,
            days=days,
        )

    def _get_monthly_recurrence_name(self):
        if self.month_by == "day":
            weekday_selection = dict(
                self._fields["weekday"]._description_selection(self.env)
            )
            byday_selection = dict(
                self._fields["byday"]._description_selection(self.env)
            )
            position_label = byday_selection[self.byday]
            weekday_label = weekday_selection[self.weekday]

            if self.repeat_type == "count":
                return _(
                    "Every %(interval)s Months on the %(position)s %(weekday)s for %(count)s events",
                    interval=self.repeat_interval,
                    position=position_label,
                    weekday=weekday_label,
                    count=self.repeat_number,
                )
            if self.repeat_type == "until":
                return _(
                    "Every %(interval)s Months on the %(position)s %(weekday)s until %(until)s",
                    interval=self.repeat_interval,
                    position=position_label,
                    weekday=weekday_label,
                    until=self.repeat_until,
                )
            return _(
                "Every %(interval)s Months on the %(position)s %(weekday)s",
                interval=self.repeat_interval,
                position=position_label,
                weekday=weekday_label,
            )
        else:
            if self.repeat_type == "count":
                return _(
                    "Every %(interval)s Months day %(day)s for %(count)s events",
                    interval=self.repeat_interval,
                    day=self.day,
                    count=self.repeat_number,
                )
            if self.repeat_type == "until":
                return _(
                    "Every %(interval)s Months day %(day)s until %(until)s",
                    interval=self.repeat_interval,
                    day=self.day,
                    until=self.repeat_until,
                )
            return _(
                "Every %(interval)s Months day %(day)s",
                interval=self.repeat_interval,
                day=self.day,
            )

    def _get_yearly_recurrence_name(self):
        if self.repeat_type == "count":
            return _(
                "Every %(interval)s Years for %(count)s events",
                interval=self.repeat_interval,
                count=self.repeat_number,
            )
        if self.repeat_type == "until":
            return _(
                "Every %(interval)s Years until %(until)s",
                interval=self.repeat_interval,
                until=self.repeat_until,
            )
        return _("Every %(interval)s Years", interval=self.repeat_interval)

    def get_recurrence_name(self):
        _debug.logic(
            "recurrence.name",
            record=self.id,
            unit=self.repeat_unit,
            repeat_type=self.repeat_type,
        )
        if self.repeat_unit == "day":
            return self._get_daily_recurrence_name()
        if self.repeat_unit == "week":
            return self._get_weekly_recurrence_name()
        if self.repeat_unit == "month":
            return self._get_monthly_recurrence_name()
        if self.repeat_unit == "year":
            return self._get_yearly_recurrence_name()
        return None

    @api.depends("rrule")
    def _compute_name(self):
        for recurrence in self:
            recurrence.name = recurrence.get_recurrence_name()

    @api.depends(
        "byday",
        "repeat_until",
        "repeat_unit",
        "month_by",
        "repeat_interval",
        "repeat_number",
        "repeat_type",
        "mon",
        "tue",
        "wed",
        "thu",
        "fri",
        "sat",
        "sun",
        "day",
        "weekday",
    )
    def _compute_rrule(self):
        for recurrence in self:
            current_rule = recurrence._rrule_serialize()
            if recurrence.rrule != current_rule:
                _debug.lifecycle(
                    "recurrence.rrule_changed",
                    record=recurrence.id,
                    unit=recurrence.repeat_unit,
                    interval=recurrence.repeat_interval,
                    repeat_type=recurrence.repeat_type,
                    had_rule=bool(recurrence.rrule),
                )
                recurrence.rrule = current_rule

    def _inverse_rrule(self):
        for recurrence in self:
            if _debug.logic.enabled and not recurrence.rrule:
                _debug.logic(
                    "recurrence.rrule_inverse_skipped",
                    record=recurrence.id,
                    reason="empty_rule",
                )
            if recurrence.rrule:
                values = self._rrule_parse(recurrence.rrule, recurrence.dtstart)
                _debug.pipeline(
                    "recurrence.rrule_inverse",
                    record=recurrence.id,
                    keys=",".join(sorted(values)),
                )
                recurrence.with_context(dont_notify=True).write(values)

    def _rrule_serialize(self):
        if self.repeat_interval <= 0:
            _debug.logic(
                "recurrence.serialize_rejected",
                record=self.id,
                reason="interval_not_positive",
            )
            raise UserError(_("The interval cannot be negative."))
        if self.repeat_type == "count" and self.repeat_number <= 0:
            _debug.logic(
                "recurrence.serialize_rejected",
                record=self.id,
                reason="count_not_positive",
            )
            raise UserError(_("The number of repetitions cannot be negative."))
        if (
            self.repeat_type == "count"
            and self.repeat_number > MAX_RECURRENT_OCCURRENCES
        ):
            _debug.logic(
                "recurrence.serialize_rejected",
                record=self.id,
                reason="count_over_maximum",
                count=self.repeat_number,
                maximum=MAX_RECURRENT_OCCURRENCES,
            )
            raise UserError(
                _(
                    "A recurrence cannot repeat more than %(maximum)s times.",
                    maximum=MAX_RECURRENT_OCCURRENCES,
                )
            )

        if not self.repeat_unit:
            _debug.logic("recurrence.serialize.empty", record=self.id)
            return ""
        return self._rrule_value(str(self._get_rrule(bounded=False)))

    @api.model
    def _rrule_value(self, rule_str):
        lines = [line.strip() for line in (rule_str or "").splitlines() if line.strip()]
        for line in lines:
            if line.startswith("RRULE:"):
                return line[len("RRULE:") :]
        _debug.logic("recurrence.rrule_value_bare", lines=len(lines))
        # No RRULE line: a bare ``FREQ=...`` is already the payload; a lone
        # DTSTART is not a rule at all.
        return next((line for line in lines if not line.startswith("DTSTART:")), "")

    @api.model
    def _rrule_parse(self, rule_str, date_start):
        # LUL TODO clean this mess
        data = {}
        day_list = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

        # Skip X-named RRULE extensions
        # TODO Remove patch when dateutils contains the fix
        # HACK https://github.com/dateutil/dateutil/pull/1374
        # Optional parameters starts with X- and they can be placed anywhere in the RRULE string.
        # RRULE:FREQ=MONTHLY;INTERVAL=3;X-RELATIVE=1
        # RRULE;X-EVOLUTION-ENDDATE=20200120:FREQ=WEEKLY;COUNT=3;BYDAY=MO
        # X-EVOLUTION-ENDDATE=20200120:FREQ=WEEKLY;COUNT=3;BYDAY=MO
        stripped = len(rule_str)  # debuglog
        rule_str = (
            re.sub(r";?X-[-\w]+=[^;:]*", "", rule_str).replace(":;", ":").lstrip(":;")
        )
        stripped -= len(rule_str)  # debuglog

        if "Z" in rule_str and date_start and not date_start.tzinfo:
            date_start = date_start.replace(tzinfo=UTC)
        rule = rrule.rrulestr(rule_str, dtstart=date_start)
        _debug.logic(
            "recurrence.rrule_parsed",
            freq=rule._freq,
            interval=rule._interval,
            count=rule._count,
            until=rule._until is not None,
            byweekday=len(rule._byweekday or ()),
            bynweekday=len(rule._bynweekday or ()),
            bymonthday=len(rule._bymonthday or ()),
            x_stripped=stripped,
            utc_marked="Z" in rule_str,
        )

        data["repeat_unit"] = freq_to_select(rule._freq)
        data["repeat_number"] = rule._count
        data["repeat_interval"] = rule._interval
        data["repeat_until"] = rule._until
        # Repeat weekly
        if rule._byweekday:
            for weekday in day_list:
                data[weekday] = False  # reset
            for weekday_index in rule._byweekday:
                weekday = rrule.weekday(weekday_index)
                data[weekday_to_field(weekday.weekday)] = True
                data["repeat_unit"] = "week"

        # Repeat monthly by nweekday ((weekday, weeknumber), )
        if rule._bynweekday:
            data["weekday"] = day_list[next(iter(rule._bynweekday))[0]].upper()
            data["byday"] = str(next(iter(rule._bynweekday))[1])
            data["month_by"] = "day"
            data["repeat_unit"] = "month"

        if rule._bymonthday and data["repeat_unit"] == "month":
            data["day"] = next(iter(rule._bymonthday))
            data["month_by"] = "date"

        if data.get("repeat_until"):
            data["repeat_type"] = "until"
        elif data.get("repeat_number"):
            data["repeat_type"] = "count"
        else:
            data["repeat_type"] = "forever"
        return data

    def _get_lang_week_start(self):
        lang = self.env["res.lang"]._get_data(code=self.env.user.lang)
        week_start = int(lang.week_start)  # lang.week_start ranges from '1' to '7'
        return rrule.weekday(week_start - 1)  # rrule expects an int from 0 to 6

    def _get_start_of_period(self, dt):
        if self.repeat_unit == "week":
            week_start = self._get_lang_week_start()
            start = dt + relativedelta(weekday=week_start(-1))
        elif self.repeat_unit == "month":
            start = dt + relativedelta(day=1)
        else:
            start = dt
        if isinstance(dt, datetime):
            tz = self._get_timezone()
            dst_dt = dt.replace(tzinfo=tz).dst()
            dst_start = start.replace(tzinfo=tz).dst()
            if dst_dt != dst_start:
                _debug.logic(
                    "recurrence.period_start_kept",
                    record=self.id,
                    unit=self.repeat_unit,
                    reason="dst_boundary",
                )
                start = dt
        return start

    def _range_calculation(self, start, duration):
        self.check_singleton()

        def only_future(ranges):
            return {
                (occurrence_start, occurrence_stop)
                for occurrence_start, occurrence_stop in ranges
                if occurrence_start.date() >= start.date()
                and occurrence_stop.date() >= start.date()
            }

        with _debug.perf("recurrence.ranges", record=self.id, unit=self.repeat_unit):
            ranges = only_future(self._get_ranges(start, duration))
        original_count = self.repeat_type == "count" and self.repeat_number
        if original_count and len(ranges) < original_count:
            inflated_count = (2 * original_count) - len(ranges)
            past = len(ranges)  # debuglog
            ranges = only_future(
                self._get_ranges(start, duration, count=inflated_count)
            )
            _debug.logic(
                "recurrence.ranges_inflated",
                record=self.id,
                wanted=original_count,
                first_pass=past,
                inflated_count=inflated_count,
                got=len(ranges),
            )
        return ranges

    def _get_ranges(self, start, occurrence_duration, count=None):
        return (
            (occurrence_start, occurrence_start + occurrence_duration)
            for occurrence_start in self._get_occurrences(start, count=count)
        )

    def _get_timezone(self):
        return timezone(self.event_tz or self.env.context.get("tz") or "UTC")

    def _get_occurrences(self, dtstart, count=None):
        self.check_singleton()
        dtstart = self._get_start_of_period(dtstart)
        if self._is_allday():
            _debug.logic(
                "recurrence.occurrences", record=self.id, allday=True, count=count
            )
            return self._get_rrule(dtstart=dtstart, count=count)

        tz = self._get_timezone()
        _debug.logic(
            "recurrence.occurrences",
            record=self.id,
            allday=False,
            tz=str(tz),
            count=count,
        )
        dtstart = dtstart.replace(tzinfo=UTC).astimezone(tz)
        occurences = self._get_rrule(dtstart=dtstart.replace(tzinfo=None), count=count)

        return (
            localize_standard(occurrence, tz).astimezone(UTC).replace(tzinfo=None)
            for occurrence in occurences
        )

    def _get_week_days(self):
        """
        :return: tuple of rrule weekdays for this recurrence.
        """
        return tuple(
            rrule.weekday(weekday_index)
            for weekday_index, weekday in {
                rrule.MO.weekday: self.mon,
                rrule.TU.weekday: self.tue,
                rrule.WE.weekday: self.wed,
                rrule.TH.weekday: self.thu,
                rrule.FR.weekday: self.fri,
                rrule.SA.weekday: self.sat,
                rrule.SU.weekday: self.sun,
            }.items()
            if weekday
        )

    def _get_rrule(self, dtstart=None, bounded=True, count=None):
        self.check_singleton()
        freq = self.repeat_unit
        rrule_params = {
            "dtstart": dtstart,
            "interval": self.repeat_interval,
        }
        if freq == "month" and self.month_by == "date":  # e.g. every 15th of the month
            rrule_params["bymonthday"] = self.day
        elif (
            freq == "month" and self.month_by == "day"
        ):  # e.g. every 2nd Monday in the month
            rrule_params["byweekday"] = getattr(rrule, RRULE_WEEKDAYS[self.weekday])(
                int(self.byday)
            )  # e.g. MO(+2) for the second Monday of the month
        elif freq == "week":
            weekdays = self._get_week_days()
            if not weekdays:
                _debug.logic(
                    "recurrence.rrule_rejected", record=self.id, reason="no_weekday"
                )
                raise UserError(_("You have to choose at least one day in the week"))
            rrule_params["byweekday"] = weekdays
            rrule_params["wkst"] = self._get_lang_week_start()

        if self.repeat_type == "count":  # e.g. stop after X occurence
            effective_count = self.repeat_number if count is None else count
            rrule_params["count"] = (
                min(effective_count, MAX_RECURRENT_OCCURRENCES)
                if bounded
                else effective_count
            )
        elif self.repeat_type == "forever" and bounded:
            rrule_params["count"] = MAX_RECURRENT_OCCURRENCES
        elif self.repeat_type == "until":  # e.g. stop after 12/10/2020
            rrule_params["until"] = datetime.combine(self.repeat_until, time.max)
        _debug.logic(
            "recurrence.rrule_built",
            record=self.id,
            freq=freq,
            repeat_type=self.repeat_type,
            bounded=bounded,
            count=rrule_params.get("count"),
            has_until="until" in rrule_params,
        )
        return rrule.rrule(freq_to_rrule(freq), **rrule_params)
