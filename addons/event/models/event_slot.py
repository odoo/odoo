import pytz
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.date_utils import float_to_time
from odoo.tools import (
    format_date,
    format_datetime,
    formatLang,
    format_time,
)


class EventSlot(models.Model):
    _name = "event.slot"
    _description = "Event Slot"
    _order = "event_id, date, start_hour, end_hour, id"

    event_id = fields.Many2one("event.event", "Event", required=True, ondelete="cascade", index=True)
    color = fields.Integer("Color", default=0)
    date = fields.Date("Date", required=True)
    date_tz = fields.Selection(related="event_id.date_tz")
    start_hour = fields.Float("Starting Hour", required=True, help="Expressed in the event timezone.")
    end_hour = fields.Float("Ending Hour", required=True, help="Expressed in the event timezone.")
    start_datetime = fields.Datetime("Start Datetime", compute="_compute_datetimes", store=True)
    end_datetime = fields.Datetime("End Datetime", compute="_compute_datetimes", store=True)

    # Registrations
    is_sold_out = fields.Boolean(
        "Sold Out", compute="_compute_is_sold_out",
        help="Whether seats are sold out for this slot.")
    registration_ids = fields.One2many("event.registration", "event_slot_id", string="Attendees")
    seats_available = fields.Integer(
        string="Available Seats",
        store=False, readonly=True, compute="_compute_seats")
    seats_reserved = fields.Integer(
        string="Number of Registrations",
        store=False, readonly=True, compute="_compute_seats")
    seats_taken = fields.Integer(
        string="Number of Taken Seats",
        store=False, readonly=True, compute="_compute_seats")
    seats_used = fields.Integer(
        string="Number of Attendees",
        store=False, readonly=True, compute="_compute_seats")

    @api.constrains("start_hour", "end_hour")
    def _check_hours(self):
        for slot in self:
            if not (0 <= slot.start_hour <= 23.99 and 0 <= slot.end_hour <= 23.99):
                raise ValidationError(_("A slot hour must be between 0:00 and 23:59."))
            if slot.end_hour <= slot.start_hour:
                raise ValidationError(_("A slot end hour must be later than its start hour.\n%s", slot.display_name))

    @api.constrains("date", "start_hour", "end_hour")
    def _check_time_range(self):
        for slot in self:
            event_start = slot.event_id.date_begin
            event_end = slot.event_id.date_end
            if not (event_start <= slot.start_datetime <= event_end) or not (event_start <= slot.end_datetime <= event_end):
                raise ValidationError(_(
                    "A slot cannot be scheduled outside of its event time range.\n\n"
                    "Event:\t\t%(event_start)s - %(event_end)s\n"
                    "Slot:\t\t%(slot_name)s",
                    event_start=format_datetime(self.env, event_start, tz=slot.date_tz, dt_format='medium'),
                    event_end=format_datetime(self.env, event_end, tz=slot.date_tz, dt_format='medium'),
                    slot_name=slot.display_name,
                ))

    @api.depends("date", "date_tz", "start_hour", "end_hour")
    def _compute_datetimes(self):
        for slot in self:
            event_tz = pytz.timezone(slot.date_tz)
            start = datetime.combine(slot.date, float_to_time(slot.start_hour))
            end = datetime.combine(slot.date, float_to_time(slot.end_hour))
            slot.start_datetime = event_tz.localize(start).astimezone(pytz.UTC).replace(tzinfo=None)
            slot.end_datetime = event_tz.localize(end).astimezone(pytz.UTC).replace(tzinfo=None)

    @api.depends("seats_available")
    @api.depends_context('name_with_seats_availability')
    def _compute_display_name(self):
        """Adds slot seats availability if requested by context.
        Always display the name without availabilities if the event is multi slots
        because the availability displayed won't be relative to the possible ticket combinations
        but only relative to the event and this will confuse the user.
        """
        for slot in self:
            date = format_date(self.env, slot.date, date_format="medium")
            start = format_time(self.env, float_to_time(slot.start_hour), time_format="short")
            end = format_time(self.env, float_to_time(slot.end_hour), time_format="short")
            name = f"{date}, {start} - {end}"
            if (
                self.env.context.get('name_with_seats_availability') and slot.event_id.seats_limited
                and not slot.event_id.is_multi_slots
            ):
                name = _('%(slot_name)s (Sold out)', slot_name=name) if not slot.seats_available else \
                    _(
                        '%(slot_name)s (%(count)s seats remaining)',
                        slot_name=name,
                        count=formatLang(self.env, slot.seats_available, digits=0),
                    )
            slot.display_name = name

    @api.depends("event_id.seats_limited", "seats_available")
    def _compute_is_sold_out(self):
        for slot in self:
            slot.is_sold_out = slot.event_id.seats_limited and not slot.seats_available

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
            query = """ SELECT event_slot_id, state, count(event_slot_id)
                        FROM event_registration
                        WHERE event_slot_id IN %s AND state IN ('open', 'done') AND active = true
                        GROUP BY event_slot_id, state
                    """
            self.env['event.registration'].flush_model(['event_slot_id', 'state', 'active'])
            self.env.cr.execute(query, (tuple(self.ids),))
            res = self.env.cr.fetchall()
            for slot_id, state, num in res:
                results[slot_id][state_field[state]] = num
        # compute seats_available
        for slot in self:
            slot.update(results.get(slot._origin.id or slot.id, base_vals))
            if slot.event_id.seats_max > 0:
                slot.seats_available = slot.event_id.seats_max - (slot.seats_reserved + slot.seats_used)
            slot.seats_taken = slot.seats_reserved + slot.seats_used

    @api.ondelete(at_uninstall=False)
    def _unlink_except_if_registrations(self):
        if self.registration_ids:
            raise UserError(_(
                "The following slots cannot be deleted while they have one or more registrations linked to them:\n- %s",
                '\n- '.join(self.mapped('display_name'))))
