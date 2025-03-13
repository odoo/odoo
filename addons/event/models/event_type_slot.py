import pytz
from datetime import datetime, time
from math import modf

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_round, format_date, format_time


class EventTypeSlot(models.Model):
    _name = "event.type.slot"
    _description = "Event Template Slot"

    event_type_id = fields.Many2one("event.type", string="Event Category", ondelete="cascade", required=True)
    name = fields.Char("Name", compute="_compute_name", store=True)
    color = fields.Integer("Color", default=0)
    date = fields.Date("Date", required=True)
    date_tz = fields.Selection(related="event_type_id.default_timezone")
    start_hour = fields.Float("Starting Hour", required=True, default=8.0, help="Expressed in the event type timezone.")
    end_hour = fields.Float("Ending Hour", required=True, default=12.0, help="Expressed in the event type timezone.")
    start_datetime = fields.Datetime("Start Datetime", compute="_compute_datetimes", precompute=True, store=True)
    end_datetime = fields.Datetime("End Datetime", compute="_compute_datetimes", precompute=True, store=True)

    @api.constrains("start_hour", "end_hour")
    def _check_hours(self):
        for type_slot in self:
            if not (0 <= type_slot.start_hour <= 23.99 and 0 <= type_slot.end_hour <= 23.99):
                raise ValidationError(_("A slot hour must be between 0:00 and 23:59."))
            elif type_slot.end_hour <= type_slot.start_hour:
                raise ValidationError(_("A slot end hour must be later than its start hour.\n%s", type_slot.name))

    @api.depends("event_type_id.default_timezone", "date", "start_hour", "end_hour")
    def _compute_datetimes(self):
        for type_slot in self:
            if not type_slot.date or not type_slot.start_hour or not type_slot.end_hour:
                type_slot.start_datetime = False
                type_slot.end_datetime = False
                continue
            event_type_tz = pytz.timezone(type_slot.event_type_id.default_timezone)
            start = datetime.combine(type_slot.date, EventTypeSlot._float_to_time(type_slot.start_hour))
            end = datetime.combine(type_slot.date, EventTypeSlot._float_to_time(type_slot.end_hour))
            type_slot.start_datetime = event_type_tz.localize(start).astimezone(pytz.UTC).replace(tzinfo=None)
            type_slot.end_datetime = event_type_tz.localize(end).astimezone(pytz.UTC).replace(tzinfo=None)

    @api.depends("date", "start_hour", "end_hour")
    def _compute_name(self):
        for type_slot in self:
            date = format_date(self.env, type_slot.date, date_format="medium")
            start = format_time(self.env, EventTypeSlot._float_to_time(type_slot.start_hour), time_format="short")
            end = format_time(self.env, EventTypeSlot._float_to_time(type_slot.end_hour), time_format="short")
            type_slot.name = f"{date}, {start} - {end}"

    @api.model
    def _get_fields_whitelist(self):
        """ Whitelist of fields that are copied from event_type_slot_ids to event_slot_ids when
        changing the event_type_id field of event.event """
        return ['color', 'date', 'start_hour', 'end_hour']

    @staticmethod
    def _float_to_time(float_time):
        """ Convert the float to an actual datetime time. """
        fractional, integral = modf(float_time)
        return time(int(integral), int(float_round(60 * fractional, precision_digits=0)), 0)
