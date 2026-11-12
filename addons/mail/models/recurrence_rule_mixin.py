import re
from datetime import datetime, time, UTC
from zoneinfo import ZoneInfo
from dateutil import rrule

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.addons.base.models.res_partner import _tz_get

from .recurrence_utils import (
    RRULE_TYPE_SELECTION, END_TYPE_SELECTION, MONTH_BY_SELECTION,
    WEEKDAY_SELECTION, BYDAY_SELECTION, RRULE_WEEKDAYS, WEEKDAY_TO_RRULE,
    freq_to_select, freq_to_rrule, weekday_to_field
)


class RecurrenceRuleMixin(models.AbstractModel):
    _name = 'mail.recurrence.rule.mixin'
    _description = 'Recurrence Engine'

    name = fields.Char(compute='_compute_name', store=True)
    recurrence_tz = fields.Selection(
        _tz_get, string='Timezone',
        default=lambda self: self.env.context.get('tz') or self.env.user.tz)
    rrule = fields.Char(compute='_compute_rrule', inverse='_inverse_rrule', store=True)
    dtstart = fields.Datetime(compute='_compute_dtstart')
    rrule_type = fields.Selection(RRULE_TYPE_SELECTION, default='weekly')
    end_type = fields.Selection(END_TYPE_SELECTION, default='forever')
    interval = fields.Integer(default=1)
    count = fields.Integer(default=1)
    mon = fields.Boolean()
    tue = fields.Boolean()
    wed = fields.Boolean()
    thu = fields.Boolean()
    fri = fields.Boolean()
    sat = fields.Boolean()
    sun = fields.Boolean()
    month_by = fields.Selection(MONTH_BY_SELECTION, default='date')
    day = fields.Integer(default=1)
    weekday = fields.Selection(WEEKDAY_SELECTION, string='Weekday')
    byday = fields.Selection(BYDAY_SELECTION, string='By day')
    until = fields.Date('Repeat Until')

    _month_day = models.Constraint("""CHECK (
        rrule_type != 'monthly'
        OR month_by != 'day'
        OR day >= 1 AND day <= 31
        OR weekday IN %s AND byday IN %s)""" % (
            tuple(wd[0] for wd in WEEKDAY_SELECTION),
            tuple(bd[0] for bd in BYDAY_SELECTION),
        ),
        "The day must be between 1 and 31",
    )

    def _get_daily_recurrence_name(self):
        if self.end_type == 'count':
            return self.env._("Every %(interval)s Days for %(count)s occurrences", interval=self.interval, count=self.count)
        if self.end_type == 'end_date':
            return self.env._("Every %(interval)s Days until %(until)s", interval=self.interval, until=self.until)
        return self.env._("Every %(interval)s Days", interval=self.interval)

    def _get_weekly_recurrence_name(self):
        weekday_selection = dict(self._fields['weekday']._description_selection(self.env))
        weekdays = self._get_week_days()
        # Convert Weekday object
        weekdays = [str(w) for w in weekdays]
        # We need to get the day full name from its three first letters.
        week_map = {v: k for k, v in RRULE_WEEKDAYS.items()}
        weekday_short = [week_map[w] for w in weekdays]
        day_strings = [weekday_selection[day] for day in weekday_short]
        days = ", ".join(day_strings)

        if self.end_type == 'count':
            return self.env._("Every %(interval)s Weeks on %(days)s for %(count)s occurrences", interval=self.interval, days=days, count=self.count)
        if self.end_type == 'end_date':
            return self.env._("Every %(interval)s Weeks on %(days)s until %(until)s", interval=self.interval, days=days, until=self.until)
        return self.env._("Every %(interval)s Weeks on %(days)s", interval=self.interval, days=days)

    def _get_monthly_recurrence_name(self):
        if self.month_by == 'day':
            weekday_selection = dict(self._fields['weekday']._description_selection(self.env))
            byday_selection = dict(self._fields['byday']._description_selection(self.env))
            position_label = byday_selection[self.byday]
            weekday_label = weekday_selection[self.weekday]

            if self.end_type == 'count':
                return self.env._("Every %(interval)s Months on the %(position)s %(weekday)s for %(count)s occurrences", interval=self.interval, position=position_label, weekday=weekday_label, count=self.count)
            if self.end_type == 'end_date':
                return self.env._("Every %(interval)s Months on the %(position)s %(weekday)s until %(until)s", interval=self.interval, position=position_label, weekday=weekday_label, until=self.until)
            return self.env._("Every %(interval)s Months on the %(position)s %(weekday)s", interval=self.interval, position=position_label, weekday=weekday_label)
        else:
            if self.end_type == 'count':
                return self.env._("Every %(interval)s Months day %(day)s for %(count)s occurrences", interval=self.interval, day=self.day, count=self.count)
            if self.end_type == 'end_date':
                return self.env._("Every %(interval)s Months day %(day)s until %(until)s", interval=self.interval, day=self.day, until=self.until)
            return self.env._("Every %(interval)s Months day %(day)s", interval=self.interval, day=self.day)

    def _get_yearly_recurrence_name(self):
        if self.end_type == 'count':
            return self.env._("Every %(interval)s Years for %(count)s occurrences", interval=self.interval, count=self.count)
        if self.end_type == 'end_date':
            return self.env._("Every %(interval)s Years until %(until)s", interval=self.interval, until=self.until)
        return self.env._("Every %(interval)s Years", interval=self.interval)

    def get_recurrence_name(self):
        if self.rrule_type == 'daily':
            return self._get_daily_recurrence_name()
        if self.rrule_type == 'weekly':
            return self._get_weekly_recurrence_name()
        if self.rrule_type == 'monthly':
            return self._get_monthly_recurrence_name()
        if self.rrule_type == 'yearly':
            return self._get_yearly_recurrence_name()

    @api.depends('rrule')
    def _compute_name(self):
        for recurrence in self:
            recurrence.name = recurrence.get_recurrence_name()

    @api.depends(
    'byday', 'until', 'rrule_type', 'month_by', 'interval', 'count', 'end_type',
    'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', 'day', 'weekday')
    def _compute_rrule(self):
        for recurrence in self:
            current_rule = recurrence._rrule_serialize()
            if recurrence.rrule != current_rule:
                recurrence.write({'rrule': current_rule})

    @api.depends()
    def _compute_dtstart(self):
        for rule in self:
            rule.dtstart = False

    def _inverse_rrule(self):
        for recurrence in self:
            if recurrence.rrule:
                values = recurrence._rrule_parse(
                    recurrence.rrule, recurrence.dtstart, until_tz=recurrence._get_timezone(),
                )
                recurrence.with_context(dont_notify=True).write(values)

    def _rrule_serialize(self):
        """
        Compute rule string according to value type RECUR of iCalendar
        :return: string containing recurring rule (empty if no rule)
        """
        if self.interval <= 0:
            raise UserError(self.env._('The interval cannot be negative.'))
        if self.end_type == 'count' and self.count <= 0:
            raise UserError(self.env._('The number of repetitions cannot be negative.'))

        return str(self._get_rrule()) if self.rrule_type else ''

    @api.model
    def _rrule_parse(self, rule_str, date_start, until_tz=None):
        """Parse an RRULE string into recurrence field values.

        :param until_tz: timezone used to convert an aware (``UNTIL=...Z``) end
            boundary into a local date. Defaults to the recurrence timezone; if
            none is known, the UTC date is kept as is.
        """
        # LUL TODO clean this mess
        data = {}
        day_list = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

        # Skip X-named RRULE extensions
        # TODO Remove patch when dateutils contains the fix
        # HACK https://github.com/dateutil/dateutil/pull/1374
        # Optional parameters starts with X- and they can be placed anywhere in the RRULE string.
        # RRULE:FREQ=MONTHLY;INTERVAL=3;X-RELATIVE=1
        # RRULE;X-EVOLUTION-ENDDATE=20200120:FREQ=WEEKLY;COUNT=3;BYDAY=MO
        # X-EVOLUTION-ENDDATE=20200120:FREQ=WEEKLY;COUNT=3;BYDAY=MO
        rule_str = re.sub(r';?X-[-\w]+=[^;:]*', '', rule_str).replace(":;", ":").lstrip(":;")

        if 'Z' in rule_str and date_start and not date_start.tzinfo:
            date_start = date_start.replace(tzinfo=UTC)
        rule = rrule.rrulestr(rule_str, dtstart=date_start)

        data['rrule_type'] = freq_to_select(rule._freq)
        data['count'] = rule._count
        data['interval'] = rule._interval
        until = rule._until
        if until:
            if until.tzinfo:
                recurrence_tz = self[:1].recurrence_tz
                tz = until_tz or (ZoneInfo(recurrence_tz) if recurrence_tz else None)
                if tz:
                    until = until.astimezone(tz)
            until = until.date()
        data['until'] = until
        # Repeat weekly
        if rule._byweekday:
            for weekday in day_list:
                data[weekday] = False  # reset
            for weekday_index in rule._byweekday:
                weekday = rrule.weekday(weekday_index)
                data[weekday_to_field(weekday.weekday)] = True
                data['rrule_type'] = 'weekly'

        # Repeat monthly by nweekday ((weekday, weeknumber), )
        if rule._bynweekday:
            weekday_index, weeknumber = next(iter(rule._bynweekday))
            data['weekday'] = day_list[weekday_index].upper()
            data['byday'] = str(weeknumber)
            data['month_by'] = 'day'
            data['rrule_type'] = 'monthly'

        if rule._bymonthday and data['rrule_type'] == 'monthly':
            data['day'] = next(iter(rule._bymonthday))
            data['month_by'] = 'date'

        if data.get('until'):
            data['end_type'] = 'end_date'
        elif data.get('count'):
            data['end_type'] = 'count'
        else:
            data['end_type'] = 'forever'
        return data

    def _get_lang_week_start(self):
        lang = self.env['res.lang']._get_data(code=self.env.user.lang)
        week_start = int(lang.week_start)  # lang.week_start ranges from '1' to '7'
        return rrule.weekday(week_start - 1)  # rrule expects an int from 0 to 6

    def _get_timezone(self):
        return ZoneInfo(self.recurrence_tz or self.env.context.get('tz') or 'UTC')

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
            }.items() if weekday
        )

    def _get_recurrence_limit_years(self):
        return 15

    def _get_max_occurrences(self):
        return 720

    def _get_rrule(self, dtstart=None):
        self.ensure_one()
        freq = self.rrule_type
        rrule_params = dict(
            dtstart=dtstart,
            interval=self.interval,
        )
        if freq == 'monthly' and self.month_by == 'date':
            rrule_params['bymonthday'] = self.day
        elif freq == 'monthly' and self.month_by == 'day':
            rrule_params['byweekday'] = WEEKDAY_TO_RRULE[self.weekday](int(self.byday))  # e.g. MO(+2) for the second Monday of the month
        elif freq == 'weekly':
            weekdays = self._get_week_days()
            if not weekdays:
                raise UserError(self.env._("You have to choose at least one day in the week"))
            rrule_params['byweekday'] = weekdays
            rrule_params['wkst'] = self._get_lang_week_start()

        # Limit the number of years to avoid creating recurrent events for up to hundreds of years
        limit_years = self._get_recurrence_limit_years()
        max_events = self._get_max_occurrences()
        if self.end_type == 'count':
            rrule_params['count'] = min(self.count, max_events)
        elif self.end_type == 'forever':
            if freq == 'yearly':
                rrule_params['count'] = min(limit_years, max_events)
            elif freq == 'monthly':
                rrule_params['count'] = min(limit_years * 12, max_events)
            elif freq == 'weekly':
                weekdays = len(self._get_week_days())
                weeks = limit_years * 365 // 7
                rrule_params['count'] = min(weeks * weekdays // max(self.interval, 1), max_events)
            else:
                rrule_params['count'] = min(limit_years * 365 // max(self.interval, 1), max_events)
        elif self.end_type == 'end_date':
            rrule_params['until'] = datetime.combine(self.until, time.max)
        return rrule.rrule(freq_to_rrule(freq), **rrule_params)
