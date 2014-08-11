# -*- coding: utf-8 -*-

import pytz

from openerp import _, api, fields, models
from openerp.exceptions import Warning


class event_type(models.Model):
    """ Event Type """
    _name = 'event.type'
    _description = 'Event Type'

    name = fields.Char('Event Type', required=True)
    default_reply_to = fields.Char('Reply To')
    default_registration_min = fields.Integer(
        'Default Minimum Registration', default=0,
        help="It will select this default minimum value when you choose this event")
    default_registration_max = fields.Integer(
        'Default Maximum Registration', default=0,
        help="It will select this default maximum value when you choose this event")


class event_event(models.Model):
    """Event"""
    _name = 'event.event'
    _description = 'Event'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'date_begin'

    name = fields.Char(
        string='Name', translate=True, required=True,
        readonly=False, states={'done': [('readonly', True)]})
    user_id = fields.Many2one(
        'res.users', string='Responsible',
        default=lambda self: self.env.user,
        readonly=False, states={'done': [('readonly', True)]})
    company_id = fields.Many2one(
        'res.company', string='Company', change_default=True,
        default=lambda self: self.env['res.company']._company_default_get('event.event'),
        required=False, readonly=False, states={'done': [('readonly', True)]})
    organizer_id = fields.Many2one(
        'res.partner', string='Organizer',
        default=lambda self: self.env.user.company_id.partner_id)
    type = fields.Many2one(
        'event.type', string='Category',
        readonly=False, states={'done': [('readonly', True)]})
    color = fields.Integer('Kanban Color Index')
    event_mail_ids = fields.One2many('event.mail', 'event_id', string='Mail Schedule', default=lambda self: self._default_event_mail_ids())

    @api.model
    def _default_event_mail_ids(self):
        return [(0, 0, {
            'interval_unit': 'now',
            'interval_type': 'after_sub',
            'template_id': self.env['ir.model.data'].xmlid_to_res_id('event.event_subscription')
        })]

    # Seats and computation
    seats_max = fields.Integer(
        string='Maximum Available Seats', oldname='register_max',
        readonly=True, states={'draft': [('readonly', False)]},
        help="You can for each event define a maximum registration level. If you have too much registrations you are not able to confirm your event. (put 0 to ignore this rule )")
    seats_availability = fields.Selection(
        [('limited', 'Limited'), ('unlimited', 'Unlimited')],
        'Available Seat', required=True, default='unlimited')
    seats_min = fields.Integer(
        string='Minimum Reserved Seats', oldname='register_min',
        readonly=True, states={'draft': [('readonly', False)]},
        help="You can for each event define a minimum registration level. If you do not enough registrations you are not able to confirm your event. (put 0 to ignore this rule )")
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
        oldname='register_attended', string='Number of Participations',
        store=True, readonly=True, compute='_compute_seats')

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

    # Registration fields
    registration_ids = fields.One2many(
        'event.registration', 'event_id', string='Attendees',
        readonly=False, states={'done': [('readonly', True)]})
    count_registrations = fields.Integer(string='Registrations', compute='_count_registrations')

    @api.one
    @api.depends('registration_ids')
    def _count_registrations(self):
        self.count_registrations = len(self.registration_ids)

    # Date fields
    date_tz = fields.Selection('_tz_get', string='Timezone', default=lambda self: self.env.user.tz)
    date_begin = fields.Datetime(
        string='Start Date', required=True,
        readonly=True, states={'draft': [('readonly', False)]})
    date_end = fields.Datetime(
        string='End Date', required=True,
        readonly=True, states={'draft': [('readonly', False)]})
    date_begin_located = fields.Datetime(string='Start Date Located', compute='_compute_date_begin_tz')
    date_end_located = fields.Datetime(string='End Date Located', compute='_compute_date_end_tz')

    @api.model
    def _tz_get(self):
        return [(x, x) for x in pytz.all_timezones]

    @api.one
    @api.depends('date_tz', 'date_begin')
    def _compute_date_begin_tz(self):
        if self.date_begin:
            self_in_tz = self.with_context(tz=(self.date_tz or 'UTC'))
            date_begin = fields.Datetime.from_string(self.date_begin)
            self.date_begin_located = fields.Datetime.to_string(fields.Datetime.context_timestamp(self_in_tz, date_begin))
        else:
            self.date_begin_located = False

    @api.one
    @api.depends('date_tz', 'date_end')
    def _compute_date_end_tz(self):
        if self.date_end:
            self_in_tz = self.with_context(tz=(self.date_tz or 'UTC'))
            date_end = fields.Datetime.from_string(self.date_end)
            self.date_end_located = fields.Datetime.to_string(fields.Datetime.context_timestamp(self_in_tz, date_end))
        else:
            self.date_end_located = False

    state = fields.Selection([
        ('draft', 'Unconfirmed'), ('cancel', 'Cancelled'),
        ('confirm', 'Confirmed'), ('done', 'Done')],
        string='Status', default='draft', readonly=True, required=True, copy=False,
        help="If event is created, the status is 'Draft'. If event is confirmed for the particular dates the status is set to 'Confirmed'. If the event is over, the status is set to 'Done'. If event is cancelled the status is set to 'Cancelled'.")
    auto_confirm = fields.Boolean(string='Auto Confirmation Activated', compute='_compute_auto_confirm')

    @api.one
    def _compute_auto_confirm(self):
        self.auto_confirm = self.env['ir.values'].get_default('marketing.config.settings', 'auto_confirmation')

    reply_to = fields.Char(
        'Reply-To Email', readonly=False, states={'done': [('readonly', True)]},
        help="The email address of the organizer is likely to be put here, with the effect to be in the 'Reply-To' of the mails sent automatically at event or registrations confirmation. You can also put the email address of your mail gateway if you use one.")
    address_id = fields.Many2one(
        'res.partner', string='Location', default=lambda self: self.env.user.company_id.partner_id,
        readonly=False, states={'done': [('readonly', True)]})
    country_id = fields.Many2one('res.country', 'Country',  related='address_id.country_id', store=True)
    description = fields.Html(
        string='Description', oldname='note', translate=True,
        readonly=False, states={'done': [('readonly', True)]})

    @api.multi
    @api.depends('name', 'date_begin', 'date_end')
    def name_get(self):
        result = []
        for event in self:
            dates = [dt.split(' ')[0] for dt in [event.date_begin, event.date_end] if dt]
            dates = sorted(set(dates))
            result.append((event.id, '%s (%s)' % (event.name, ' - '.join(dates))))
        return result

    @api.one
    @api.constrains('seats_max', 'seats_available')
    def _check_seats_limit(self):
        if self.seats_max and self.seats_available < 0:
            raise Warning(_('No more available seats.'))

    @api.one
    @api.constrains('date_begin', 'date_end')
    def _check_closing_date(self):
        if self.date_end < self.date_begin:
            raise Warning(_('Closing Date cannot be set before Beginning Date.'))

    @api.model
    def create(self, vals):
        res = super(event_event, self).create(vals)
        if res.auto_confirm:
            res.button_confirm()
        return res

    @api.one
    def button_draft(self):
        self.state = 'draft'

    @api.one
    def button_cancel(self):
        for event_reg in self.registration_ids:
            if event_reg.state == 'done':
                raise Warning(_("You have already set a registration for this event as 'Attended'. Please reset it to draft if you want to cancel this event."))
        self.registration_ids.write({'state': 'cancel'})
        self.state = 'cancel'

    @api.one
    def button_done(self):
        self.state = 'done'

    @api.one
    def button_confirm(self):
        self.state = 'confirm'

    @api.onchange('type')
    def _onchange_type(self):
        if self.type:
            self.seats_min = self.type.default_registration_min
            self.seats_max = self.type.default_registration_max
            self.reply_to = self.type.default_reply_to

    @api.multi
    def action_event_registration_report(self):
        res = self.env['ir.actions.act_window'].for_xml_id('event', 'action_report_event_registration')
        res['context'] = {
            "search_default_event_id": self.id,
            "group_by": ['create_date:day'],
        }
        return res

    @api.one
    def mail_attendees(self, template_id, force_send=False, filter_func=lambda self: True):
        for attendee in self.registration_ids.filtered(filter_func):
            self.env['email.template'].browse(template_id).send_mail(attendee.id, force_send=force_send)


