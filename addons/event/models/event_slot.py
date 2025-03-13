import pytz
from datetime import datetime

from odoo import _, api, fields, models
from odoo.addons.event.models.event_type_slot import EventTypeSlot
from odoo.exceptions import ValidationError
from odoo.tools import format_datetime
from odoo.tools.misc import formatLang


class EventSlot(models.Model):
    _name = "event.slot"
    _inherit = ['event.type.slot']
    _description = "Event Slot"
    _order = "event_id, date, start_hour, end_hour, id"

    event_id = fields.Many2one("event.event", "Event", required=True, ondelete="cascade")
    event_type_id = fields.Many2one("event.type", ondelete='set null', required=False)
    date_tz = fields.Selection(related="event_id.date_tz")
    start_hour = fields.Float(help="Expressed in the event timezone.")
    end_hour = fields.Float(help="Expressed in the event timezone.")

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
        "Sold Out", compute="_compute_is_sold_out",
        help="Whether seats are not available for this slot.")
    event_slot_ticket_ids = fields.One2many("event.slot.ticket", "slot_id", string="Tickets Seats")

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
                    tz=slot.date_tz,
                    event_start=format_datetime(self.env, event_start, tz=slot.date_tz, dt_format='medium'),
                    event_end=format_datetime(self.env, event_end, tz=slot.date_tz, dt_format='medium'),
                    slot_name=slot.name,
                ))

    @api.depends("date", "date_tz", "start_hour", "end_hour")
    def _compute_datetimes(self):
        for slot in self:
            if not slot.date or not slot.start_hour or not slot.end_hour:
                slot.start_datetime = False
                slot.end_datetime = False
                continue
            event_tz = pytz.timezone(slot.date_tz)
            start = datetime.combine(slot.date, EventTypeSlot._float_to_time(slot.start_hour))
            end = datetime.combine(slot.date, EventTypeSlot._float_to_time(slot.end_hour))
            slot.start_datetime = event_tz.localize(start).astimezone(pytz.UTC).replace(tzinfo=None)
            slot.end_datetime = event_tz.localize(end).astimezone(pytz.UTC).replace(tzinfo=None)

    @api.depends("event_id", "event_id.seats_limited", "seats_available")
    def _compute_is_sold_out(self):
        for slot in self:
            slot.is_sold_out = slot.event_id.seats_limited and not slot.seats_available

    @api.depends("name")
    @api.depends_context('name_with_seats_availability')
    def _compute_display_name(self):
        """Adds slot seats availability if requested by context."""
        for slot in self:
            if not self.env.context.get('name_with_seats_availability') or not slot.event_id.seats_limited:
                slot.display_name = slot.name
                continue
            if not slot.seats_available:
                slot.display_name = _('%(slot_name)s (Sold out)', slot_name=slot.name)
            else:
                slot.display_name = _(
                    '%(slot_name)s (%(count)s seats remaining)',
                    slot_name=slot.name,
                    count=formatLang(self.env, slot.seats_available, digits=0),
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

    @api.model_create_multi
    def create(self, vals_list):
        new_slots = super().create(vals_list)
        # Create missing slot-ticket combinations when a new slot is added
        existing_combinations = [(slot_ticket.slot_id.id, slot_ticket.ticket_id.id) for slot_ticket in self.env['event.slot.ticket'].search([])]
        new_combinations = []
        for slot in new_slots:
            for ticket in slot.event_id.event_ticket_ids:
                if not (slot.id, ticket.id) in existing_combinations:
                    new_combinations.append((slot.id, ticket.id))
        self.env["event.slot.ticket"].create([{
            "slot_id": slot_id,
            "ticket_id": ticket_id,
        } for (slot_id, ticket_id) in new_combinations])
        return new_slots
