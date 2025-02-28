import pytz
from math import modf

from collections import defaultdict
from datetime import datetime, time

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import format_date, format_datetime, format_time
from odoo.tools.float_utils import float_round
from odoo.tools.misc import formatLang


class EventSlot(models.Model):
    _name = "event.slot"
    _description = "Event Slot"
    _order = "date, start_hour, end_hour, id"

    name = fields.Char("Name", compute="_compute_name", store=True)
    event_id = fields.Many2one("event.event", "Event", ondelete="cascade")
    date = fields.Date("Date", required=True)
    start_hour = fields.Float("Starting Hour", required=True, default=8.0, help="Expressed in the event timezone.")
    end_hour = fields.Float("Ending Hour", required=True, default=12.0, help="Expressed in the event timezone.")
    start_datetime = fields.Datetime("Start Datetimes", compute="_compute_datetimes")
    end_datetime = fields.Datetime("End Datetimes", compute="_compute_datetimes")

    # Registrations
    registration_ids = fields.One2many("event.registration", "slot_id", string="Attendees")
    seats_reserved = fields.Integer(
        string="Number of Registrations",
        store=False, readonly=True, compute="_compute_seats")
    seats_available = fields.Integer(
        string="Available Seats",
        store=False, readonly=True, compute="_compute_seats")
    seats_used = fields.Integer(
        string="Number of Attendees",
        store=False, readonly=True, compute="_compute_seats")
    seats_taken = fields.Integer(
        string="Number of Taken Seats",
        store=False, readonly=True, compute="_compute_seats")
    is_sold_out = fields.Boolean(
        "Sold Out", compute="_compute_is_sold_out", store=True,
        help="Whether seats are not available for this slot.")
    # Seats per Ticket
    ticket_limitation_ids = fields.One2many("event.slot.ticket", "slot_id", string="Tickets Limitations")

    @api.constrains("start_hour", "end_hour")
    def _check_hours(self):
        for slot in self:
            if not (0 <= slot.start_hour <= 23.99 and 0 <= slot.end_hour <= 23.99):
                raise ValidationError(_("A slot hour must be between 0:00 and 23:59."))
            elif slot.end_hour <= slot.start_hour:
                raise ValidationError(_("A slot end hour must be later than its start hour.\n%s", slot.name))

    @api.constrains("date", "start_hour", "end_hour")
    def _check_time_range(self):
        for slot in self:
            event_start = slot.event_id.date_begin
            event_end = slot.event_id.date_end
            if not (event_start <= slot.start_datetime <= event_end) or not (event_start <= slot.end_datetime <= event_end):
                raise ValidationError(_(
                    "A slot cannot be scheduled outside of the event time range.\n\n"
                    "Event (%(tz)s):\t%(event_start)s - %(event_end)s\n"
                    "Slot (%(tz)s):\t\t%(slot_name)s",
                    tz=slot.event_id.date_tz,
                    event_start=format_datetime(self.env, event_start, tz=slot.event_id.date_tz, dt_format='medium'),
                    event_end=format_datetime(self.env, event_end, tz=slot.event_id.date_tz, dt_format='medium'),
                    slot_name=slot.name,
                ))

    @api.depends("event_id.date_tz", "date", "start_hour", "end_hour")
    def _compute_datetimes(self):
        for slot in self:
            event_tz = pytz.timezone(slot.event_id.date_tz)
            start = datetime.combine(slot.date, EventSlot._float_to_time(slot.start_hour))
            end = datetime.combine(slot.date, EventSlot._float_to_time(slot.end_hour))
            slot.start_datetime = event_tz.localize(start).astimezone(pytz.UTC).replace(tzinfo=None)
            slot.end_datetime = event_tz.localize(end).astimezone(pytz.UTC).replace(tzinfo=None)

    @api.depends("event_id", "event_id.seats_limited", "seats_available")
    def _compute_is_sold_out(self):
        for slot in self:
            slot.is_sold_out = slot.event_id.seats_limited and not slot.seats_available

    @api.depends("date", "start_hour", "end_hour", "is_sold_out", "event_id", "event_id.seats_max")
    def _compute_name(self):
        for slot in self:
            weekday = format_date(self.env, slot.date, date_format="EEE")
            date = format_date(self.env, slot.date, date_format="long")
            start = format_time(self.env, EventSlot._float_to_time(slot.start_hour), time_format="short")
            end = format_time(self.env, EventSlot._float_to_time(slot.end_hour), time_format="short")
            slot.name = f"{weekday}, {date}, {start} - {end}"

    @api.depends("name")
    @api.depends_context('name_with_seats_availability', 'availability_for_ticket')
    def _compute_display_name(self):
        name_with_availability = self.env.context.get('name_with_seats_availability')
        selected_ticket = self.env.context.get('availability_for_ticket')
        if selected_ticket:
            availability_per_slot = defaultdict(int)
            for slot_ticket in self.ticket_limitation_ids.filtered(lambda slot_ticket: slot_ticket.ticket_id.id == selected_ticket):
                availability_per_slot[slot_ticket.slot_id] += slot_ticket.seats_available

        for slot in self:
            if not name_with_availability or not slot.event_id.seats_limited:
                slot.display_name = slot.name
                continue
            seats_available = availability_per_slot.get(slot) if selected_ticket else slot.seats_available
            if not seats_available:
                slot.display_name = _('%(slot_name)s (Sold out)', slot_name=slot.name)
            else:
                slot.display_name = _(
                    '%(slot_name)s (%(count)s seats remaining)',
                    slot_name=slot.name,
                    count=formatLang(self.env, seats_available, digits=0),
                )

    @api.depends("event_id", "event_id.seats_max", "registration_ids.state", "registration_ids.active")
    def _compute_seats(self):
        # initialize fields to 0
        for slot in self:
            slot.seats_reserved = slot.seats_used = slot.seats_available = 0
        # aggregate registrations by slot and by state
        state_field = {
            'open': 'seats_reserved',
            'done': 'seats_used',
        }
        base_vals = dict.fromkeys(state_field.values(), 0)
        results = {slot_id: dict(base_vals) for slot_id in self.ids}
        if self.ids:
            query = """ SELECT slot_id, state, count(slot_id)
                        FROM event_registration
                        WHERE slot_id IN %s AND state IN ('open', 'done') AND active = true
                        GROUP BY slot_id, state
                    """
            self.env['event.registration'].flush_model(['slot_id', 'state', 'active'])
            self._cr.execute(query, (tuple(self.ids),))
            res = self._cr.fetchall()
            for slot_id, state, num in res:
                results[slot_id][state_field[state]] = num

        # compute seats_available and expected
        for slot in self:
            slot.update(results.get(slot._origin.id or slot.id, base_vals))
            if slot.event_id.seats_max > 0:
                slot.seats_available = slot.event_id.seats_max - (slot.seats_reserved + slot.seats_used)
            slot.seats_taken = slot.seats_reserved + slot.seats_used

    # --------------------------------------
    # Utils
    # --------------------------------------

    @staticmethod
    def _float_to_time(float_time):
        """ Convert the float to an actual datetime time. """
        fractional, integral = modf(float_time)
        return time(int(integral), int(float_round(60 * fractional, precision_digits=0)), 0)
