# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from datetime import timedelta

import pytz

from openerp import models, fields, api, _
from openerp.exceptions import Warning

class event_type(models.Model):
    """ Event Type """
    _name = 'event.type'

    name = fields.Char(string='Event Type', required=True)
    default_reply_to = fields.Char(string='Default Reply-To',
        help="The email address of the organizer which is put in the 'Reply-To' of all emails sent automatically at event or registrations confirmation. You can also put your email address of your mail gateway if you use one.")
    default_email_event = fields.Many2one('email.template', string='Event Confirmation Email',
        help="It will select this default confirmation event mail value when you choose this event")
    default_email_registration = fields.Many2one('email.template', string='Registration Confirmation Email',
        help="It will select this default confirmation registration mail value when you choose this event")
    default_registration_min = fields.Integer(string='Default Minimum Registration', default=0,
        help="It will select this default minimum value when you choose this event")
    default_registration_max = fields.Integer(string='Default Maximum Registration', default=0,
        help="It will select this default maximum value when you choose this event")


class event_event(models.Model):
    """Event"""
    _name = 'event.event'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'date_begin'

    name = fields.Char(string='Event Name', translate=True, required=True,
        readonly=False, states={'done': [('readonly', True)]})
    user_id = fields.Many2one('res.users', string='Responsible User',
        default=lambda self: self.env.user,
        readonly=False, states={'done': [('readonly', True)]})
    type = fields.Many2one('event.type', string='Type of Event',
        readonly=False, states={'done': [('readonly', True)]})
    seats_max = fields.Integer(string='Maximum Avalaible Seats', oldname='register_max',
        readonly=True, states={'draft': [('readonly', False)]},
        help="You can for each event define a maximum registration level. If you have too much registrations you are not able to confirm your event. (put 0 to ignore this rule )")
    seats_min = fields.Integer(string='Minimum Reserved Seats', oldname='register_min',
        readonly=True, states={'draft': [('readonly', False)]},
        help="You can for each event define a minimum registration level. If you do not enough registrations you are not able to confirm your event. (put 0 to ignore this rule )")

    seats_reserved = fields.Integer(oldname='register_current', string='Reserved Seats',
        store=True, readonly=True, compute='_compute_seats')
    seats_available = fields.Integer(oldname='register_avail', string='Available Seats',
        store=True, readonly=True, compute='_compute_seats')
    seats_unconfirmed = fields.Integer(oldname='register_prospect', string='Unconfirmed Seat Reservations',
        store=True, readonly=True, compute='_compute_seats')
    seats_used = fields.Integer(oldname='register_attended', string='Number of Participations',
        store=True, readonly=True, compute='_compute_seats')

    @api.multi
    @api.depends('seats_max', 'registration_ids.state', 'registration_ids.nb_register')
    def _compute_seats(self):
        """ Determine reserved, available, reserved but unconfirmed and used seats. """
        # initialize fields to 0
        for event in self:
            event.seats_unconfirmed = event.seats_reserved = event.seats_used = 0
        # aggregate registrations by event and by state
        if self.ids:
            state_field = {
                'draft': 'seats_unconfirmed',
                'open':'seats_reserved',
                'done': 'seats_used',
            }
            query = """ SELECT event_id, state, sum(nb_register)
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
            event.seats_available = \
                event.seats_max - (event.seats_reserved + event.seats_used) \
                if event.seats_max > 0 else 0

    registration_ids = fields.One2many('event.registration', 'event_id', string='Registrations',
        readonly=False, states={'done': [('readonly', True)]})
    count_registrations = fields.Integer(string='Registrations',
        compute='_count_registrations')

    date_begin = fields.Datetime(string='Start Date', required=True,
        readonly=True, states={'draft': [('readonly', False)]})
    date_end = fields.Datetime(string='End Date', required=True,
        readonly=True, states={'draft': [('readonly', False)]})

    @api.model
    def _tz_get(self):
        return [(x, x) for x in pytz.all_timezones]

    date_tz = fields.Selection('_tz_get', string='Timezone',
                        default=lambda self: self._context.get('tz', 'UTC'))

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

    date_begin_located = fields.Datetime(string='Start Date Located', compute='_compute_date_begin_tz')
    date_end_located = fields.Datetime(string='End Date Located', compute='_compute_date_end_tz')

    state = fields.Selection([
            ('draft', 'Unconfirmed'),
            ('cancel', 'Cancelled'),
            ('confirm', 'Confirmed'),
            ('done', 'Done')
        ], string='Status', default='draft', readonly=True, required=True, copy=False,
        help="If event is created, the status is 'Draft'. If event is confirmed for the particular dates the status is set to 'Confirmed'. If the event is over, the status is set to 'Done'. If event is cancelled the status is set to 'Cancelled'.")
    email_registration_id = fields.Many2one('email.template', string='Registration Confirmation Email',
        help='This field contains the template of the mail that will be automatically sent each time a registration for this event is confirmed.')
    email_confirmation_id = fields.Many2one('email.template', string='Event Confirmation Email',
        help="If you set an email template, each participant will receive this email announcing the confirmation of the event.")
    reply_to = fields.Char(string='Reply-To Email',
        readonly=False, states={'done': [('readonly', True)]},
        help="The email address of the organizer is likely to be put here, with the effect to be in the 'Reply-To' of the mails sent automatically at event or registrations confirmation. You can also put the email address of your mail gateway if you use one.")
    address_id = fields.Many2one('res.partner', string='Location',
        default=lambda self: self.env.user.company_id.partner_id,
        readonly=False, states={'done': [('readonly', True)]})
    country_id = fields.Many2one('res.country', string='Country', related='address_id.country_id',
        store=True, readonly=False, states={'done': [('readonly', True)]})
    description = fields.Html(string='Description', oldname='note', translate=True,
        readonly=False, states={'done': [('readonly', True)]})
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
        default=lambda self: self.env['res.company']._company_default_get('event.event'),
        required=False, readonly=False, states={'done': [('readonly', True)]})
    organizer_id = fields.Many2one('res.partner', string='Organizer',
        default=lambda self: self.env.user.company_id.partner_id)

    is_subscribed = fields.Boolean(string='Subscribed',
        compute='_compute_subscribe')

    @api.one
    @api.depends('registration_ids')
    def _count_registrations(self):
        self.count_registrations = len(self.registration_ids)

    @api.one
    @api.depends('registration_ids.user_id', 'registration_ids.state')
    def _compute_subscribe(self):
        """ Determine whether the current user is already subscribed to any event in `self` """
        user = self.env.user
        self.is_subscribed = any(
            reg.user_id == user and reg.state in ('open', 'done')
            for reg in self.registration_ids
        )

    @api.one
    @api.depends('name', 'date_begin', 'date_end')
    def _compute_display_name(self):
        dates = [dt.split(' ')[0] for dt in [self.date_begin, self.date_end] if dt]
        dates = sorted(set(dates))
        self.display_name = '%s (%s)' % (self.name, ' - '.join(dates))

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
    def confirm_event(self):
        if self.email_confirmation_id:
            # send reminder that will confirm the event for all the people that were already confirmed
            regs = self.registration_ids.filtered(lambda reg: reg.state not in ('draft', 'cancel'))
            regs.mail_user_confirm()
        self.state = 'confirm'

    @api.one
    def button_confirm(self):
        """ Confirm Event and send confirmation email to all register peoples """
        self.confirm_event()

    @api.one
    def subscribe_to_event(self):
        """ Subscribe the current user to a given event """
        user = self.env.user
        num_of_seats = int(self._context.get('ticket', 1))
        regs = self.registration_ids.filtered(lambda reg: reg.user_id == user)
        # the subscription is done as SUPERUSER_ID because in case we share the
        # kanban view, we want anyone to be able to subscribe
        if not regs:
            regs = regs.sudo().create({
                'event_id': self.id,
                'email': user.email,
                'name':user.name,
                'user_id': user.id,
                'nb_register': num_of_seats,
            })
        else:
            regs.write({'nb_register': num_of_seats})
        regs.sudo().confirm_registration()

    @api.one
    def unsubscribe_to_event(self):
        """ Unsubscribe the current user from a given event """
        # the unsubscription is done as SUPERUSER_ID because in case we share
        # the kanban view, we want anyone to be able to unsubscribe
        user = self.env.user
        regs = self.sudo().registration_ids.filtered(lambda reg: reg.user_id == user)
        regs.button_reg_cancel()

    @api.onchange('type')
    def _onchange_type(self):
        if self.type:
            self.reply_to = self.type.default_reply_to
            self.email_registration_id = self.type.default_email_registration
            self.email_confirmation_id = self.type.default_email_event
            self.seats_min = self.type.default_registration_min
            self.seats_max = self.type.default_registration_max

    @api.onchange('date_begin')
    def _onchange_date_begin(self):
        if self.date_begin and not self.date_end:
            date_begin = fields.Datetime.from_string(self.date_begin)
            self.date_end = fields.Datetime.to_string(date_begin + timedelta(hours=1))


class event_registration(models.Model):
    """Event Registration"""
    _name= 'event.registration'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'name, create_date desc'

    origin = fields.Char(string='Source Document', readonly=True,
        help="Reference of the sales order which created the registration")
    nb_register = fields.Integer(string='Number of Participants', required=True, default=1,
        readonly=True, states={'draft': [('readonly', False)]})
    event_id = fields.Many2one('event.event', string='Event', required=True,
        readonly=True, states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one('res.partner', string='Partner',
        states={'done': [('readonly', True)]})
    date_open = fields.Datetime(string='Registration Date', readonly=True)
    date_closed = fields.Datetime(string='Attended Date', readonly=True)
    reply_to = fields.Char(string='Reply-to Email', related='event_id.reply_to',
        readonly=True)
    log_ids = fields.One2many('mail.message', 'res_id', string='Logs',
        domain=[('model', '=', _name)])
    event_begin_date = fields.Datetime(string="Event Start Date", related='event_id.date_begin',
        readonly=True)
    event_end_date = fields.Datetime(string="Event End Date", related='event_id.date_end',
        readonly=True)
    user_id = fields.Many2one('res.users', string='User', states={'done': [('readonly', True)]})
    company_id = fields.Many2one('res.company', string='Company', related='event_id.company_id',
        store=True, readonly=True, states={'draft':[('readonly', False)]})
    state = fields.Selection([
            ('draft', 'Unconfirmed'),
            ('cancel', 'Cancelled'),
            ('open', 'Confirmed'),
            ('done', 'Attended'),
        ], string='Status', default='draft', readonly=True, copy=False)
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    name = fields.Char(string='Name', select=True)

    @api.one
    @api.constrains('event_id', 'state', 'nb_register')
    def _check_seats_limit(self):
        if self.event_id.seats_max and \
            self.event_id.seats_available < (self.nb_register if self.state == 'draft' else 0):
                raise Warning(_('No more available seats.'))

    @api.one
    def do_draft(self):
        self.state = 'draft'

    @api.one
    def confirm_registration(self):
        self.event_id.message_post(
            body=_('New registration confirmed: %s.') % (self.name or ''),
            subtype="event.mt_event_registration")
        self.message_post(body=_('Event Registration confirmed.'))
        self.state = 'open'

    @api.one
    def registration_open(self):
        """ Open Registration """
        self.confirm_registration()
        self.mail_user()

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

    @api.one
    def mail_user(self):
        """Send email to user with email_template when registration is done """
        if self.event_id.state == 'confirm' and self.event_id.email_confirmation_id:
            self.mail_user_confirm()
        else:
            template = self.event_id.email_registration_id
            if template:
                mail_message = template.send_mail(self.id)

    @api.one
    def mail_user_confirm(self):
        """Send email to user when the event is confirmed """
        template = self.event_id.email_confirmation_id
        if template:
            mail_message = template.send_mail(self.id)

    @api.onchange('partner_id')
    def _onchange_partner(self):
        if self.partner_id:
            contact = self.partner_id.address_get().get('default', False)
            if contact:
                self.name = contact.name
                self.email = contact.email
                self.phone = contact.phone

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
