# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import time
from math import modf
from random import randint

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import format_date, format_time
from odoo.tools.float_utils import float_round


def float_to_time(float_time):
    if float_time == 24.0:
        return time.max
    fractional, integral = modf(float_time)
    return time(int(integral), int(float_round(60 * fractional, precision_digits=0)), 0)


def time_to_float(time):
    return float_round(time.hour + time.minute / 60 + time.second / 3600, precision_digits=2)


class EventSlot(models.Model):
    _name = "event.slot"
    _description = "Event Slot"
    _order = "start_datetime asc"

    name = fields.Char("Datetime", compute="_compute_name")
    event_id = fields.Many2one(related="date_id.event_id")
    date_id = fields.Many2one("event.slot.date", "Date", required=True, ondelete="cascade")
    start_datetime = fields.Datetime("Start Datetime", required=True)
    end_datetime = fields.Datetime("End Datetime", required=True)

    @api.depends("start_datetime", "end_datetime")
    def _compute_name(self):
        for slot in self:
            date = format_date(self.env, slot.start_datetime, date_format="full")
            start = format_time(self.env, slot.start_datetime, time_format="short")
            end = format_time(self.env, slot.end_datetime, time_format="short")
            slot.name = f"{date}, {start} - {end}"


class EventSlotTag(models.Model):
    _name = "event.slot.tag"
    _description = "Event Slot Tag"
    _order = "start_time asc"
    _rec_names_search = ['start_time']

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char("Name", required=True)
    color = fields.Integer("Color Index", default=_get_default_color)
    start_time = fields.Float("Slot Start Time", required=True)
    end_time = fields.Float("Slot End Time", required=True)

    @api.constrains("start_time", "end_time")
    def _check_start_and_end_times(self):
        for tag in self:
            start_check = (
                (tag.end_time == 0 and (tag.start_time > 0 and tag.start_time <= 23.99)) or
                (tag.start_time >= 0 and tag.start_time < tag.end_time)
            )
            end_check = tag.end_time == 0 or (tag.start_time < tag.end_time and tag.end_time <= 23.99)
            if not (start_check and end_check):
                raise ValidationError(_("The end time must be later than the start time."))
