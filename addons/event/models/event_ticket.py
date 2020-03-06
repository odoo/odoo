# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from collections import Counter


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
    seats_availability = fields.Selection([
        ('limited', 'Limited'), ('unlimited', 'Unlimited')], string='Seats Limit',
        readonly=True, store=True, compute='_compute_seats_availability')
    seats_max = fields.Integer(
        string='Maximum Seats',
        help="Define the number of available tickets. If you have too many registrations you will "
             "not be able to sell tickets anymore. Set 0 to ignore this rule set as unlimited.")

    @api.depends('seats_max')
    def _compute_seats_availability(self):
        for ticket in self:
            ticket.seats_availability = 'limited' if ticket.seats_max else 'unlimited'

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
            res['name'] = _('Registration for %s') % self.env.context['default_event_name']
        return res

    # description
    event_type_id = fields.Many2one(ondelete='set null', required=False)
    event_id = fields.Many2one(
        'event.event', string="Event",
        ondelete='cascade', required=True)
    company_id = fields.Many2one('res.company', related='event_id.company_id')
    # sale
    start_sale_date = fields.Datetime(string="Registration Start")
    end_sale_date = fields.Datetime(string="Registration End")
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
            if ticket.end_sale_date:
                current_date = fields.Datetime.now()
                ticket.is_expired = ticket.end_sale_date < current_date
            else:
                ticket.is_expired = False

    @api.depends('start_sale_date', 'end_sale_date', 'event_id.date_tz')
    def _compute_sale_available(self):
        for ticket in self:
            current_date = fields.Datetime.now()
            if (ticket.start_sale_date and ticket.start_sale_date > current_date) or \
                    ticket.end_sale_date and ticket.end_sale_date < current_date:
                ticket.sale_available = False
            else:
                ticket.sale_available = True

    @api.depends('seats_max', 'registration_ids.state')
    def _compute_seats(self):
        """ Determine reserved, available, reserved but unconfirmed and used seats. """
        for ticket in self:
                ticket.seats_unconfirmed = ticket.seats_used = ticket.seats_reserved = ticket.seats_expected = 0
                ticket.seats_available = ticket.seats_max
        if self.ids:
            registration_data = self.env['event.registration'].read_group(
                [('event_ticket_id', 'in', self.ids), ('state', 'in', ['draft', 'open', 'done'])],
                ['event_ticket_id', 'states:array_agg(state)'],
                ['event_ticket_id']
            )

            processed_data = {registration['event_ticket_id'][0]: {'states': registration['states']} for registration in registration_data}

            state_field = {
                'draft': 'seats_unconfirmed',
                'open': 'seats_reserved',
                'done': 'seats_used',
            }

            for ticket in self:
                if processed_data.get(ticket.id):
                    states = Counter(processed_data[ticket.id]['states'])
                    for state, count in states.items():
                        ticket[state_field[state]] = count
                        if state in ['open', 'done']:
                            ticket.seats_available -= count if ticket.seats_max > 0 else 0

    @api.constrains('seats_available', 'seats_max')
    def _constrains_seats_available(self):
        if any(record.seats_max and record.seats_available < 0 for record in self):
            raise ValidationError(_('No more available seats for this ticket.'))

    def _get_ticket_multiline_description(self):
        """ Compute a multiline description of this ticket. It is used when ticket
        description are necessary without having to encode it manually, like sales
        information. """
        return '%s\n%s' % (self.display_name, self.event_id.display_name)

    def _get_ticket_tz(self):
        return self.event_id.date_tz or self.env.user.tz
