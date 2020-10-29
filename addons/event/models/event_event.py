# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pytz

from odoo import _, api, fields, models
from odoo.addons.base.models.res_partner import _tz_get
from odoo.tools import format_datetime
from odoo.exceptions import ValidationError
from odoo.tools.translate import html_translate

_logger = logging.getLogger(__name__)

try:
    import vobject
except ImportError:
    _logger.warning("`vobject` Python module not found, iCal file generation disabled. Consider installing this module if you want to generate iCal files")
    vobject = None


class EventType(models.Model):
    _name = 'event.type'
    _description = 'Event Template'
    _order = 'sequence, id'

    name = fields.Char('Event Template', required=True, translate=True)
    sequence = fields.Integer()
    # tickets
    use_ticket = fields.Boolean('Ticketing')
    event_type_ticket_ids = fields.One2many(
        'event.type.ticket', 'event_type_id',
        string='Tickets', compute='_compute_event_type_ticket_ids',
        readonly=False, store=True)
    tag_ids = fields.Many2many('event.tag', string="Tags")
    # registration
    has_seats_limitation = fields.Boolean('Limited Seats')
    seats_max = fields.Integer(
        'Maximum Registrations', compute='_compute_default_registration',
        readonly=False, store=True,
        help="It will select this default maximum value when you choose this event")
    auto_confirm = fields.Boolean(
        'Automatically Confirm Registrations', default=True,
        help="Events and registrations will automatically be confirmed "
             "upon creation, easing the flow for simple events.")
    # location
    use_timezone = fields.Boolean('Use Default Timezone')
    default_timezone = fields.Selection(
        _tz_get, string='Timezone', default=lambda self: self.env.user.tz or 'UTC')
    # communication
    use_mail_schedule = fields.Boolean(
        'Automatically Send Emails', default=True)
    event_type_mail_ids = fields.One2many(
        'event.type.mail', 'event_type_id',
        string='Mail Schedule', compute='_compute_event_type_mail_ids',
        readonly=False, store=True)

    @api.depends('use_mail_schedule')
    def _compute_event_type_mail_ids(self):
        for template in self:
            if not template.use_mail_schedule:
                template.event_type_mail_ids = [(5, 0)]
            elif not template.event_type_mail_ids:
                template.event_type_mail_ids = [(0, 0, {
                    'notification_type': 'mail',
                    'interval_unit': 'now',
                    'interval_type': 'after_sub',
                    'template_id': self.env.ref('event.event_subscription').id,
                }), (0, 0, {
                    'notification_type': 'mail',
                    'interval_nbr': 10,
                    'interval_unit': 'days',
                    'interval_type': 'before_event',
                    'template_id': self.env.ref('event.event_reminder').id,
                })]

    @api.depends('use_ticket')
    def _compute_event_type_ticket_ids(self):
        for template in self:
            if not template.use_ticket:
                template.event_type_ticket_ids = [(5, 0)]
            elif not template.event_type_ticket_ids:
                template.event_type_ticket_ids = [(0, 0, {
                    'name': _('Registration'),
                })]

    @api.depends('has_seats_limitation')
    def _compute_default_registration(self):
        for template in self:
            if not template.has_seats_limitation:
                template.seats_max = 0


