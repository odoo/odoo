# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang


class EventEventTicket(models.Model):
    """ Ticket model allowing to have different kind of registrations for a given
    event. Ticket are based on ticket type as they share some common fields
    and behavior. Those models come from <= v13 Odoo event.event.ticket that
    modeled both concept: tickets for event templates, and tickets for events. """
    _name = 'event.event.ticket'
    _inherit = ['event.type.ticket']
    _description = 'Event Ticket'
    _order = "event_id, sequence, name, id"

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if 'name' in fields and (not res.get('name') or res['name'] == _('Registration')) and self.env.context.get('default_event_name'):
            res['name'] = _('Registration for %s', self.env.context['default_event_name'])
        return res

    # description
    event_type_id = fields.Many2one(ondelete='set null', required=False)
    event_id = fields.Many2one(
        'event.event', string="Event",
        ondelete='cascade', required=True, index=True)
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
    # seats
    seats_reserved = fields.Integer(string='Reserved Seats', compute='_compute_seats', store=False)
    seats_available = fields.Integer(string='Available Seats', compute='_compute_seats', store=False)
    seats_used = fields.Integer(string='Used Seats', compute='_compute_seats', store=False)
    seats_taken = fields.Integer(string="Taken Seats", compute="_compute_seats", store=False)
    limit_max_per_order = fields.Integer(string='Limit per Order', default=0,
        help="Maximum of this product per order.\nSet to 0 to ignore this rule")
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

    @api.depends('is_expired', 'start_sale_datetime', 'event_id.date_tz', 'seats_available', 'seats_max')
    def _compute_sale_available(self):
        for ticket in self:
            ticket.sale_available = ticket.is_launched and not ticket.is_expired and not ticket.is_sold_out

    @api.depends('seats_max', 'registration_ids.state', 'registration_ids.active')
    def _compute_seats(self):
        """ Determine available, reserved, used and taken seats. """
        # initialize fields to 0 + compute seats availability
        for ticket in self:
            ticket.seats_reserved = ticket.seats_used = ticket.seats_available = 0
        # aggregate registrations by ticket and by state
        results = {}
        if self.ids:
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
            self.env.cr.execute(query, (tuple(self.ids),))
            for event_ticket_id, state, num in self.env.cr.fetchall():
                results.setdefault(event_ticket_id, {})[state_field[state]] = num

        # compute seats_available
        for ticket in self:
            ticket.update(results.get(ticket._origin.id or ticket.id, {}))
            if ticket.seats_max > 0:
                ticket.seats_available = ticket.seats_max - (ticket.seats_reserved + ticket.seats_used)
            ticket.seats_taken = ticket.seats_reserved + ticket.seats_used

    @api.depends('seats_limited', 'seats_available', 'event_id.event_registrations_sold_out')
    def _compute_is_sold_out(self):
        for ticket in self:
            ticket.is_sold_out = (
                (ticket.seats_limited and not ticket.seats_available)
                or ticket.event_id.event_registrations_sold_out
            )

    @api.constrains('start_sale_datetime', 'end_sale_datetime')
    def _constrains_dates_coherency(self):
        for ticket in self:
            if ticket.start_sale_datetime and ticket.end_sale_datetime and ticket.start_sale_datetime > ticket.end_sale_datetime:
                raise UserError(_('The stop date cannot be earlier than the start date. '
                                  'Please check ticket %(ticket_name)s', ticket_name=ticket.name))

    @api.constrains('limit_max_per_order', 'seats_max')
    def _constrains_limit_max_per_order(self):
        for ticket in self:
            if ticket.seats_max and ticket.limit_max_per_order > ticket.seats_max:
                raise UserError(_('The limit per order cannot be greater than the maximum seats number. '
                                  'Please check ticket %(ticket_name)s', ticket_name=ticket.name))
            if ticket.limit_max_per_order > ticket.event_id.EVENT_MAX_TICKETS:
                raise UserError(_('The limit per order cannot be greater than %(limit_orderable)s. '
                                  'Please check ticket %(ticket_name)s', limit_orderable=ticket.event_id.EVENT_MAX_TICKETS, ticket_name=ticket.name))
            if ticket.limit_max_per_order < 0:
                raise UserError(_('The limit per order must be positive. '
                                  'Please check ticket %(ticket_name)s', ticket_name=ticket.name))

    @api.depends('seats_max', 'seats_available')
    @api.depends_context('name_with_seats_availability')
    def _compute_display_name(self):
        """Adds ticket seats availability if requested by context.
        Always display the name without availabilities if the event is multi slots
        because the availability displayed won't be relative to the possible slot combinations
        but only relative to the event and this will confuse the user.
        """
        if not self.env.context.get('name_with_seats_availability'):
            return super()._compute_display_name()
        for ticket in self:
            if not ticket.seats_max or ticket.event_id.is_multi_slots:
                name = ticket.name
            elif not ticket.seats_available:
                name = _('%(ticket_name)s (Sold out)', ticket_name=ticket.name)
            else:
                name = _(
                    '%(ticket_name)s (%(count)s seats remaining)',
                    ticket_name=ticket.name,
                    count=formatLang(self.env, ticket.seats_available, digits=0),
                )
            ticket.display_name = name

    def _get_current_limit_per_order(self, event_slot=False, event=False):
        """ Compute the maximum possible number of tickets for an order, taking
        into account the given event_slot if applicable.
        If no ticket is created (alone event), event_id argument is used. Then
        return the dictionary with False as key. """
        event_slot.ensure_one() if event_slot else None
        if self:
            slots_seats_available = self.event_id._get_seats_availability([[event_slot, ticket] for ticket in self])
        else:
            return {False: event_slot.seats_available if event_slot else (event.seats_available if event.seats_limited else event.EVENT_MAX_TICKETS)}
        availabilities = {}
        for ticket, seats_available in zip(self, slots_seats_available):
            if not seats_available:  # "No limit"
                seats_available = ticket.limit_max_per_order or ticket.event_id.EVENT_MAX_TICKETS
            else:
                seats_available = min(ticket.limit_max_per_order or seats_available, seats_available)
            availabilities[ticket.id] = seats_available
        return availabilities

    def _get_ticket_multiline_description(self):
        """ Compute a multiline description of this ticket. It is used when ticket
        description are necessary without having to encode it manually, like sales
        information. """
        return '%s\n%s' % (self.display_name, self.event_id.display_name)

    def _set_tz_context(self):
        self.ensure_one()
        return self.with_context(tz=self.event_id.date_tz or 'UTC')

    @api.ondelete(at_uninstall=False)
    def _unlink_except_if_registrations(self):
        if self.registration_ids:
            raise UserError(_(
                "The following tickets cannot be deleted while they have one or more registrations linked to them:\n- %s",
                '\n- '.join(self.mapped('name'))))