class event_registration(models.Model):
    _name = 'event.registration'
    _description = 'Attendee'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'name, create_date desc'

    origin = fields.Char(
        string='Source Document', readonly=True,
        help="Reference of the document that created the registration, for example a sale order")
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
    name = fields.Char(string='Attendee Name', select=True)

    @api.one
    @api.constrains('event_id', 'state')
    def _check_seats_limit(self):
        if self.event_id.seats_max and self.event_id.seats_available < (1 if self.state == 'draft' else 0):
            raise Warning(_('No more seats available for this event.'))

    @api.one
    def _check_auto_confirmation(self):
        if self._context.get('registration_force_draft'):
            return False
        if self.event_id and self.event_id.state == 'confirm' and self.event_id.auto_confirm and self.event_id.seats_available:
            return True
        return False

    @api.model
    def create(self, vals):
        registration = super(event_registration, self).create(vals)
        if registration._check_auto_confirmation():
            registration.sudo().confirm_registration()
        return registration

    @api.one
    def do_draft(self):
        self.state = 'draft'

    @api.one
    def confirm_registration(self):
        self.event_id.message_post(
            body=_('New registration confirmed: %s.') % (self.name or ''),
            subtype="event.mt_event_registration")
        self.state = 'open'

    @api.one
    def button_reg_close(self):
        """ Close Registration """
        today = fields.Datetime.now()
        if self.event_id.date_begin <= today:
            self.write({'state': 'done', 'date_closed': today})
        else:
            raise Warning(_("You must wait for the starting day of the event to do this action."))

    @api.one
    def button_reg_cancel(self):
        self.state = 'cancel'

    @api.onchange('partner_id')
    def _onchange_partner(self):
        if self.partner_id:
            contact_id = self.partner_id.address_get().get('default', False)
            if contact_id:
                contact = self.env['res.partner'].browse(contact_id)
                self.name = self.name or contact.name
                self.email = self.email or contact.email
                self.phone = self.phone or contact.phone
