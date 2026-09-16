from calendar import monthrange
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools.date_utils import Anchor, anchor_day, next_anchor, previous_anchor

from odoo.addons.base.models.mixin_recurrence_interval import REPEAT_UNIT_SELECTION

_debug = DebugLog(__name__)

WEEKDAY_SELECTION = [
    ("MON", "Monday"),
    ("TUE", "Tuesday"),
    ("WED", "Wednesday"),
    ("THU", "Thursday"),
    ("FRI", "Friday"),
    ("SAT", "Saturday"),
    ("SUN", "Sunday"),
]
WEEKDAY_INDEX = {code: index for index, (code, _label) in enumerate(WEEKDAY_SELECTION)}

DAY_SELECTION = [(str(day), str(day)) for day in range(1, 32)]
LAST_DAY = "last"
ANCHOR_DAY_SELECTION = [*DAY_SELECTION, (LAST_DAY, "Last day")]

MONTH_SELECTION = [
    ("1", "January"),
    ("2", "February"),
    ("3", "March"),
    ("4", "April"),
    ("5", "May"),
    ("6", "June"),
    ("7", "July"),
    ("8", "August"),
    ("9", "September"),
    ("10", "October"),
    ("11", "November"),
    ("12", "December"),
]


# Days and months are Selections of strings rather than integers because the day
# picker narrows its options by the month next to it, and that widget is a
# Selection field; the arithmetic reads them as integers.
class MixinRecurrenceAnchored(models.AbstractModel):
    _name = "mixin.recurrence.anchored"
    _description = "Anchored Recurrence Mixin"

    repeat_unit = fields.Selection(
        selection=REPEAT_UNIT_SELECTION,
        string="Every",
        export_string_translation=False,
        default="month",
        required=True,
    )
    repeat_twice = fields.Boolean(
        string="Twice per Period",
        help="Two anchors in each month or year instead of one",
    )
    repeat_weekday = fields.Selection(
        selection=WEEKDAY_SELECTION,
        string="Weekday",
        default="MON",
    )
    repeat_day = fields.Selection(
        selection=ANCHOR_DAY_SELECTION,
        compute="_compute_repeat_day",
        default="1",
        store=True,
        readonly=False,
    )
    repeat_month = fields.Selection(
        selection=MONTH_SELECTION,
        default="1",
    )
    repeat_second_day = fields.Selection(
        selection=ANCHOR_DAY_SELECTION,
        compute="_compute_repeat_second_day",
        store=True,
        readonly=False,
    )
    repeat_second_month = fields.Selection(
        selection=MONTH_SELECTION,
        default="7",
    )

    @staticmethod
    def _clamp_day(day, month):
        if day == LAST_DAY:
            return day
        return str(min(monthrange(2020, int(month))[1], int(day)))

    @api.depends("repeat_month", "repeat_unit")
    def _compute_repeat_day(self):
        for record in self:
            if (
                record.repeat_unit == "year"
                and record.repeat_day
                and record.repeat_month
            ):
                clamped = self._clamp_day(record.repeat_day, record.repeat_month)
                if _debug.logic.enabled and clamped != record.repeat_day:
                    _debug.logic(
                        "recurrence.anchor_day_clamped",
                        record=record.id,
                        field="repeat_day",
                        month=record.repeat_month,
                        day=record.repeat_day,
                        clamped=clamped,
                    )
                record.repeat_day = clamped

    # The second anchor's default depends on the period: the middle of a month,
    # the first of a half-year. It is filled only once a second anchor exists,
    # so a level created as twice a year, whose period is set after the record
    # is, does not keep the month's default.
    @api.depends("repeat_second_month", "repeat_unit", "repeat_twice")
    def _compute_repeat_second_day(self):
        for record in self:
            if not record.repeat_twice:
                continue
            if not record.repeat_second_day:
                record.repeat_second_day = (
                    "15" if record.repeat_unit == "month" else "1"
                )
                _debug.logic(
                    "recurrence.second_anchor_defaulted",
                    record=record.id,
                    unit=record.repeat_unit,
                    day=record.repeat_second_day,
                )
            elif record.repeat_unit == "year" and record.repeat_second_month:
                clamped = self._clamp_day(
                    record.repeat_second_day, record.repeat_second_month
                )
                if _debug.logic.enabled and clamped != record.repeat_second_day:
                    _debug.logic(
                        "recurrence.anchor_day_clamped",
                        record=record.id,
                        field="repeat_second_day",
                        month=record.repeat_second_month,
                        day=record.repeat_second_day,
                        clamped=clamped,
                    )
                record.repeat_second_day = clamped

    @api.constrains(
        "repeat_unit",
        "repeat_twice",
        "repeat_weekday",
        "repeat_day",
        "repeat_month",
        "repeat_second_day",
        "repeat_second_month",
    )
    def _check_repeat_anchors(self):
        for record in self:
            if record.repeat_unit == "week" and not record.repeat_weekday:
                _debug.logic(
                    "recurrence.anchors_rejected",
                    record=record.id,
                    reason="weekday_missing",
                )
                raise ValidationError(self.env._("A weekly schedule needs a weekday."))
            if not record.repeat_twice or record.repeat_unit not in ("month", "year"):
                continue
            anchors = record._get_recurrence_anchors()
            first, second = map(record._get_boundary_in_reference_period, anchors)
            one_period = relativedelta(**{f"{record.repeat_unit}s": 1})
            _debug.logic(
                "recurrence.anchors_checked",
                record=record.id,
                unit=record.repeat_unit,
                anchors=len(anchors),
                last_day=any(anchor.last_day for anchor in anchors),
                ordered=first < second,
            )
            if any(anchor.last_day for anchor in anchors) and second in (
                first,
                first + one_period,
            ):
                _debug.logic(
                    "recurrence.anchors_rejected",
                    record=record.id,
                    reason="same_period_closed",
                )
                raise ValidationError(
                    self.env._(
                        "The last day of a month and the first day of the next one "
                        "close the same period, so they cannot be the two dates."
                    )
                )
            if first >= second:
                _debug.logic(
                    "recurrence.anchors_rejected",
                    record=record.id,
                    reason="unordered",
                    unit=record.repeat_unit,
                )
                raise ValidationError(
                    self.env._("The first day must be lower than the second day.")
                    if record.repeat_unit == "month"
                    else self.env._(
                        "The first date must be earlier in the year than the second date."
                    )
                )

    # 2024 is a leap year, so no day a record can hold is clamped before it is
    # compared, and January is long enough for every day of a monthly anchor.
    @staticmethod
    def _get_boundary_in_reference_period(anchor):
        first = date(2024, anchor.month or 1, 1)
        if anchor.last_day:
            return first + relativedelta(months=1)
        return first.replace(day=anchor.day)

    @staticmethod
    def _prepare_day_anchor(day, month):
        if day == LAST_DAY:
            return Anchor(month=month, last_day=True)
        return Anchor(day=int(day), month=month)

    def _get_recurrence_anchors(self):
        self.check_singleton()
        unit = self.repeat_unit
        if unit == "day":
            return []
        if unit == "week":
            return [Anchor(weekday=WEEKDAY_INDEX[self.repeat_weekday])]
        month = int(self.repeat_month) if unit == "year" else None
        anchors = [self._prepare_day_anchor(self.repeat_day, month)]
        if self.repeat_twice:
            second_month = int(self.repeat_second_month) if unit == "year" else None
            anchors.append(
                self._prepare_day_anchor(self.repeat_second_day, second_month)
            )
        _debug.logic(
            "recurrence.anchors_built",
            record=self.id,
            unit=unit,
            anchors=len(anchors),
            twice=bool(self.repeat_twice),
        )
        return anchors

    def _get_next_anchor(self, after):
        return next_anchor(after, self.repeat_unit, self._get_recurrence_anchors())

    def _get_previous_anchor(self, on):
        return previous_anchor(on, self.repeat_unit, self._get_recurrence_anchors())

    def _get_anchor_day(self, boundary):
        if self.repeat_unit in ("day", "week"):
            return boundary
        return anchor_day(boundary, self.repeat_unit, self._get_recurrence_anchors())
