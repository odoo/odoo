from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools.date_utils import get_timedelta, next_after, time_unit_selection

_debug = DebugLog(__name__)

REPEAT_UNIT_SELECTION = time_unit_selection("day", "week", "month", "year")


class MixinRecurrenceInterval(models.AbstractModel):
    _name = "mixin.recurrence.interval"
    _description = "Recurrence Interval Mixin"

    repeat_interval = fields.Integer(
        string="Repeat Every",
        default=1,
    )
    repeat_unit = fields.Selection(
        selection=REPEAT_UNIT_SELECTION,
        export_string_translation=False,
        default="week",
    )

    @api.constrains("repeat_interval")
    def _check_repeat_interval(self):
        if invalid := self.filtered(lambda record: record.repeat_interval <= 0):
            _debug.logic(
                "recurrence.interval_rejected",
                model=self._name,
                records=invalid,
                reason="not_positive",
            )
            raise ValidationError(self.env._("The interval should be greater than 0"))

    def _get_recurrence_delta(self):
        self.check_singleton()
        return get_timedelta(self.repeat_interval, self.repeat_unit)

    def _get_next_recurrence_after(self, start, after, tz=None):
        self.check_singleton()
        _debug.logic(
            "recurrence.next_after",
            record=self.id,
            interval=self.repeat_interval,
            unit=self.repeat_unit,
            tz=tz,
        )
        return next_after(start, after, self.repeat_interval, self.repeat_unit, tz)
