# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
from math import modf

from datetime import datetime, time

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import format_datetime, format_time
from odoo.tools.float_utils import float_round


class EventSlotWeekday(models.Model):
    _name = "event.slot.weekday"
    _description = "Event Slot Weekday"
    _order = "sequence"

    name = fields.Char("Name", required=True)
    sequence = fields.Integer("Sequence", required=True)
    color = fields.Integer("Color")


class EventSlot(models.Model):
    _name = "event.slot"
    _description = "Event Slot"
    _order = "is_recurrent DESC, date, start_hour, end_hour, id"

    # TODO: exclude date?

    # TODO: seats_limited (event and ticket) per slot instead of for the whole event
    # TODO: Check each tab
    # TODO: once all the generation are good, we can go further with the mailing and slots picking
    # TODO: mailing: Actually to simplify also the way we will handle multi slots events
    # (to avoid having if and else everywhere), we decided that it would be good to store
    # the event date on the attendee. So when generating emails, we will use the date stored
    # on the attendee (whether it’s the date of the event or the date of the slot). So if an attendee
    # registers to an event and it is not a multi slot event, we will store on the attendee the date
    # of the event, otherwise if it’s a multi slot event we will store in the attendee the date of
    # the selected slot. When generating the emails, the date to display will be the date stored on
    # the attendee. So in summary in the generated emails, i think we should keep it the way it is
    # displayed (since we added a start time & end time to a slot) but now we will use the dates stored
    # on the attendee in any case.

    name = fields.Char("Name", compute="_compute_name")
    event_id = fields.Many2one("event.event", "Event", ondelete="cascade")
    start_hour = fields.Float("Starting Hour", required=True, default=8.0, help="Expressed in the event timezone.")
    end_hour = fields.Float("Ending Hour", required=True, default=12.0, help="Expressed in the event timezone.")
    start_datetime = fields.Datetime("Start Datetimes", compute="_compute_datetimes")
    end_datetime = fields.Datetime("End Datetimes", compute="_compute_datetimes")
    is_recurrent = fields.Boolean("Is Recurrent", compute="_compute_is_recurrent", store=True)
    # Punctual
    date = fields.Date("Date")
    # Recurrent
    weekdays = fields.Many2many("event.slot.weekday", "Weekday")

    @api.constrains("start_hour", "end_hour")
    def _check_hours(self):
        for slot in self:
            if not (0 <= slot.start_hour <= 23.99 and 0 <= slot.end_hour <= 23.99):
                raise ValidationError(_("A slot hour must be between 0:00 and 23:59."))
            elif slot.end_hour <= slot.start_hour:
                raise ValidationError(_("A slot end hour must be later than its start hour.\n%s", slot.name))

    @api.constrains("date", "start_hour", "end_hour")
    def _check_datetime_range(self):
        for slot in self:
            if not slot.is_recurrent:
                event_start = slot.event_id.date_begin
                event_end = slot.event_id.date_end
                if not (event_start <= slot.start_datetime <= event_end) or not (event_start <= slot.end_datetime <= event_end):
                    raise ValidationError(_(
                        "A slot cannot be scheduled outside of the event time range.\n\n"
                        "Event (%(tz)s):\t%(event_start)s - %(event_end)s\n"
                        "Slot (%(tz)s):\t%(slot_name)s",
                        tz=slot.event_id.date_tz,
                        event_start=slot.event_id.date_begin_located,
                        event_end=slot.event_id.date_end_located,
                        slot_name=slot.name,
                    ))

    @api.constrains("date", "weekdays")
    def _check_recurrence_type(self):
        for slot in self:
            if slot.date and slot.weekdays:
                raise ValidationError(_("A slot cannot have both a date and week day recurrences."))
            elif not slot.date and not slot.weekdays:
                raise ValidationError(_("A slot must have a date or week day recurrence."))

    @api.depends("event_id.date_tz", "date", "start_hour", "end_hour")
    def _compute_datetimes(self):
        for slot in self:
            if slot.is_recurrent:
                slot.start_datetime = False
                slot.end_datetime = False
                continue
            event_tz = pytz.timezone(self.event_id.date_tz)
            start = datetime.combine(slot.date, EventSlot._float_to_time(slot.start_hour))
            end = datetime.combine(slot.date, EventSlot._float_to_time(slot.end_hour))
            slot.start_datetime = event_tz.localize(start).astimezone(pytz.UTC).replace(tzinfo=None)
            slot.end_datetime = event_tz.localize(end).astimezone(pytz.UTC).replace(tzinfo=None)

    @api.depends("weekdays")
    def _compute_is_recurrent(self):
        for slot in self:
            slot.is_recurrent = bool(slot.weekdays)

    @api.depends("event_id.date_tz", "date", "weekdays", "start_hour", "end_hour")
    def _compute_name(self):
        for slot in self:
            if slot.is_recurrent:
                start = format_time(self.env, EventSlot._float_to_time(slot.start_hour), time_format="short")
                end = format_time(self.env, EventSlot._float_to_time(slot.end_hour), time_format="short")
                weekdays = " ".join(slot.weekdays.mapped("name"))
                slot.name = f"Every {weekdays}, {start} - {end}"
                continue
            start = format_datetime(self.env, slot.start_datetime, tz=slot.event_id.date_tz, dt_format='medium')
            end = format_datetime(self.env, slot.end_datetime, tz=slot.event_id.date_tz, dt_format='medium')
            slot.name = f"{start} - {end}"

    @api.onchange("date")
    def _onchange_date(self):
        for slot in self:
            if slot.date:
                slot.weekdays = False

    @api.onchange("weekdays")
    def _onchange_weekdays(self):
        for slot in self:
            if slot.weekdays:
                slot.date = False

    # --------------------------------------
    # Utils
    # --------------------------------------

    @staticmethod
    def _float_to_time(float_time):
        """ Convert the float to an actual datetime time. """
        fractional, integral = modf(float_time)
        return time(int(integral), int(float_round(60 * fractional, precision_digits=0)), 0)
