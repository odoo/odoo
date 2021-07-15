# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class EventTemplateTicket(models.Model):
    _name = 'event.type.ticket'
    _description = 'Event Template Ticket'

    # description
    name = fields.Char(
        string='Name', default=lambda self: _('Registration'),
        required=True, translate=True)
    description = fields.Text(
        'Description', translate=True,
        help="A description of the ticket that you want to communicate to your customers.")
    event_type_id = fields.Many2one(
        'event.type', string='Event Category', ondelete='cascade', required=True)
    # seats
    seats_limited = fields.Boolean(string='Seats Limit', readonly=True, store=True,
                                   compute='_compute_seats_limited')
    seats_max = fields.Integer(
        string='Maximum Seats',
        help="Define the number of available tickets. If you have too many registrations you will "
             "not be able to sell tickets anymore. Set 0 to ignore this rule set as unlimited.")

    @api.depends('seats_max')
    def _compute_seats_limited(self):
        for ticket in self:
            ticket.seats_limited = ticket.seats_max

    @api.model
    def _get_event_ticket_fields_whitelist(self):
        """ Whitelist of fields that are copied from event_type_ticket_ids to event_ticket_ids when
        changing the event_type_id field of event.event """
        return ['name', 'description', 'seats_max']


class EventTicket(models.Model):
    """ Ticket model allowing to have differnt kind of registrations for a given
    event. Ticket are based on ticket type as they share some common fields
    and behavior. Those models come from <= v13 Odoo event.event.ticket that
    modeled both concept: tickets for event templates, and tickets for events. """
    _name = 'event.event.ticket'
    _inherit = 'event.type.ticket'
    _description = 'Event Ticket'

    @api.model
    def default_get(self, fields):
        res = super(EventTicket, self).default_get(fields)
        if 'name' in fields and (not res.get('name') or res['name'] == _('Registration')) and self.env.context.get('default_event_name'):
            res['name'] = _('Registration for %s', self.env.context['default_event_name'])
        return res

    # description
    event_type_id = fields.Many2one(ondelete='set null', required=False)
    event_id = fields.Many2one(
        'event.event', string="Event",
        ondelete='cascade', required=True)
    company_id = fields.Many2one('res.company', related='event_id.company_id')
    # sale
    start_sale_date = fields.Date(string="Registration Start")
    end_sale_date = fields.Date(string="Registration End")
    is_expired = fields.Boolean(string='Is Expired', compute='_compute_is_expired')
    sale_available = fields.Boolean(string='Is Available', compute='_compute_sale_available', compute_sudo=True)
    registration_ids = fields.One2many('event.registration', 'event_ticket_id', string='Registrations')
    # seats
    seats_reserved = fields.Integer(string='Reserved Seats', compute='_compute_seats', store=True)
    seats_available = fields.Integer(string='Available Seats', compute='_compute_seats', store=True)
    seats_unconfirmed = fields.Integer(string='Unconfirmed Seats', compute='_compute_seats', store=True)
    seats_used = fields.Integer(string='Used Seats', compute='_compute_seats', store=True)

    @api.depends('end_sale_date', 'event_id.date_tz')
    def _compute_is_expired(self):
        for ticket in self:
            ticket = ticket._set_tz_context()
            current_date = fields.Date.context_today(ticket)
            if ticket.end_sale_date:
                ticket.is_expired = ticket.end_sale_date < current_date
            else:
                ticket.is_expired = False

    @api.depends('is_expired', 'start_sale_date', 'event_id.date_tz', 'seats_available', 'seats_max')
    def _compute_sale_available(self):
        for ticket in self:
            if not ticket.is_launched() or ticket.is_expired or (ticket.seats_max and ticket.seats_available <= 0):
                ticket.sale_available = False
            else:
                ticket.sale_available = True

    @api.depends('seats_max', 'registration_ids.state')
    def _compute_seats(self):
        """ Determine reserved, available, reserved but unconfirmed and used seats. """
        # initialize fields to 0 + compute seats availability
        for ticket in self:
            ticket.seats_unconfirmed = ticket.seats_reserved = ticket.seats_used = ticket.seats_available = 0
        # aggregate registrations by ticket and by state
        if self.ids:
            state_field = {
                'draft': 'seats_unconfirmed',
                'open': 'seats_reserved',
                'done': 'seats_used',
            }
            query = """ SELECT event_ticket_id, state, count(event_id)
                        FROM event_registration
                        WHERE event_ticket_id IN %s AND state IN ('draft', 'open', 'done')
                        GROUP BY event_ticket_id, state
                    """
            self.env['event.registration'].flush(['event_id', 'event_ticket_id', 'state'])
            self.env.cr.execute(query, (tuple(self.ids),))
            for event_ticket_id, state, num in self.env.cr.fetchall():
                ticket = self.browse(event_ticket_id)
                ticket[state_field[state]] += num
        # compute seats_available
        for ticket in self:
            if ticket.seats_max > 0:
                ticket.seats_available = ticket.seats_max - (ticket.seats_reserved + ticket.seats_used)

    @api.constrains('start_sale_date', 'end_sale_date')
    def _constrains_dates_coherency(self):
        for ticket in self:
            if ticket.start_sale_date and ticket.end_sale_date and ticket.start_sale_date > ticket.end_sale_date:
                raise UserError(_('The stop date cannot be earlier than the start date.'))

    @api.constrains('seats_available', 'seats_max')
    def _constrains_seats_available(self):
        if any(record.seats_max and record.seats_available < 0 for record in self):
            raise ValidationError(_('No more available seats for this ticket.'))

    def _get_ticket_multiline_description(self):
        """ Compute a multiline description of this ticket. It is used when ticket
        description are necessary without having to encode it manually, like sales
        information. """
        return '%s\n%s' % (self.display_name, self.event_id.display_name)

    def _set_tz_context(self):
        self.ensure_one()
        return self.with_context(tz=self.event_id.date_tz or 'UTC')

    def is_launched(self):
        # TDE FIXME: in master, make a computed field, easier to use
        self.ensure_one()
        if self.start_sale_date:
            ticket = self._set_tz_context()
            current_date = fields.Date.context_today(ticket)
            return ticket.start_sale_date <= current_date
        else:
            return True
