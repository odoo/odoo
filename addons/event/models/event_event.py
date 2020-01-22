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
    _description = 'Event Category'
    _order = 'sequence, id'

    @api.model
    def _get_default_event_type_mail_ids(self):
        return [(0, 0, {
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

    name = fields.Char('Event Category', required=True, translate=True)
    sequence = fields.Integer()
    # registration
    has_seats_limitation = fields.Boolean('Limited Seats')
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
        _tz_get, string='Timezone', default=lambda self: self.env.user.tz or 'UTC')
    # communication
    use_hashtag = fields.Boolean('Use Default Hashtag')
    default_hashtag = fields.Char('Twitter Hashtag')
    use_mail_schedule = fields.Boolean(
        'Automatically Send Emails', default=True)
    event_type_mail_ids = fields.One2many(
        'event.type.mail', 'event_type_id', string='Mail Schedule',
        copy=False,
        default=lambda self: self._get_default_event_type_mail_ids())

    @api.onchange('has_seats_limitation')
    def _onchange_has_seats_limitation(self):
        if not self.has_seats_limitation:
            self.default_registration_min = 0
            self.default_registration_max = 0


class EventEvent(models.Model):
    """Event"""
    _name = 'event.event'
    _description = 'Event'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_begin'

    def _get_default_stage_id(self):
        event_stages = self.env['event.stage'].search([])
        return event_stages[0] if event_stages else False

    name = fields.Char(string='Event', translate=True, required=True)
    note = fields.Text(string='Note')
    description = fields.Html(string='Description', translate=html_translate, sanitize_attributes=False)
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
    event_type_id = fields.Many2one('event.type', string='Category', ondelete='set null')
    color = fields.Integer('Kanban Color Index')
    event_mail_ids = fields.One2many('event.mail', 'event_id', string='Mail Schedule', copy=True)
    # Kanban fields
    kanban_state = fields.Selection([('normal', 'In Progress'), ('done', 'Done'), ('blocked', 'Blocked')])
    kanban_state_label = fields.Char(compute='_compute_kanban_state_label', string='Kanban State Label', tracking=True, store=True)
    stage_id = fields.Many2one(
        'event.stage', ondelete='restrict', default=_get_default_stage_id,
        group_expand='_read_group_stage_ids', tracking=True)
    legend_blocked = fields.Char(related='stage_id.legend_blocked', string='Kanban Blocked Explanation', readonly=True)
    legend_done = fields.Char(related='stage_id.legend_done', string='Kanban Valid Explanation', readonly=True)
    legend_normal = fields.Char(related='stage_id.legend_normal', string='Kanban Ongoing Explanation', readonly=True)
    # Seats and computation
    seats_max = fields.Integer(
        string='Maximum Attendees Number',
        help="For each event you can define a maximum registration of seats(number of attendees), above this numbers the registrations are not accepted.")
    seats_availability = fields.Selection(
        [('limited', 'Limited'), ('unlimited', 'Unlimited')],
        'Maximum Attendees', required=True, default='unlimited')
    seats_min = fields.Integer(
        string='Minimum Attendees',
        help="For each event you can define a minimum reserved seats (number of attendees), if it does not reach the mentioned registrations the event can not be confirmed (keep 0 to ignore this rule)")
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
        compute_sudo=True, readonly=True, compute='_compute_seats')
    # Registration fields
    auto_confirm = fields.Boolean(string='Autoconfirm Registrations')
    registration_ids = fields.One2many('event.registration', 'event_id', string='Attendees')
    event_registrations_open = fields.Boolean('Registration open', compute='_compute_event_registrations_open')
    # Date fields
    date_tz = fields.Selection(
        _tz_get, string='Timezone', required=True,
        default=lambda self: self.env.user.tz or 'UTC')
    date_begin = fields.Datetime(string='Start Date', required=True, tracking=True)
    date_end = fields.Datetime(string='End Date', required=True, tracking=True)
    date_begin_located = fields.Char(string='Start Date Located', compute='_compute_date_begin_tz')
    date_end_located = fields.Char(string='End Date Located', compute='_compute_date_end_tz')
    is_one_day = fields.Boolean(compute='_compute_field_is_one_day')
    # Location and communication
    is_online = fields.Boolean('Online Event')
    address_id = fields.Many2one(
        'res.partner', string='Location', tracking=True,
        default=lambda self: self.env.company.partner_id,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    country_id = fields.Many2one('res.country', 'Country',  related='address_id.country_id', store=True, readonly=False)
    twitter_hashtag = fields.Char('Twitter Hashtag')
    # badge fields
    badge_front = fields.Html(string='Badge Front')
    badge_back = fields.Html(string='Badge Back')
    badge_innerleft = fields.Html(string='Badge Inner Left')
    badge_innerright = fields.Html(string='Badge Inner Right')
    event_logo = fields.Html(string='Event Logo')

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
            self.env['event.registration'].flush(['event_id', 'state'])
            self._cr.execute(query, (tuple(self.ids),))
            for event_id, state, num in self._cr.fetchall():
                event = self.browse(event_id)
                event[state_field[state]] += num
        # compute seats_available
        for event in self:
            if event.seats_max > 0:
                event.seats_available = event.seats_max - (event.seats_reserved + event.seats_used)
            event.seats_expected = event.seats_unconfirmed + event.seats_reserved + event.seats_used

    @api.depends('date_end', 'seats_available', 'seats_availability')
    def _compute_event_registrations_open(self):
        for event in self:
            event.event_registrations_open = event.date_end > fields.Datetime.now() and (event.seats_available or event.seats_availability == 'unlimited')

    @api.depends('stage_id', 'kanban_state')
    def _compute_kanban_state_label(self):
        for event in self:
            if event.kanban_state == 'normal':
                event.kanban_state_label = event.stage_id.legend_normal
            elif event.kanban_state == 'blocked':
                event.kanban_state_label = event.stage_id.legend_blocked
            else:
                event.kanban_state_label = event.stage_id.legend_done

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

    @api.depends('date_begin', 'date_end', 'date_tz')
    def _compute_field_is_one_day(self):
        for event in self:
            # Need to localize because it could begin late and finish early in
            # another timezone
            event = event.with_context(tz=event.date_tz)
            begin_tz = fields.Datetime.context_timestamp(event, event.date_begin)
            end_tz = fields.Datetime.context_timestamp(event, event.date_end)
            event.is_one_day = (begin_tz.date() == end_tz.date())

    @api.onchange('is_online')
    def _onchange_is_online(self):
        if self.is_online:
            self.address_id = False

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

            if self.event_type_id.use_mail_schedule and self.event_type_id.event_type_mail_ids:
                self.event_mail_ids = [(5, 0, 0)] + [
                    (0, 0, {
                        attribute_name: line[attribute_name] if not isinstance(line[attribute_name], models.BaseModel) else line[attribute_name].id
                        for attribute_name in self.env['event.type.mail']._get_event_mail_fields_whitelist()
                        })
                    for line in self.event_type_id.event_type_mail_ids]

    @api.constrains('seats_min', 'seats_max', 'seats_availability')
    def _check_seats_min_max(self):
        if any(event.seats_availability == 'limited' and event.seats_min > event.seats_max for event in self):
            raise ValidationError(_('Maximum attendees number should be greater than minimum attendees number.'))

    @api.constrains('seats_max', 'seats_available')
    def _check_seats_limit(self):
        if any(event.seats_availability == 'limited' and event.seats_max and event.seats_available < 0 for event in self):
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
        res = super(EventEvent, self).create(vals)
        if res.organizer_id:
            res.message_subscribe([res.organizer_id.id])
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
