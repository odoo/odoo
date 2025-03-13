from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import formatLang


class EventSlotTicket(models.Model):
    """ Used to keep track of the registrations per slot and per ticket for multi-slots events.
    I.e. if the seats_max for a specific ticket is 5, keeping track of the ticket registrations for each slot
    to ensure that it doesn't exceed 5. If the number of registrations of a ticket reaches 5 for a slot,
    the ticket will be considered sold out for that slot.
    """
    _name = "event.slot.ticket"
    _description = "Event Slot Ticket"

    name = fields.Char("Name", compute="_compute_name", store=True)
    event_id = fields.Many2one("event.event", string="Event", store=True, related="slot_id.event_id")
    slot_id = fields.Many2one("event.slot", string="Slot", required=True, ondelete="cascade")
    ticket_id = fields.Many2one("event.event.ticket", string="Ticket", required=True, ondelete="cascade")

    # Seats availabilities for this slot and this ticket
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

    _slot_ticket_combination_uniq = models.Constraint(
        'unique(slot_id, ticket_id)',
        'This slot-ticket combination already exists.',
    )

    @api.constrains('registration_ids', 'seats_available')
    def _check_seats_availability(self, minimal_availability=0):
        sold_out_slot_tickets = []
        for slot_ticket in self:
            if (slot_ticket.event_id.seats_max or slot_ticket.ticket_id.seats_max) and slot_ticket.seats_available < minimal_availability:
                sold_out_slot_tickets.append(_(
                    '- %(slot_ticket_name)s" (%(event_name)s): Missing %(nb_too_many)i seats.',
                    slot_ticket_name=slot_ticket.name,
                    event_name=slot_ticket.event_id.name,
                    nb_too_many=-slot_ticket.seats_available))
        if sold_out_slot_tickets:
            raise ValidationError(_('There are not enough seats available for:')
                                  + '\n%s\n' % '\n'.join(sold_out_slot_tickets))

    @api.depends("event_id", "event_id.seats_limited", "seats_available")
    def _compute_is_sold_out(self):
        for slot_ticket in self:
            slot_ticket.is_sold_out = slot_ticket.event_id.seats_limited and not slot_ticket.seats_available

    @api.depends("slot_id", "slot_id.name", "ticket_id", "ticket_id.name")
    def _compute_name(self):
        for slot_ticket in self:
            slot_ticket.name = '%s - "%s" ticket' % (slot_ticket.slot_id.name, slot_ticket.ticket_id.name)

    @api.depends("name")
    @api.depends_context('name_with_seats_availability')
    def _compute_display_name(self):
        for slot_ticket in self:
            if not self.env.context.get('name_with_seats_availability') or \
                (not slot_ticket.event_id.seats_max and not slot_ticket.ticket_id.seats_max):
                slot_ticket.display_name = slot_ticket.name
                continue
            if not slot_ticket.seats_available:
                slot_ticket.display_name = _('%(slot_name)s (Sold out)', slot_name=slot_ticket.name)
            else:
                slot_ticket.display_name = _(
                    '%(slot_name)s (%(count)s seats remaining)',
                    slot_name=slot_ticket.name,
                    count=formatLang(self.env, slot_ticket.seats_available, digits=0),
                )

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
