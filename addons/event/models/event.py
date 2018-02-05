# -*- coding: utf-8 -*-

import pytz

from odoo import _, api, fields, models
from odoo.addons.mail.models.mail_template import format_tz
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.translate import html_translate

from dateutil.relativedelta import relativedelta


class EventType(models.Model):
    _name = 'event.type'
    _description = 'Event Category'

    @api.model
    def _get_default_event_type_mail_ids(self):
        return [(0, 0, {
            'interval_unit': 'now',
            'interval_type': 'after_sub',
            'template_id': self.env.ref('event.event_subscription')
        }), (0, 0, {
            'interval_nbr': 1,
            'interval_unit': 'days',
            'interval_type': 'before_event',
            'template_id': self.env.ref('event.event_reminder')
        }), (0, 0, {
            'interval_nbr': 10,
            'interval_unit': 'days',
            'interval_type': 'before_event',
            'template_id': self.env.ref('event.event_reminder')
        })]

    name = fields.Char('Event Category', required=True, translate=True)
    # registration
    has_seats_limitation = fields.Boolean(
        'Limited Seats', default=False)
    default_registration_min = fields.Integer(
        'Minimum Registrations', default=0,
        help="It will select this default minimum value when you choose this event")
    default_registration_max = fields.Integer(
        'Maximum Registrations', default=0,
        help="It will select this default maximum value when you choose this event")
    auto_confirm = fields.Boolean(
        'Automatically Confirm Registrations', default=True,
        help="Events and registrations will automatically be confirmed "
             "upon creation, easing the flow for simple events.")
    # location
    is_online = fields.Boolean(
        'Online Event', help='Online events like webinars do not require a specific location and are hosted online.')
    use_timezone = fields.Boolean('Use Default Timezone')
    default_timezone = fields.Selection(
        '_tz_get', string='Timezone',
        default=lambda self: self.env.user.tz)
    # communication
    use_hashtag = fields.Boolean('Use Default Hashtag')
    default_hashtag = fields.Char('Twitter Hashtag')
    use_mail_schedule = fields.Boolean(
        'Automatically Send Emails', default=True)
    event_type_mail_ids = fields.One2many(
        'event.type.mail', 'event_type_id', string='Mail Schedule',
        copy=False,
        default=_get_default_event_type_mail_ids)

    @api.onchange('has_seats_limitation')
    def _onchange_has_seats_limitation(self):
        if not self.has_seats_limitation:
            self.default_registration_min = 0
            self.default_registration_max = 0

    @api.model
    def _tz_get(self):
        return [(x, x) for x in pytz.all_timezones]