class EventEvent(models.Model):
    """Event"""
    _name = 'event.event'
    _description = 'Event'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_begin'

    def _get_default_stage_id(self):
        event_stages = self.env['event.stage'].search([])
        return event_stages[0] if event_stages else False

    def _default_description(self):
        return self.env['ir.ui.view']._render_template('event.event_default_descripton')

    name = fields.Char(string='Event', translate=True, required=True)
    note = fields.Text(string='Note')
    description = fields.Html(string='Description', translate=html_translate, sanitize_attributes=False, sanitize_form=False, default=_default_description)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one(
        'res.users', string='Responsible', tracking=True,
        default=lambda self: self.env.user)
    company_id = fields.Many2one(
        'res.company', string='Company', change_default=True,
        default=lambda self: self.env.company,
        required=False)
    organizer_id = fields.Many2one(
        'res.partner', string='Organizer', tracking=True,
        default=lambda self: self.env.company.partner_id,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    event_type_id = fields.Many2one('event.type', string='Template', ondelete='set null')
    event_mail_ids = fields.One2many(
        'event.mail', 'event_id', string='Mail Schedule', copy=True,
        compute='_compute_event_mail_ids', readonly=False, store=True)
    tag_ids = fields.Many2many(
        'event.tag', string="Tags", readonly=False,
        store=True, compute="_compute_from_event_type")
    # Kanban fields
    kanban_state = fields.Selection([('normal', 'In Progress'), ('done', 'Done'), ('blocked', 'Blocked')], default='normal')
    kanban_state_label = fields.Char(
        string='Kanban State Label', compute='_compute_kanban_state_label',
        store=True, tracking=True)
    stage_id = fields.Many2one(
        'event.stage', ondelete='restrict', default=_get_default_stage_id,
        group_expand='_read_group_stage_ids', tracking=True)
    legend_blocked = fields.Char(related='stage_id.legend_blocked', string='Kanban Blocked Explanation', readonly=True)
    legend_done = fields.Char(related='stage_id.legend_done', string='Kanban Valid Explanation', readonly=True)
    legend_normal = fields.Char(related='stage_id.legend_normal', string='Kanban Ongoing Explanation', readonly=True)
    # Seats and computation
    seats_max = fields.Integer(
        string='Maximum Attendees Number',
        compute='_compute_from_event_type', readonly=False, store=True,
        help="For each event you can define a maximum registration of seats(number of attendees), above this numbers the registrations are not accepted.")
    seats_limited = fields.Boolean('Maximum Attendees', required=True, compute='_compute_seats_limited',
                                   readonly=False, store=True)
    seats_reserved = fields.Integer(
        string='Reserved Seats',
        store=True, readonly=True, compute='_compute_seats')
    seats_available = fields.Integer(
        string='Available Seats',
        store=True, readonly=True, compute='_compute_seats')
    seats_unconfirmed = fields.Integer(
        string='Unconfirmed Seat Reservations',
        store=True, readonly=True, compute='_compute_seats')
    seats_used = fields.Integer(
        string='Number of Participants',
        store=True, readonly=True, compute='_compute_seats')
    seats_expected = fields.Integer(
        string='Number of Expected Attendees',
        compute_sudo=True, readonly=True, compute='_compute_seats_expected')
    # Registration fields
    auto_confirm = fields.Boolean(
        string='Autoconfirmation', compute='_compute_from_event_type', readonly=False, store=True,
        help='Autoconfirm Registrations. Registrations will automatically be confirmed upon creation.')
    registration_ids = fields.One2many('event.registration', 'event_id', string='Attendees')
    event_ticket_ids = fields.One2many(
        'event.event.ticket', 'event_id', string='Event Ticket', copy=True,
        compute='_compute_event_ticket_ids', readonly=False, store=True)
    event_registrations_open = fields.Boolean(
        'Registration open', compute='_compute_event_registrations_open', compute_sudo=True,
        help="Registrations are open if:\n"
        "- the event is not ended\n"
        "- there are seats available on event\n"
        "- the tickets are sellable (if ticketing is used)")
    event_registrations_sold_out = fields.Boolean(
        'Sold Out', compute='_compute_event_registrations_sold_out', compute_sudo=True,
        help='The event is sold out if no more seats are available on event. If ticketing is used and all tickets are sold out, the event will be sold out.')
    start_sale_date = fields.Date(
        'Start sale date', compute='_compute_start_sale_date',
        help='If ticketing is used, contains the earliest starting sale date of tickets.')
    # Date fields
    date_tz = fields.Selection(
        _tz_get, string='Timezone', required=True,
        compute='_compute_date_tz', readonly=False, store=True)
    date_begin = fields.Datetime(string='Start Date', required=True, tracking=True)
    date_end = fields.Datetime(string='End Date', required=True, tracking=True)
    date_begin_located = fields.Char(string='Start Date Located', compute='_compute_date_begin_tz')
    date_end_located = fields.Char(string='End Date Located', compute='_compute_date_end_tz')
    is_ongoing = fields.Boolean('Is Ongoing', compute='_compute_is_ongoing', search='_search_is_ongoing')
    is_one_day = fields.Boolean(compute='_compute_field_is_one_day')
    # Location and communication
    address_id = fields.Many2one(
        'res.partner', string='Venue', default=lambda self: self.env.company.partner_id.id,
        tracking=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    country_id = fields.Many2one(
        'res.country', 'Country', related='address_id.country_id', readonly=False, store=True)
    # badge fields
    badge_front = fields.Html(string='Badge Front')
    badge_back = fields.Html(string='Badge Back')
    badge_innerleft = fields.Html(string='Badge Inner Left')
    badge_innerright = fields.Html(string='Badge Inner Right')
    event_logo = fields.Html(string='Event Logo')

    @api.depends('stage_id', 'kanban_state')
    def _compute_kanban_state_label(self):
        for event in self:
            if event.kanban_state == 'normal':
                event.kanban_state_label = event.stage_id.legend_normal
            elif event.kanban_state == 'blocked':
                event.kanban_state_label = event.stage_id.legend_blocked
            else:
                event.kanban_state_label = event.stage_id.legend_done

    @api.depends('seats_max', 'registration_ids.state')
    def _compute_seats(self):
        """ Determine reserved, available, reserved but unconfirmed and used seats. """
        # initialize fields to 0
        for event in self:
            event.seats_unconfirmed = event.seats_reserved = event.seats_used = event.seats_available = 0
        # aggregate registrations by event and by state
        state_field = {
            'draft': 'seats_unconfirmed',
            'open': 'seats_reserved',
            'done': 'seats_used',
        }
        base_vals = dict((fname, 0) for fname in state_field.values())
        results = dict((event_id, dict(base_vals)) for event_id in self.ids)
        if self.ids:
            query = """ SELECT event_id, state, count(event_id)
                        FROM event_registration
                        WHERE event_id IN %s AND state IN ('draft', 'open', 'done')
                        GROUP BY event_id, state
                    """
            self.env['event.registration'].flush(['event_id', 'state'])
            self._cr.execute(query, (tuple(self.ids),))
            res = self._cr.fetchall()
            for event_id, state, num in res:
                results[event_id][state_field[state]] += num

        # compute seats_available
        for event in self:
            event.update(results.get(event._origin.id or event.id, base_vals))
            if event.seats_max > 0:
                event.seats_available = event.seats_max - (event.seats_reserved + event.seats_used)

    @api.depends('seats_unconfirmed', 'seats_reserved', 'seats_used')
    def _compute_seats_expected(self):
        for event in self:
            event.seats_expected = event.seats_unconfirmed + event.seats_reserved + event.seats_used

    @api.depends('date_tz', 'start_sale_date', 'date_end', 'seats_available', 'seats_limited', 'event_ticket_ids.sale_available')
    def _compute_event_registrations_open(self):
        """ Compute whether people may take registrations for this event

          * event.date_end -> if event is done, registrations are not open anymore;
          * event.start_sale_date -> lowest start date of tickets (if any; start_sale_date
            is False if no ticket are defined, see _compute_start_sale_date);
          * any ticket is available for sale (seats available) if any;
          * seats are unlimited or seats are available;
        """
        for event in self:
            event = event._set_tz_context()
            current_datetime = fields.Datetime.context_timestamp(event, fields.Datetime.now())
            date_end_tz = event.date_end.astimezone(pytz.timezone(event.date_tz or 'UTC')) if event.date_end else False
            event.event_registrations_open = (event.start_sale_date <= current_datetime.date() if event.start_sale_date else True) and \
                (date_end_tz >= current_datetime if date_end_tz else True) and \
                (not event.seats_limited or event.seats_available) and \
                (not event.event_ticket_ids or any(ticket.sale_available for ticket in event.event_ticket_ids))

    @api.depends('event_ticket_ids.start_sale_date')
    def _compute_start_sale_date(self):
        """ Compute the start sale date of an event. Currently lowest starting sale
        date of tickets if they are used, of False. """
        for event in self:
            start_dates = [ticket.start_sale_date for ticket in event.event_ticket_ids if not ticket.is_expired]
            event.start_sale_date = min(start_dates) if start_dates and all(start_dates) else False

    @api.depends('event_ticket_ids.sale_available')
    def _compute_event_registrations_sold_out(self):
        for event in self:
            if event.seats_limited and not event.seats_available:
                event.event_registrations_sold_out = True
            elif event.event_ticket_ids:
                event.event_registrations_sold_out = not any(
                    ticket.seats_available > 0 if ticket.seats_limited else True for ticket in event.event_ticket_ids
                )
            else:
                event.event_registrations_sold_out = False

    @api.depends('date_tz', 'date_begin')
    def _compute_date_begin_tz(self):
        for event in self:
            if event.date_begin:
                event.date_begin_located = format_datetime(
                    self.env, event.date_begin, tz=event.date_tz, dt_format='medium')
            else:
                event.date_begin_located = False

    @api.depends('date_tz', 'date_end')
    def _compute_date_end_tz(self):
        for event in self:
            if event.date_end:
                event.date_end_located = format_datetime(
                    self.env, event.date_end, tz=event.date_tz, dt_format='medium')
            else:
                event.date_end_located = False

    @api.depends('date_begin', 'date_end')
    def _compute_is_ongoing(self):
        now = fields.Datetime.now()
        for event in self:
            event.is_ongoing = event.date_begin <= now < event.date_end

    def _search_is_ongoing(self, operator, value):
        if operator not in ['=', '!=']:
            raise ValueError(_('This operator is not supported'))
        if not isinstance(value, bool):
            raise ValueError(_('Value should be True or False (not %s)'), value)
        now = fields.Datetime.now()
        if (operator == '=' and value) or (operator == '!=' and not value):
            domain = [('date_begin', '<=', now), ('date_end', '>', now)]
        else:
            domain = ['|', ('date_begin', '>', now), ('date_end', '<=', now)]
        event_ids = self.env['event.event']._search(domain)
        return [('id', 'in', event_ids)]

    @api.depends('date_begin', 'date_end', 'date_tz')
    def _compute_field_is_one_day(self):
        for event in self:
            # Need to localize because it could begin late and finish early in
            # another timezone
            event = event._set_tz_context()
            begin_tz = fields.Datetime.context_timestamp(event, event.date_begin)
            end_tz = fields.Datetime.context_timestamp(event, event.date_end)
            event.is_one_day = (begin_tz.date() == end_tz.date())

    @api.depends('event_type_id')
    def _compute_date_tz(self):
        for event in self:
            if event.event_type_id.use_timezone and event.event_type_id.default_timezone:
                event.date_tz = event.event_type_id.default_timezone
            if not event.date_tz:
                event.date_tz = self.env.user.tz or 'UTC'

    @api.depends('event_type_id')
    def _compute_seats_limited(self):
        """ Make it separate from ``_compute_from_event_type`` because otherwise
        a value given at create (see create override) would protect all other fields
        depending on event type id from being computed as compute method will be
        blacklisted during create (see ``registry.field_computed`` attribute used in create
        to compute protected field from re-computation) """
        for event in self:
            if event.event_type_id.seats_max:
                event.seats_limited = True
            if not event.seats_limited:
                event.seats_limited = False

    @api.depends('event_type_id')
    def _compute_from_event_type(self):
        """ Update event configuration from its event type. Depends are set only
        on event_type_id itself, not its sub fields. Indeed purpose is to emulate
        an onchange: if event type is changed, update event configuration. Changing
        event type content itself should not trigger this method.

        Updated by this method
          * seats_max -> triggers _compute_seats (all seats computation)
          * seats_limited
          * auto_confirm
          * tag_ids
        """
        for event in self:
            if not event.event_type_id:
                if not event.seats_max:
                    event.seats_max = 0
                continue

            event.seats_max = event.event_type_id.seats_max

            if event.event_type_id.has_seats_limitation != event.seats_limited:
                event.seats_limited = event.event_type_id.has_seats_limitation

            event.auto_confirm = event.event_type_id.auto_confirm
            if not event.tag_ids and event.event_type_id.tag_ids:
                event.tag_ids = event.event_type_id.tag_ids

    @api.depends('event_type_id')
    def _compute_event_mail_ids(self):
        """ Update event mails from its event type. Depends are set only on
        event_type_id itself to emulate an onchange. Changing event type content
        itself should not trigger this method.

        When synchronizing mails:

          * lines that are not sent and have no registrations linked are remove;
          * type lines are added;
        """
        for event in self:
            if not event.event_type_id and not event.event_mail_ids:
                event.event_mail_ids = False
                continue

            # lines to keep: those with already sent emails or registrations
            mails_toremove = event._origin.event_mail_ids.filtered(lambda mail: not mail.mail_sent and not(mail.mail_registration_ids))
            command = [(3, mail.id) for mail in mails_toremove]
            if event.event_type_id.use_mail_schedule:
                command += [
                    (0, 0, {
                        attribute_name: line[attribute_name] if not isinstance(line[attribute_name], models.BaseModel) else line[attribute_name].id
                        for attribute_name in self.env['event.type.mail']._get_event_mail_fields_whitelist()
                    }) for line in event.event_type_id.event_type_mail_ids
                ]
            if command:
                event.event_mail_ids = command

    @api.depends('event_type_id')
    def _compute_event_ticket_ids(self):
        """ Update event tickets from its event type. Depends are set only on
        event_type_id itself to emulate an onchange. Changing event type content
        itself should not trigger this method.

        When synchronizing tickets:

          * lines that have no registrations linked are remove;
          * type lines are added;

        Note that updating event_ticket_ids triggers _compute_start_sale_date
        (start_sale_date computation) so ensure result to avoid cache miss.
        """
        if self.ids or self._origin.ids:
            # lines to keep: those with already sent emails or registrations
            tickets_tokeep_ids = self.env['event.registration'].search(
                [('event_id', 'in', self.ids or self._origin.ids)]
            ).event_ticket_id.ids
        else:
            tickets_tokeep_ids = []
        for event in self:
            if not event.event_type_id and not event.event_ticket_ids:
                event.event_ticket_ids = False
                continue

            # lines to keep: those with existing registrations
            if tickets_tokeep_ids:
                tickets_toremove = event._origin.event_ticket_ids.filtered(lambda ticket: ticket.id not in tickets_tokeep_ids)
                command = [(3, ticket.id) for ticket in tickets_toremove]
            else:
                command = [(5, 0)]
            if event.event_type_id.use_ticket:
                command += [
                    (0, 0, {
                        attribute_name: line[attribute_name] if not isinstance(line[attribute_name], models.BaseModel) else line[attribute_name].id
                        for attribute_name in self.env['event.type.ticket']._get_event_ticket_fields_whitelist()
                    }) for line in event.event_type_id.event_type_ticket_ids
                ]
            event.event_ticket_ids = command

    @api.constrains('seats_max', 'seats_available', 'seats_limited')
    def _check_seats_limit(self):
        if any(event.seats_limited and event.seats_max and event.seats_available < 0 for event in self):
            raise ValidationError(_('No more available seats.'))

    @api.constrains('date_begin', 'date_end')
    def _check_closing_date(self):
        for event in self:
            if event.date_end < event.date_begin:
                raise ValidationError(_('The closing date cannot be earlier than the beginning date.'))

    @api.depends('name', 'date_begin', 'date_end')
    def name_get(self):
        result = []
        for event in self:
            date_begin = fields.Datetime.from_string(event.date_begin)
            date_end = fields.Datetime.from_string(event.date_end)
            dates = [fields.Date.to_string(fields.Datetime.context_timestamp(event, dt)) for dt in [date_begin, date_end] if dt]
            dates = sorted(set(dates))
            result.append((event.id, '%s (%s)' % (event.name, ' - '.join(dates))))
        return result

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return self.env['event.stage'].search([])

    @api.model
    def create(self, vals):
        # Temporary fix for ``seats_limited`` and ``date_tz`` required fields (see ``_compute_from_event_type``
        vals.update(self._sync_required_computed(vals))

        res = super(EventEvent, self).create(vals)
        if res.organizer_id:
            res.message_subscribe([res.organizer_id.id])
        res.flush()
        return res

    def write(self, vals):
        res = super(EventEvent, self).write(vals)
        if vals.get('organizer_id'):
            self.message_subscribe([vals['organizer_id']])
        return res

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {}, name=_("%s (copy)") % (self.name))
        return super(EventEvent, self).copy(default)

    def _sync_required_computed(self, values):
        # TODO: See if the change to seats_limited affects this ?
        """ Call compute fields in cache to find missing values for required fields
        (seats_limited and date_tz) in case they are not given in values """
        missing_fields = list(set(['seats_limited', 'date_tz']).difference(set(values.keys())))
        if missing_fields and values:
            cache_event = self.new(values)
            cache_event._compute_from_event_type()
            return dict((fname, cache_event[fname]) for fname in missing_fields)
        else:
            return {}

    def _set_tz_context(self):
        self.ensure_one()
        return self.with_context(tz=self.date_tz or 'UTC')

    def action_set_done(self):
        """
        Action which will move the events
        into the first next (by sequence) stage defined as "Ended"
        (if they are not already in an ended stage)
        """
        first_ended_stage = self.env['event.stage'].search([('pipe_end', '=', True)], order='sequence')
        if first_ended_stage:
            self.write({'stage_id': first_ended_stage[0].id})

    def mail_attendees(self, template_id, force_send=False, filter_func=lambda self: self.state != 'cancel'):
        for event in self:
            for attendee in event.registration_ids.filtered(filter_func):
                self.env['mail.template'].browse(template_id).send_mail(attendee.id, force_send=force_send)

    def _get_ics_file(self):
        """ Returns iCalendar file for the event invitation.
            :returns a dict of .ics file content for each event
        """
        result = {}
        if not vobject:
            return result

        for event in self:
            cal = vobject.iCalendar()
            cal_event = cal.add('vevent')

            cal_event.add('created').value = fields.Datetime.now().replace(tzinfo=pytz.timezone('UTC'))
            cal_event.add('dtstart').value = fields.Datetime.from_string(event.date_begin).replace(tzinfo=pytz.timezone('UTC'))
            cal_event.add('dtend').value = fields.Datetime.from_string(event.date_end).replace(tzinfo=pytz.timezone('UTC'))
            cal_event.add('summary').value = event.name
            if event.address_id:
                cal_event.add('location').value = event.sudo().address_id.contact_address

            result[event.id] = cal.serialize().encode('utf-8')
        return result

    @api.autovacuum
    def _gc_mark_events_done(self):
        """ move every ended events in the next 'ended stage' """
        ended_events = self.env['event.event'].search([
            ('date_end', '<', fields.Datetime.now()),
            ('stage_id.pipe_end', '=', False),
        ])
        if ended_events:
            ended_events.action_set_done()
