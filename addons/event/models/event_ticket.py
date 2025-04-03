# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.misc import formatLang


class EventEventTicket(models.Model):
    """ Ticket model allowing to have different kind of registrations for a given
    event. Ticket are based on ticket type as they share some common fields
    and behavior. Those models come from <= v13 Odoo event.event.ticket that
    modeled both concept: tickets for event templates, and tickets for events.

    Model used to represent:
    - No slot tickets
        Tickets not linked to any slots and created from the event form.
        Effective tickets when the event is not multi slots.
    - Slot tickets
        Slot - Ticket combinations, created in the event.event '_compute_event_ticket_ids'
        using the declared no slot tickets and the event slots.
        (cf 'slot_id' and 'parent_ticket_id' fields)
        Effective tickets when the event is multi slots.

        Delete ticket / slot without any linked registrations:
            => Deletes the ticket / slot and their related slot tickets
               (cf 'parent_ticket_id' and 'slot_id' ondelete cascade)
        Delete ticket with linked registrations
            => Raise Validation Error (cf _unlink_except_if_registrations)
        Delete slot with linked registrations
            => Archiving the slot and their related slot tickets so that users can't register
               to it anymore while still keeping the time slots linked for the existing registrations.
               Useful to ease slots management via the calendar view without raising ValidationError every time.
               (cf event.slot unlink)
    """
    _name = 'event.event.ticket'
    _inherit = ['event.type.ticket']
    _description = 'Event Ticket'
    _order = "event_id, slot_id, sequence, name, id"

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if 'name' in fields and (not res.get('name') or res['name'] == _('Registration')) and self.env.context.get('default_event_name'):
            res['name'] = _('Registration for %s', self.env.context['default_event_name'])
        return res

    # description
    active = fields.Boolean("Active", default=True)
    name = fields.Char(compute="_compute_name", store=True, readonly=False)
    event_type_id = fields.Many2one(ondelete='set null', required=False)
    event_id = fields.Many2one(
        'event.event', string="Event",
        ondelete='cascade', required=True, index=True)
    # Technical field: Useful to unlink tickets from the effective event tickets (event_ticket_ids)
    # without completely deleting the ticket record (no ondelete cascade) and without removing the event link.
    event_ticket_event_id = fields.Many2one('event.event', string="Effective Event")
    company_id = fields.Many2one('res.company', related='event_id.company_id')
    # sale
    start_sale_datetime = fields.Datetime(string="Registration Start")
    end_sale_datetime = fields.Datetime(string="Registration End")
    is_launched = fields.Boolean(string='Are sales launched', compute='_compute_is_launched')
    is_expired = fields.Boolean(string='Is Expired', compute='_compute_is_expired')
    sale_available = fields.Boolean(
        string='Is Available', compute='_compute_sale_available', compute_sudo=True,
        help='Whether it is possible to sell these tickets')
    registration_ids = fields.One2many('event.registration', 'event_ticket_id', string='Registrations')
    # slot tickets
    slot_id = fields.Many2one("event.slot", string="Slot", ondelete="cascade",
        help="""Ticket related slot.
        Has a value if the ticket is a slot ticket, else the ticket is a parent ticket.""")
    slot_ticket_ids = fields.One2many("event.event.ticket", "parent_ticket_id", string="Slot tickets")
    parent_ticket_id = fields.Many2one("event.event.ticket", string="Parent Ticket", ondelete="cascade")
    # seats
    seats_reserved = fields.Integer(string='Reserved Seats', compute='_compute_seats', store=False)
    seats_available = fields.Integer(string='Available Seats', compute='_compute_seats', store=False)
    seats_used = fields.Integer(string='Used Seats', compute='_compute_seats', store=False)
    seats_taken = fields.Integer(string="Taken Seats", compute="_compute_seats", store=False)
    is_sold_out = fields.Boolean(
        'Sold Out', compute='_compute_is_sold_out', help='Whether seats are not available for this ticket.')
    # reports
    color = fields.Char('Color', default="#875A7B")

    @api.depends('end_sale_datetime', 'event_id.date_tz')
    def _compute_is_expired(self):
        for ticket in self:
            ticket = ticket._set_tz_context()
            current_datetime = fields.Datetime.context_timestamp(ticket, fields.Datetime.now())
            if ticket.end_sale_datetime:
                end_sale_datetime = fields.Datetime.context_timestamp(ticket, ticket.end_sale_datetime)
                ticket.is_expired = end_sale_datetime < current_datetime
            else:
                ticket.is_expired = False

    @api.depends('start_sale_datetime', 'event_id.date_tz')
    def _compute_is_launched(self):
        now = fields.Datetime.now()
        for ticket in self:
            if not ticket.start_sale_datetime:
                ticket.is_launched = True
            else:
                ticket = ticket._set_tz_context()
                current_datetime = fields.Datetime.context_timestamp(ticket, now)
                start_sale_datetime = fields.Datetime.context_timestamp(ticket, ticket.start_sale_datetime)
                ticket.is_launched = start_sale_datetime <= current_datetime

    @api.depends('parent_ticket_id', 'slot_id', 'slot_id.name')
    def _compute_name(self):
        """ Computes the slot tickets names from their parent tickets.
        Do not add the 'parent_ticket_id.name' depends as it is triggering a recursion error
        (parent_ticket_id.name updates handled in the write method).
        """
        for ticket in self:
            if ticket.slot_id:
                ticket.name = _('%(parent_ticket_name)s - %(slot_name)s',
                                parent_ticket_name=ticket.parent_ticket_id.name,
                                slot_name=ticket.slot_id.name)

    @api.depends('is_expired', 'start_sale_datetime', 'event_id.date_tz', 'seats_available', 'seats_max')
    def _compute_sale_available(self):
        for ticket in self:
            ticket.sale_available = ticket.is_launched and not ticket.is_expired and not ticket.is_sold_out

    @api.depends('parent_ticket_id', 'slot_id', 'seats_max', 'event_id.is_multi_slots',
                 'registration_ids.state', 'registration_ids.active')
    def _compute_seats(self):
        """ Determine available, reserved, used and taken seats. """
        # initialize fields to 0 + compute seats availability
        for ticket in self:
            ticket.seats_reserved = ticket.seats_used = ticket.seats_available = 0
        # Only sql query on registrations for slot tickets and non multi slots tickets
        tickets_to_compute = self.filtered(lambda ticket:
            (ticket.slot_id and ticket.parent_ticket_id) or
            not ticket.event_id.is_multi_slots
        )
        # aggregate registrations by ticket and by state
        results = {}
        if tickets_to_compute.ids:
            state_field = {
                'open': 'seats_reserved',
                'done': 'seats_used',
            }
            query = """ SELECT event_ticket_id, state, count(event_id)
                        FROM event_registration
                        WHERE event_ticket_id IN %s AND state IN ('open', 'done') AND active = true
                        GROUP BY event_ticket_id, state
                    """
            self.env['event.registration'].flush_model(['event_id', 'event_ticket_id', 'state', 'active'])
            self.env.cr.execute(query, (tuple(tickets_to_compute.ids),))
            for event_ticket_id, state, num in self.env.cr.fetchall():
                results.setdefault(event_ticket_id, {})[state_field[state]] = num

        # Compute seats for slot tickets and non multi slots tickets
        for ticket in tickets_to_compute:
            ticket.update(results.get(ticket._origin.id or ticket.id, {}))
            slot_seats_max = ticket.event_id.seats_max if ticket.slot_id else 0
            if ticket.seats_max > 0 or slot_seats_max > 0:
                seats_max = slot_seats_max if ticket.seats_max == 0 else \
                            ticket.seats_max if slot_seats_max == 0 else \
                            min(slot_seats_max, ticket.seats_max)
                seats_available = seats_max - (ticket.seats_reserved + ticket.seats_used)
                ticket.seats_available = min(seats_available, ticket.slot_id.seats_available) \
                    if ticket.event_id.seats_max and ticket.slot_id else seats_available
            ticket.seats_taken = ticket.seats_reserved + ticket.seats_used

        # Compute seats for parent tickets
        # Done after the slot tickets computation so that their seats are up to date
        for ticket in self - tickets_to_compute:
            ticket.seats_available = sum(ticket.slot_ticket_ids.mapped("seats_available"))
            ticket.seats_reserved = sum(ticket.slot_ticket_ids.mapped("seats_reserved"))
            ticket.seats_used = sum(ticket.slot_ticket_ids.mapped("seats_used"))
            ticket.seats_taken = ticket.seats_reserved + ticket.seats_used

    @api.depends("parent_ticket_id", "parent_ticket_id.seats_max")
    def _compute_seats_max(self):
        for ticket in self:
            if ticket.parent_ticket_id:
                ticket.seats_max = ticket.parent_ticket_id.seats_max

    @api.depends('seats_limited', 'seats_available')
    def _compute_is_sold_out(self):
        for ticket in self:
            ticket.is_sold_out = ticket.seats_limited and not ticket.seats_available

    @api.constrains('start_sale_datetime', 'end_sale_datetime')
    def _constrains_dates_coherency(self):
        for ticket in self:
            if ticket.start_sale_datetime and ticket.end_sale_datetime and ticket.start_sale_datetime > ticket.end_sale_datetime:
                raise UserError(_('The stop date cannot be earlier than the start date. '
                                  'Please check ticket %(ticket_name)s', ticket_name=ticket.name))

    @api.constrains('parent_ticket_id', 'slot_id', 'slot_ticket_ids')
    def _check_parent_and_slot_tickets_relationship(self):
        for ticket in self:
            if not ticket.parent_ticket_id and ticket.slot_id:
                raise ValidationError(_('A parent ticket cannot be linked to a slot.'))
            if ticket.parent_ticket_id and not ticket.slot_id:
                raise ValidationError(_('A slot ticket must be linked to a slot.'))
            if ticket.parent_ticket_id and ticket.slot_ticket_ids:
                raise ValidationError(_('A slot ticket cannot have any child tickets.'))

    @api.constrains('event_id', 'registration_ids', 'seats_max', 'slot_ticket_ids')
    def _check_seats_availability(self, minimal_availability=0):
        sold_out_tickets = []
        for ticket in self:
            if ticket.seats_max and ticket.seats_available < minimal_availability:
                sold_out_tickets.append(_(
                    '- the ticket "%(ticket_name)s" (%(event_name)s): Missing %(nb_too_many)i seats.',
                    ticket_name=ticket.name,
                    event_name=ticket.event_id.name,
                    nb_too_many=minimal_availability - ticket.seats_available,
                ))
            for slot_ticket in ticket.slot_ticket_ids:
                if (slot_ticket.seats_max or slot_ticket.event_id.seats_max) and \
                    slot_ticket.seats_available < minimal_availability:
                    sold_out_tickets.append(_(
                        '- the ticket "%(slot_ticket_name)s" (%(event_name)s): Missing %(nb_too_many)i seats.',
                        slot_ticket_name=slot_ticket.with_context(name_with_slot_date=True).display_name,
                        event_name=slot_ticket.event_id.name,
                        nb_too_many=minimal_availability - slot_ticket.seats_available,
                    ))
        if sold_out_tickets:
            raise ValidationError(_('There are not enough seats available for:')
                                  + '\n%s\n' % '\n'.join(sold_out_tickets))

    @api.depends('seats_max', 'seats_available')
    @api.depends_context('name_with_seats_availability', 'name_with_slot_date')
    def _compute_display_name(self):
        """Adds ticket seats availability or ticket slot date (only if slot ticket) if requested by context."""
        for ticket in self:
            if not self.env.context.get('name_with_slot_date') and ticket.parent_ticket_id:
                ticket_name = ticket.parent_ticket_id.name
            else:
                ticket_name = ticket.name
            if not self.env.context.get('name_with_seats_availability'):
                ticket.display_name = ticket_name
                continue
            # Name with availability
            if not ticket.seats_max and not (ticket.slot_id and ticket.event_id.seats_max):
                name = ticket_name
            elif not ticket.seats_available:
                name = _('%(ticket_name)s (Sold out)', ticket_name=ticket_name)
            else:
                name = _(
                    '%(ticket_name)s (%(count)s seats remaining)',
                    ticket_name=ticket_name,
                    count=formatLang(self.env, ticket.seats_available, digits=0),
                )
            ticket.display_name = name

    @api.model
    def _get_common_fields_w_parent_ticket(self):
        return ['color', 'event_type_id', 'start_sale_datetime', 'end_sale_datetime', 'seats_max']

    def _get_ticket_multiline_description(self):
        """ Compute a multiline description of this ticket. It is used when ticket
        description are necessary without having to encode it manually, like sales
        information. """
        return '%s\n%s' % (self.with_context(name_with_slot_date=True).display_name, self.event_id.display_name)

    def _set_tz_context(self):
        self.ensure_one()
        return self.with_context(tz=self.event_id.date_tz or 'UTC')

    @api.model_create_multi
    def create(self, vals_list):
        tickets = super().create(vals_list)
        tickets._compute_name()  # Override default name for slot tickets
        return tickets

    def write(self, vals):
        res = super().write(vals)

        parent_tickets = self.filtered(lambda ticket: not ticket.slot_id)
        if parent_tickets:
            common_parent_updated_vals = {
                field: vals[field]
                for field in vals
                if field in self._get_common_fields_w_parent_ticket()
            }
            if common_parent_updated_vals:
                # If a common field between the parent ticket and its slot tickets
                # is changed on the parent, updating all its slot tickets fields as well.
                parent_tickets.slot_ticket_ids.write(common_parent_updated_vals)
            if 'name' in vals:
                # If the name of the parent ticket is changed, updating its slot tickets names as well.
                # Called in the write method because these 2 other options are triggering a Recursion Error:
                # - adding the 'parent_ticket_id.name' depends on the '_compute_name'
                # - adding the recursive=True attribute on the name field
                parent_tickets.slot_ticket_ids._compute_name()

        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_if_registrations(self):
        if self.registration_ids or (self.slot_ticket_ids and self.slot_ticket_ids.registration_ids):
            raise UserError(_(
                "The following tickets cannot be deleted while they have one or more registrations linked to them:\n- %s",
                '\n- '.join(self.mapped('name'))))