class EventEvent(models.Model):
    """Event"""
    _name = 'event.event'
    _description = 'Event'
    _inherit = ['mail.thread']
    _order = 'date_begin'

    name = fields.Char(
        string='Event Name', translate=True, required=True,
        readonly=False, states={'done': [('readonly', True)]})
    active = fields.Boolean(default=True)
    user_id = fields.Many2one(
        'res.users', string='Responsible',
        default=lambda self: self.env.user,
        track_visibility="onchange",
        readonly=False, states={'done': [('readonly', True)]})
    company_id = fields.Many2one(
        'res.company', string='Company', change_default=True,
        default=lambda self: self.env['res.company']._company_default_get('event.event'),
        required=False, readonly=False, states={'done': [('readonly', True)]})
    organizer_id = fields.Many2one(
        'res.partner', string='Organizer',
        track_visibility="onchange",
        default=lambda self: self.env.user.company_id.partner_id)
    event_type_id = fields.Many2one(
        'event.type', string='Category',
        readonly=False, states={'done': [('readonly', True)]},
        oldname='type')
    color = fields.Integer('Kanban Color Index')
    event_mail_ids = fields.One2many('event.mail', 'event_id', string='Mail Schedule', copy=True)

    # Seats and computation
    seats_max = fields.Integer(
        string='Maximum Attendees Number', oldname='register_max',
        readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        help="For each event you can define a maximum registration of seats(number of attendees), above this numbers the registrations are not accepted.")
    seats_availability = fields.Selection(
        [('limited', 'Limited'), ('unlimited', 'Unlimited')],
        'Maximum Attendees', required=True, default='unlimited')
    seats_min = fields.Integer(
        string='Minimum Attendees', oldname='register_min',
        help="For each event you can define a minimum reserved seats (number of attendees), if it does not reach the mentioned registrations the event can not be confirmed (keep 0 to ignore this rule)")
    seats_reserved = fields.Integer(
        oldname='register_current', string='Reserved Seats',
        store=True, readonly=True, compute='_compute_seats')
    seats_available = fields.Integer(
        oldname='register_avail', string='Available Seats',
        store=True, readonly=True, compute='_compute_seats')
    seats_unconfirmed = fields.Integer(
        oldname='register_prospect', string='Unconfirmed Seat Reservations',
        store=True, readonly=True, compute='_compute_seats')
    seats_used = fields.Integer(
        oldname='register_attended', string='Number of Participants',
        store=True, readonly=True, compute='_compute_seats')
    seats_expected = fields.Integer(
        string='Number of Expected Attendees',
        readonly=True, compute='_compute_seats')

    # Registration fields
    registration_ids = fields.One2many(
        'event.registration', 'event_id', string='Attendees',
        readonly=False, states={'done': [('readonly', True)]})
    # Date fields
    date_tz = fields.Selection('_tz_get', string='Timezone', required=True, default=lambda self: self.env.user.tz or 'UTC')
    date_begin = fields.Datetime(
        string='Start Date', required=True,
        track_visibility='onchange', states={'done': [('readonly', True)]})
    date_end = fields.Datetime(
        string='End Date', required=True,
        track_visibility='onchange', states={'done': [('readonly', True)]})
    date_begin_located = fields.Char(string='Start Date Located', compute='_compute_date_begin_tz')
    date_end_located = fields.Char(string='End Date Located', compute='_compute_date_end_tz')

    state = fields.Selection([
        ('draft', 'Unconfirmed'), ('cancel', 'Cancelled'),
        ('confirm', 'Confirmed'), ('done', 'Done')],
        string='Status', default='draft', readonly=True, required=True, copy=False,
        help="If event is created, the status is 'Draft'. If event is confirmed for the particular dates the status is set to 'Confirmed'. If the event is over, the status is set to 'Done'. If event is cancelled the status is set to 'Cancelled'.")
    auto_confirm = fields.Boolean(string='Autoconfirm Registrations')
    is_online = fields.Boolean('Online Event')
    address_id = fields.Many2one(
        'res.partner', string='Location',
        default=lambda self: self.env.user.company_id.partner_id,
        readonly=False, states={'done': [('readonly', True)]},
        track_visibility="onchange")
    country_id = fields.Many2one('res.country', 'Country',  related='address_id.country_id', store=True)
    twitter_hashtag = fields.Char('Twitter Hashtag')
    description = fields.Html(
        string='Description', oldname='note', translate=html_translate, sanitize_attributes=False,
        readonly=False, states={'done': [('readonly', True)]})
    # badge fields
    badge_front = fields.Html(string='Badge Front')
    badge_back = fields.Html(string='Badge Back')
    badge_innerleft = fields.Html(string='Badge Inner Left')
    badge_innerright = fields.Html(string='Badge Inner Right')
    event_logo = fields.Html(string='Event Logo')

    @api.multi
    @api.depends('seats_max', 'registration_ids.state')
    def _compute_seats(self):
        """ Determine reserved, available, reserved but unconfirmed and used seats. """
        # initialize fields to 0
        for event in self:
            event.seats_unconfirmed = event.seats_reserved = event.seats_used = event.seats_available = 0
        # aggregate registrations by event and by state
        if self.ids:
            state_field = {
                'draft': 'seats_unconfirmed',
                'open': 'seats_reserved',
                'done': 'seats_used',
            }
            query = """ SELECT event_id, state, count(event_id)
                        FROM event_registration
                        WHERE event_id IN %s AND state IN ('draft', 'open', 'done')
                        GROUP BY event_id, state
                    """
            self._cr.execute(query, (tuple(self.ids),))
            for event_id, state, num in self._cr.fetchall():
                event = self.browse(event_id)
                event[state_field[state]] += num
        # compute seats_available
        for event in self:
            if event.seats_max > 0:
                event.seats_available = event.seats_max - (event.seats_reserved + event.seats_used)
            event.seats_expected = event.seats_unconfirmed + event.seats_reserved + event.seats_used

    @api.model
    def _tz_get(self):
        return [(x, x) for x in pytz.all_timezones]

    @api.one
    @api.depends('date_tz', 'date_begin')
    def _compute_date_begin_tz(self):
        if self.date_begin:
            self.date_begin_located = format_tz(self.with_context(use_babel=True).env, self.date_begin, tz=self.date_tz)
        else:
            self.date_begin_located = False

    @api.one
    @api.depends('date_tz', 'date_end')
    def _compute_date_end_tz(self):
        if self.date_end:
            self.date_end_located = format_tz(self.with_context(use_babel=True).env, self.date_end, tz=self.date_tz)
        else:
            self.date_end_located = False

    @api.onchange('event_type_id')
    def _onchange_type(self):
        if self.event_type_id:
            self.seats_min = self.event_type_id.default_registration_min
            self.seats_max = self.event_type_id.default_registration_max
            if self.event_type_id.default_registration_max:
                self.seats_availability = 'limited'

            if self.event_type_id.auto_confirm:
                self.auto_confirm = self.event_type_id.auto_confirm

            if self.event_type_id.use_hashtag:
                self.twitter_hashtag = self.event_type_id.default_hashtag

            if self.event_type_id.use_timezone:
                self.date_tz = self.event_type_id.default_timezone

            self.is_online = self.event_type_id.is_online

            if self.event_type_id.event_type_mail_ids:
                self.event_mail_ids = [(5, 0, 0)] + [{
                    'template_id': line.template_id,
                    'interval_nbr': line.interval_nbr,
                    'interval_unit': line.interval_unit,
                    'interval_type': line.interval_type}
                    for line in self.event_type_id.event_type_mail_ids]

    @api.constrains('seats_min', 'seats_max', 'seats_availability')
    def _check_seats_min_max(self):
        if any(event.seats_availability == 'limited' and event.seats_min > event.seats_max for event in self):
            raise ValidationError(_('Maximum attendees number should be greater than minimum attendees number.'))

    @api.constrains('seats_max', 'seats_available')
    def _check_seats_limit(self):
        if any(event.seats_availability == 'limited' and event.seats_max and event.seats_available < 0 for event in self):
            raise ValidationError(_('No more available seats.'))

    @api.one
    @api.constrains('date_begin', 'date_end')
    def _check_closing_date(self):
        if self.date_end < self.date_begin:
            raise ValidationError(_('Closing Date cannot be set before Beginning Date.'))

    @api.multi
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
    def create(self, vals):
        res = super(EventEvent, self).create(vals)
        if res.organizer_id:
            res.message_subscribe([res.organizer_id.id])
        if res.auto_confirm:
            res.button_confirm()
        return res

    @api.multi
    def write(self, vals):
        res = super(EventEvent, self).write(vals)
        if vals.get('organizer_id'):
            self.message_subscribe([vals['organizer_id']])
        return res

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {}, name=_("%s (copy)") % (self.name))
        return super(EventEvent, self).copy(default)

    @api.one
    def button_draft(self):
        self.state = 'draft'

    @api.multi
    def button_cancel(self):
        if any('done' in event.mapped('registration_ids.state') for event in self):
            raise UserError(_("There are already attendees who attended this event. Please reset it to draft if you want to cancel this event."))
        self.registration_ids.write({'state': 'cancel'})
        self.state = 'cancel'

    @api.one
    def button_done(self):
        self.state = 'done'

    @api.one
    def button_confirm(self):
        self.state = 'confirm'

    @api.one
    def mail_attendees(self, template_id, force_send=False, filter_func=lambda self: True):
        for attendee in self.registration_ids.filtered(filter_func):
            self.env['mail.template'].browse(template_id).send_mail(attendee.id, force_send=force_send)

    @api.multi
    def _is_event_registrable(self):
        return True


