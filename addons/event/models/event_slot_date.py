# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
from datetime import datetime, timedelta

from odoo import _, api, Command, fields, models
from odoo.addons.event.models.event_slot import float_to_time, time_to_float
from odoo.exceptions import ValidationError
from odoo.tools import format_datetime, format_time


class EventSlotDate(models.Model):
    _name = "event.slot.date"
    _description = "Event Slot Date"

    event_id = fields.Many2one("event.event", string="Event", ondelete="cascade")
    date = fields.Date("Date", required=True)
    slot_ids = fields.One2many("event.slot", "date_id", "Slots", compute="_compute_slots", store=True)
    slot_tag_ids = fields.Many2many("event.slot.tag", string="Slots tags")
    weekday = fields.Selection([
        ('1', 'Monday'),
        ('2', 'Tuesday'),
        ('3', 'Wednesday'),
        ('4', 'Thursday'),
        ('5', 'Friday'),
        ('6', 'Saturday'),
        ('7', 'Sunday'),
    ], string="Week Day", compute="_compute_weekday", readonly=True)

    # TODO: check for start AND end

    # @api.constrains("slot_ids")
    # def _check_slots(self):
    #     for slot_date in self:
    #         wrong_slot_datetimes = [
    #             format_datetime(self.env, slot_datetime, dt_format='short', tz=slot.event_id.date_tz)
    #             for slot_datetime in slot_date.slot_ids.mapped('slot_datetime')
    #             if slot_datetime < slot.event_id.date_begin or slot_datetime > slot.event_id.date_end
    #         ]
    #         if wrong_slot_datetimes:
    #             raise ValidationError(_(
    #                 'You cannot schedule slots outside of their event time range:\n%s',
    #                 '\n'.join(f'- {dt}' for dt in wrong_slot_datetimes)
    #             ))

    @api.depends("event_id.date_tz", "date", "slot_tag_ids.start_time", "slot_tag_ids.end_time")
    def _compute_slots(self):
        for slot_date in self:
            slot_date.slot_ids.unlink()
            slot_date.slot_ids = [
                Command.create({
                    'date_id': slot_date,
                    'start_datetime': self._convert_from_event_tz_to_utc(
                        datetime.combine(
                            slot_date.date,
                            float_to_time(tag.start_time)
                        )
                    ),
                    'end_datetime': self._convert_from_event_tz_to_utc(
                        datetime.combine(
                            slot_date.date,
                            float_to_time(tag.end_time)
                        )
                    ),
                })
                for tag in slot_date.slot_tag_ids
            ]

    # TODO: default la premiere ligne dans event.event depends on multi_slots
    # compute les autres lignes ici

    # @api.depends("event_id")
    # def _compute_details(self):
    #     """ Defaults slot date and time to 7 days after the last event slot
    #     (if later than the event end datetime, defaults to nothing).
    #     If the event doesn't have any slot yet, defaults the slot to the start datetime of the event.
    #     """
    #     for slot_date in self:
    #         existing_dates = slot_date.event_id.slot_date_ids - slot_date
    #         if existing_dates:
    #             last_date = existing_dates.sorted(lambda slot: slot.date, reverse=True)[0]
    #             if all(dt + timedelta(days=7) <= slot_date.event_id.date_end for dt in last_date.slot_ids.mapped('slot_datetime')):
    #                 slot_date.date = last_date.date + timedelta(days=7)
    #                 slot_date.slot_tag_ids = last_date.slot_tag_ids

    @api.depends("date")
    def _compute_weekday(self):
        for slot in self:
            slot.weekday = str(slot.date.weekday() + 1) if slot.date else False

    @api.model
    def _convert_from_event_tz_to_utc(self, datetime):
        event_tz = pytz.timezone(self.event_id.date_tz)
        return event_tz.localize(datetime).astimezone(pytz.UTC).replace(tzinfo=None)

    @api.model
    def _convert_from_utc_to_event_tz(self, datetime):
        event_tz = pytz.timezone(self.event_id.date_tz)
        return pytz.UTC.localize(datetime).astimezone(event_tz).replace(tzinfo=None)
