from odoo import api, fields, models
from odoo.tools.sql import drop_view_if_exists, SQL


class EventSlotTicket(models.Model):
    """ Used to keep track of the registrations per slot and per ticket for multi-slots events.
    I.e. if the seats_max for a specific ticket is 5, keeping track of the ticket registrations for each slot
    to ensure that it doesn't exceed 5. If the number of registrations reaches 5 for a specific slot,
    the ticket will be considered sold out for that slot.
    """
    _name = "event.slot.ticket"
    _description = "Event Slot Ticket"
    _auto = False

    event_id = fields.Many2one("event.event", string="Event", related="slot_id.event_id")
    slot_id = fields.Many2one("event.slot", string="Slot", required=True, ondelete="cascade")
    ticket_id = fields.Many2one("event.event.ticket", string="Ticket", required=True, ondelete="cascade")

    # Limitations for this slot and this ticket
    registration_ids = fields.One2many("event.registration", string="Attendees", compute="_compute_registration_ids", search="_search_registration_ids")
    seats_reserved = fields.Integer(string="Reserved Seats", compute="_compute_seats", store=False)
    seats_available = fields.Integer(string="Available Seats", compute="_compute_seats", store=False)
    seats_used = fields.Integer(string="Used Seats", compute="_compute_seats", store=False)
    seats_taken = fields.Integer(string="Taken Seats", compute="_compute_seats", store=False)
    is_sold_out = fields.Boolean(
        "Sold Out", compute="_compute_is_sold_out", help="Whether seats are not available for this slot and ticket.")
    sale_available = fields.Boolean(
        string='Is Ticket Available', compute='_compute_sale_available', compute_sudo=True,
        help='Whether it is possible to sell this ticket for this slot.')

    def init(self):
        """ Create a line for each event slot and ticket combinations. """
        query = """
              SELECT ROW_NUMBER() OVER () AS id, slot.id AS slot_id, ticket.id AS ticket_id
                FROM event_slot AS slot
          CROSS JOIN event_event_ticket AS ticket
               WHERE slot.event_id = ticket.event_id
        """
        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(SQL("""CREATE or REPLACE VIEW %s as (%s)""", SQL.identifier(self._table), SQL(query)))

    @api.depends("event_id", "event_id.seats_limited", "seats_available")
    def _compute_is_sold_out(self):
        for slot_ticket in self:
            slot_ticket.is_sold_out = slot_ticket.event_id.seats_limited and not slot_ticket.seats_available

    @api.depends("event_id", "event_id.registration_ids", "slot_id", "ticket_id")
    def _compute_registration_ids(self):
        for slot_ticket in self:
            slot_ticket.registration_ids = slot_ticket.event_id.registration_ids.filtered(
                lambda registration: registration.slot_id == slot_ticket.slot_id and registration.event_ticket_id == slot_ticket.ticket_id)

    @api.model
    def _search_registration_ids(self, operator, value):
        return [('event_id.registration_ids', operator, value)]

    @api.depends("is_sold_out", "seats_available", "ticket_id", "event_id.date_tz", "ticket_id.is_expired", "ticket_id.seats_max", "ticket_id.start_sale_datetime")
    def _compute_sale_available(self):
        for slot_ticket in self:
            slot_ticket.sale_available = slot_ticket.ticket_id.is_launched and not slot_ticket.ticket_id.is_expired and not slot_ticket.is_sold_out

    @api.depends("event_id", "event_id.seats_max", "slot_id", "ticket_id", "registration_ids.state", "registration_ids.active")
    def _compute_seats(self):
        """ Determine available, reserved, used and taken seats. """
        # initialize fields to 0
        for slot_ticket in self:
            slot_ticket.seats_reserved = slot_ticket.seats_used = slot_ticket.seats_available = 0
        # aggregate registrations by slot, by ticket and by state
        results = {}
        if self.ids:
            state_field = {
                'open': 'seats_reserved',
                'done': 'seats_used',
            }
            query = """ SELECT slot_id, event_ticket_id, state, count(event_id)
                        FROM event_registration
                        WHERE slot_id IN %s AND event_ticket_id IN %s AND state IN ('open', 'done') AND active = true
                        GROUP BY slot_id, event_ticket_id, state
                    """
            self.env['event.registration'].flush_model(['event_id', 'slot_id', 'event_ticket_id', 'state', 'active'])
            self.env.cr.execute(query, (tuple(self.mapped("slot_id").ids), tuple(self.mapped("ticket_id").ids)))
            for slot_id, event_ticket_id, state, num in self.env.cr.fetchall():
                results.setdefault(slot_id, {}).setdefault(event_ticket_id, {})[state_field[state]] = num

        # compute seats_available
        for slot_ticket in self:
            slot_ticket.update(
                results.get(slot_ticket.slot_id._origin.id or slot_ticket.slot_id.id, {}).get(slot_ticket.ticket_id._origin.id or slot_ticket.ticket_id.id, {})
            )
            event_seats_max = slot_ticket.event_id.seats_max
            ticket_seats_max = slot_ticket.ticket_id.seats_max
            if event_seats_max > 0 or ticket_seats_max > 0:
                seats_max = event_seats_max if ticket_seats_max == 0 else \
                            ticket_seats_max if event_seats_max == 0 else \
                            min(event_seats_max, ticket_seats_max)
                seats_available = seats_max - (slot_ticket.seats_reserved + slot_ticket.seats_used)
                slot_ticket.seats_available = min(seats_available, slot_ticket.slot_id.seats_available)
            slot_ticket.seats_taken = slot_ticket.seats_reserved + slot_ticket.seats_used