class EventRegistration(models.Model):
    _name = 'event.registration'
    _description = 'Attendee'
    _inherit = ['mail.thread']
    _order = 'name, create_date desc'

    origin = fields.Char(
        string='Source Document', readonly=True,
        help="Reference of the document that created the registration, for example a sales order")
    event_id = fields.Many2one(
        'event.event', string='Event', required=True,
        readonly=True, states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one(
        'res.partner', string='Contact',
        states={'done': [('readonly', True)]})
    date_open = fields.Datetime(string='Registration Date', readonly=True, default=lambda self: fields.datetime.now())  # weird crash is directly now
    date_closed = fields.Datetime(string='Attended Date', readonly=True)
    event_begin_date = fields.Datetime(string="Event Start Date", related='event_id.date_begin', readonly=True)
    event_end_date = fields.Datetime(string="Event End Date", related='event_id.date_end', readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Company', related='event_id.company_id',
        store=True, readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Unconfirmed'), ('cancel', 'Cancelled'),
        ('open', 'Confirmed'), ('done', 'Attended')],
        string='Status', default='draft', readonly=True, copy=False, track_visibility='onchange')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    name = fields.Char(string='Attendee Name', index=True)

    @api.one
    @api.constrains('event_id', 'state')
    def _check_seats_limit(self):
        if self.event_id.seats_availability == 'limited' and self.event_id.seats_max and self.event_id.seats_available < (1 if self.state == 'draft' else 0):
            raise ValidationError(_('No more seats available for this event.'))

    @api.multi
    def _check_auto_confirmation(self):
        if self._context.get('registration_force_draft'):
            return False
        if any(registration.event_id.state != 'confirm' or
               not registration.event_id.auto_confirm or
               (not registration.event_id.seats_available and registration.event_id.seats_availability == 'limited') for registration in self):
            return False
        return True

    @api.model
    def create(self, vals):
        registration = super(EventRegistration, self).create(vals)
        if registration._check_auto_confirmation():
            registration.sudo().confirm_registration()
        return registration

    @api.model
    def _prepare_attendee_values(self, registration):
        """ Method preparing the values to create new attendees based on a
        sales order line. It takes some registration data (dict-based) that are
        optional values coming from an external input like a web page. This method
        is meant to be inherited in various addons that sell events. """
        partner_id = registration.pop('partner_id', self.env.user.partner_id)
        event_id = registration.pop('event_id', False)
        data = {
            'name': registration.get('name', partner_id.name),
            'phone': registration.get('phone', partner_id.phone),
            'email': registration.get('email', partner_id.email),
            'partner_id': partner_id.id,
            'event_id': event_id and event_id.id or False,
        }
        data.update({key: value for key, value in registration.items() if key in self._fields})
        return data

    @api.one
    def do_draft(self):
        self.state = 'draft'

    @api.one
    def confirm_registration(self):
        self.state = 'open'

        # auto-trigger after_sub (on subscribe) mail schedulers, if needed
        onsubscribe_schedulers = self.event_id.event_mail_ids.filtered(
            lambda s: s.interval_type == 'after_sub')
        onsubscribe_schedulers.execute()

    @api.one
    def button_reg_close(self):
        """ Close Registration """
        today = fields.Datetime.now()
        if self.event_id.date_begin <= today and self.event_id.state == 'confirm':
            self.write({'state': 'done', 'date_closed': today})
        elif self.event_id.state == 'draft':
            raise UserError(_("You must wait the event confirmation before doing this action."))
        else:
            raise UserError(_("You must wait the event starting day before doing this action."))

    @api.one
    def button_reg_cancel(self):
        self.state = 'cancel'

    @api.onchange('partner_id')
    def _onchange_partner(self):
        if self.partner_id:
            contact_id = self.partner_id.address_get().get('contact', False)
            if contact_id:
                contact = self.env['res.partner'].browse(contact_id)
                self.name = contact.name or self.name
                self.email = contact.email or self.email
                self.phone = contact.phone or self.phone

    @api.multi
    def message_get_suggested_recipients(self):
        recipients = super(EventRegistration, self).message_get_suggested_recipients()
        try:
            for attendee in self:
                if attendee.partner_id:
                    attendee._message_add_suggested_recipient(recipients, partner=attendee.partner_id, reason=_('Customer'))
                elif attendee.email:
                    attendee._message_add_suggested_recipient(recipients, email=attendee.email, reason=_('Customer Email'))
        except AccessError:     # no read access rights -> ignore suggested recipients
            pass
        return recipients

    def _message_post_after_hook(self, message):
        if self.email and not self.partner_id:
            # we consider that posting a message with a specified recipient (not a follower, a specific one)
            # on a document without customer means that it was created through the chatter using
            # suggested recipients. This heuristic allows to avoid ugly hacks in JS.
            new_partner = message.partner_ids.filtered(lambda partner: partner.email == self.email)
            if new_partner:
                self.search([
                    ('partner_id', '=', False),
                    ('email', '=', new_partner.email),
                    ('state', 'not in', ['cancel']),
                ]).write({'partner_id': new_partner.id})
        return super(EventRegistration, self)._message_post_after_hook(message)

    @api.multi
    def action_send_badge_email(self):
        """ Open a window to compose an email, with the template - 'event_badge'
            message loaded by default
        """
        self.ensure_one()
        template = self.env.ref('event.event_registration_mail_template_badge')
        compose_form = self.env.ref('mail.email_compose_message_wizard_form')
        ctx = dict(
            default_model='event.registration',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode='comment',
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def get_date_range_str(self):
        self.ensure_one()
        today = fields.Datetime.from_string(fields.Datetime.now())
        event_date = fields.Datetime.from_string(self.event_begin_date)
        diff = (event_date.date() - today.date())
        if diff.days <= 0:
            return _('today')
        elif diff.days == 1:
            return _('tomorrow')
        elif (diff.days < 7):
            return _('in %d days') % (diff.days, )
        elif (diff.days < 14):
            return _('next week')
        elif event_date.month == (today + relativedelta(months=+1)).month:
            return _('next month')
        else:
            return _('on ') + format_tz(self.with_context({'use_babel': True}).env, self.event_begin_date, tz=self.event_id.date_tz or 'UTC')

    @api.multi
    def summary(self):
        self.ensure_one()
        return {'information': []}
