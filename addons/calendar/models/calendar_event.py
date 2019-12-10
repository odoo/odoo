# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import babel.dates
import datetime
import math
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import logging
import pytz

from odoo import api, fields, models
from odoo import tools
from odoo.addons.base.models.res_partner import _tz_get
from odoo.addons.calendar.models.calendar_attendee import Attendee
from odoo.addons.calendar.models.calendar_recurrence import weekday_to_field, RRULE_TYPE_SELECTION, END_TYPE_SELECTION, MONTH_BY_SELECTION, WEEKDAY_SELECTION, BYDAY_SELECTION
from odoo.tools.translate import _
from odoo.tools.misc import get_lang
from odoo.tools import pycompat
from odoo.exceptions import UserError, ValidationError


_logger = logging.getLogger(__name__)


SORT_ALIASES = {
    'start': 'sort_start',
    'start_date': 'sort_start',
    'start_datetime': 'sort_start',
}

def get_weekday_occurence(date):
    """
    :returns: ocurrence

    >>> get_weekday_occurence(date(2019, 12, 17))
    3  # third Tuesday of the month

    >>> get_weekday_occurence(date(2019, 12, 25))
    -1  # last Friday of the month
    """
    occurence_in_month = math.ceil(date.day/7)
    if occurence_in_month in {4, 5}:  # fourth or fifth week on the month -> last
        return -1
    return occurence_in_month


class Meeting(models.Model):
    """ Model for Calendar Event

        Special context keys :
            - `no_mail_to_attendees` : disabled sending email to attendees when creating/editing a meeting
    """

    _name = 'calendar.event'
    _description = "Calendar Event"
    _order = "start desc"
    _inherit = ["mail.thread"]

    @api.model
    def default_get(self, fields):
        # super default_model='crm.lead' for easier use in addons
        if self.env.context.get('default_res_model') and not self.env.context.get('default_res_model_id'):
            self = self.with_context(
                default_res_model_id=self.env['ir.model'].sudo().search([
                    ('model', '=', self.env.context['default_res_model'])
                ], limit=1).id
            )

        defaults = super(Meeting, self).default_get(fields)

        # support active_model / active_id as replacement of default_* if not already given
        if 'res_model_id' not in defaults and 'res_model_id' in fields and \
                self.env.context.get('active_model') and self.env.context['active_model'] != 'calendar.event':
            defaults['res_model_id'] = self.env['ir.model'].sudo().search([('model', '=', self.env.context['active_model'])], limit=1).id
        if 'res_id' not in defaults and 'res_id' in fields and \
                defaults.get('res_model_id') and self.env.context.get('active_id'):
            defaults['res_id'] = self.env.context['active_id']

        return defaults

    @api.model
    def _default_partners(self):
        """ When active_model is res.partner, the current partners should be attendees """
        partners = self.env.user.partner_id
        active_id = self._context.get('active_id')
        if self._context.get('active_model') == 'res.partner' and active_id:
            if active_id not in partners.ids:
                partners |= self.env['res.partner'].browse(active_id)
        return partners

    def _find_my_attendee(self):
        """ Return the first attendee where the user connected has been invited
            from all the meeting_ids in parameters.
        """
        self.ensure_one()
        for attendee in self.attendee_ids:
            if self.env.user.partner_id == attendee.partner_id:
                return attendee
        return False

    @api.model
    def _get_date_formats(self):
        """ get current date and time format, according to the context lang
            :return: a tuple with (format date, format time)
        """
        lang = get_lang(self.env)
        return (lang.date_format, lang.time_format)

    @api.model
    def _get_recurrent_fields(self):
        return {'byday', 'until', 'rrule_type', 'month_by', 'event_tz', 'rrule',
                'interval', 'count', 'end_type', 'mo', 'tu', 'we', 'th', 'fr', 'sa',
                'su', 'day', 'weekday'}

    @api.model
    def _get_time_fields(self):
        return {'start', 'stop', 'start_date', 'stop_date', 'start_datetime', 'stop_datetime'}

    @api.model
    def _get_display_time(self, start, stop, zduration, zallday):
        """ Return date and time (from to from) based on duration with timezone in string. Eg :
                1) if user add duration for 2 hours, return : August-23-2013 at (04-30 To 06-30) (Europe/Brussels)
                2) if event all day ,return : AllDay, July-31-2013
        """
        timezone = self._context.get('tz') or self.env.user.partner_id.tz or 'UTC'

        # get date/time format according to context
        format_date, format_time = self._get_date_formats()

        # convert date and time into user timezone
        self_tz = self.with_context(tz=timezone)
        date = fields.Datetime.context_timestamp(self_tz, fields.Datetime.from_string(start))
        date_deadline = fields.Datetime.context_timestamp(self_tz, fields.Datetime.from_string(stop))

        # convert into string the date and time, using user formats
        to_text = pycompat.to_text
        date_str = to_text(date.strftime(format_date))
        time_str = to_text(date.strftime(format_time))

        if zallday:
            display_time = _("AllDay , %s") % (date_str)
        elif zduration < 24:
            duration = date + timedelta(minutes=round(zduration*60))
            duration_time = to_text(duration.strftime(format_time))
            display_time = _(u"%s at (%s To %s) (%s)") % (
                date_str,
                time_str,
                duration_time,
                timezone,
            )
        else:
            dd_date = to_text(date_deadline.strftime(format_date))
            dd_time = to_text(date_deadline.strftime(format_time))
            display_time = _(u"%s at %s To\n %s at %s (%s)") % (
                date_str,
                time_str,
                dd_date,
                dd_time,
                timezone,
            )
        return display_time

    def _get_duration(self, start, stop):
        """ Get the duration value between the 2 given dates. """
        if start and stop:
            diff = fields.Datetime.from_string(stop) - fields.Datetime.from_string(start)
            if diff:
                duration = float(diff.days) * 24 + (float(diff.seconds) / 3600)
                return round(duration, 2)
            return 0.0

    def _compute_is_highlighted(self):
        if self.env.context.get('active_model') == 'res.partner':
            partner_id = self.env.context.get('active_id')
            for event in self:
                if event.partner_ids.filtered(lambda s: s.id == partner_id):
                    event.is_highlighted = True
                else:
                    event.is_highlighted = False
        else:
            for event in self:
                event.is_highlighted = False

    name = fields.Char('Meeting Subject', required=True, states={'done': [('readonly', True)]})
    state = fields.Selection([('draft', 'Unconfirmed'), ('open', 'Confirmed')], string='Status', readonly=True, tracking=True, default='draft')

    is_attendee = fields.Boolean('Attendee', compute='_compute_attendee')
    attendee_status = fields.Selection(Attendee.STATE_SELECTION, string='Attendee Status', compute='_compute_attendee')
    display_time = fields.Char('Event Time', compute='_compute_display_time')
    display_start = fields.Char('Date', compute='_compute_display_start', store=True)
    start = fields.Datetime('Start', required=True, help="Start date of an event, without time for full days events")
    stop = fields.Datetime('Stop', required=True, help="Stop date of an event, without time for full days events")

    allday = fields.Boolean('All Day', states={'done': [('readonly', True)]}, default=False)
    start_date = fields.Date('Start Date', compute='_compute_dates', inverse='_inverse_dates', store=True, states={'done': [('readonly', True)]}, tracking=True)
    start_datetime = fields.Datetime('Start DateTime', compute='_compute_dates', inverse='_inverse_dates', store=True, states={'done': [('readonly', True)]}, tracking=True)
    stop_date = fields.Date('End Date', compute='_compute_dates', inverse='_inverse_dates', store=True, states={'done': [('readonly', True)]}, tracking=True)
    stop_datetime = fields.Datetime('End Datetime', compute='_compute_dates', inverse='_inverse_dates', store=True, states={'done': [('readonly', True)]}, tracking=True)  # old date_deadline
    event_tz = fields.Selection('_event_tz_get', string='Timezone', default=lambda self: self.env.context.get('tz') or self.user_id.tz)
    duration = fields.Float('Duration', compute='_compute_dates', inverse='_inverse_duration', compute_sudo=True, states={'done': [('readonly', True)]})
    description = fields.Text('Description', states={'done': [('readonly', True)]})
    privacy = fields.Selection([('public', 'Everyone'), ('private', 'Only me'), ('confidential', 'Only internal users')], 'Privacy', default='public', states={'done': [('readonly', True)]}, required=True)
    location = fields.Char('Location', states={'done': [('readonly', True)]}, tracking=True, help="Location of Event")
    show_as = fields.Selection([('free', 'Free'), ('busy', 'Busy')], 'Show Time as', states={'done': [('readonly', True)]}, default='busy', required=True)

    # linked document
    res_id = fields.Integer('Document ID')
    res_model_id = fields.Many2one('ir.model', 'Document Model', ondelete='cascade')
    res_model = fields.Char('Document Model Name', related='res_model_id.model', readonly=True, store=True)
    activity_ids = fields.One2many('mail.activity', 'calendar_event_id', string='Activities')

    #redifine message_ids to remove autojoin to avoid search to crash in get_recurrent_ids
    message_ids = fields.One2many(auto_join=False)

    user_id = fields.Many2one('res.users', 'Owner', default=lambda self: self.env.user)
    partner_id = fields.Many2one(
        'res.partner', string='Responsible', related='user_id.partner_id', readonly=True)
    active = fields.Boolean(
        'Active', default=True,
        help="If the active field is set to false, it will allow you to hide the event alarm information without removing it.")
    categ_ids = fields.Many2many(
        'calendar.event.type', 'meeting_category_rel', 'event_id', 'type_id', 'Tags')
    attendee_ids = fields.One2many(
        'calendar.attendee', 'event_id', 'Participant')
    partner_ids = fields.Many2many(
        'res.partner', 'calendar_event_res_partner_rel',
        string='Attendees', default=_default_partners)
    alarm_ids = fields.Many2many(
        'calendar.alarm', 'calendar_alarm_calendar_event_rel',
        string='Reminders', ondelete="restrict")
    is_highlighted = fields.Boolean(
        compute='_compute_is_highlighted', string='Is the Event Highlighted')

    # RECURRENCE FIELD
    recurrency = fields.Boolean('Recurrent', help="Recurrent Event")
    recurrence_id = fields.Many2one('calendar.recurrence', string="Recurrence Rule", index=True)
    recurrence_update = fields.Selection([
        ('self_only', "This event"),
        ('future_events', "This and following events"),
        ('all_events', "All events"),
    ], store=False, copy=False, default='self_only',
       help="Choose what to do with other events in the recurrence. Updating All Events is not allowed when dates or time is modified")

    # Those field are pseudo-related fields of recurrence_id.
    # They can't be "real" related fields because it should work at record creation
    # when recurrence_id is not created yet.
    # If some of these fields are set and recurrence_id does not exists, a `calendar.recurrence.rule`
    # will be dynamically created.
    rrule = fields.Char('Recurrent Rule', compute='_compute_recurrence', readonly=False)
    rrule_type = fields.Selection(RRULE_TYPE_SELECTION, string='Recurrence',
                                  help="Let the event automatically repeat at that interval",
                                  compute='_compute_recurrence', readonly=False)
    event_tz = fields.Selection(_tz_get, string='Timezone', compute='_compute_recurrence', readonly=False)
    end_type = fields.Selection(END_TYPE_SELECTION, string='Recurrence Termination', compute='_compute_recurrence', readonly=False)
    interval = fields.Integer(string='Repeat Every', help="Repeat every (Days/Week/Month/Year)", compute='_compute_recurrence', readonly=False)
    count = fields.Integer(string='Repeat', help="Repeat x times", compute='_compute_recurrence', readonly=False)
    mo = fields.Boolean('Mon', compute='_compute_recurrence', readonly=False)
    tu = fields.Boolean('Tue', compute='_compute_recurrence', readonly=False)
    we = fields.Boolean('Wed', compute='_compute_recurrence', readonly=False)
    th = fields.Boolean('Thu', compute='_compute_recurrence', readonly=False)
    fr = fields.Boolean('Fri', compute='_compute_recurrence', readonly=False)
    sa = fields.Boolean('Sat', compute='_compute_recurrence', readonly=False)
    su = fields.Boolean('Sun', compute='_compute_recurrence', readonly=False)
    month_by = fields.Selection(MONTH_BY_SELECTION, string='Option', compute='_compute_recurrence', readonly=False)
    day = fields.Integer('Date of month', compute='_compute_recurrence', readonly=False)
    weekday = fields.Selection(WEEKDAY_SELECTION, compute='_compute_recurrence', readonly=False)
    byday = fields.Selection(BYDAY_SELECTION, compute='_compute_recurrence', readonly=False)
    until = fields.Date(compute='_compute_recurrence', readonly=False)

    def _compute_attendee(self):
        for meeting in self:
            attendee = meeting._find_my_attendee()
            meeting.is_attendee = bool(attendee)
            meeting.attendee_status = attendee.state if attendee else 'needsAction'

    def _compute_display_time(self):
        for meeting in self:
            meeting.display_time = self._get_display_time(meeting.start, meeting.stop, meeting.duration, meeting.allday)

    @api.depends('allday', 'start_date', 'start_datetime')
    def _compute_display_start(self):
        for meeting in self:
            meeting.display_start = meeting.start_date if meeting.allday else meeting.start_datetime

    @api.depends('allday', 'start', 'stop')
    def _compute_dates(self):
        """ Adapt the value of start_date(time)/stop_date(time) according to start/stop fields and allday. Also, compute
            the duration for not allday meeting ; otherwise the duration is set to zero, since the meeting last all the day.
        """
        for meeting in self:
            if meeting.allday and meeting.start and meeting.stop:
                meeting.start_date = meeting.start.date()
                meeting.start_datetime = False
                meeting.stop_date = meeting.stop.date()
                meeting.stop_datetime = False

                meeting.duration = 0.0
            else:
                meeting.start_date = False
                meeting.start_datetime = meeting.start
                meeting.stop_date = False
                meeting.stop_datetime = meeting.stop

                meeting.duration = self._get_duration(meeting.start, meeting.stop)

    def _inverse_dates(self):
        for meeting in self:
            if meeting.allday:

                # Convention break:
                # stop and start are NOT in UTC in allday event
                # in this case, they actually represent a date
                # because fullcalendar just drops times for full day events.
                # i.e. Christmas is on 25/12 for everyone
                # even if people don't celebrate it simultaneously
                enddate = fields.Datetime.from_string(meeting.stop_date)
                enddate = enddate.replace(hour=18)

                startdate = fields.Datetime.from_string(meeting.start_date)
                startdate = startdate.replace(hour=8)  # Set 8 AM

                meeting.write({
                    'start': startdate.replace(tzinfo=None),
                    'stop': enddate.replace(tzinfo=None)
                })
            else:
                meeting.write({'start': meeting.start_datetime,
                               'stop': meeting.stop_datetime})

    def _inverse_duration(self):
        for event in self:
            event.stop = event.start + relativedelta(hours=event.duration)

    @api.constrains('start_datetime', 'stop_datetime', 'start_date', 'stop_date')
    def _check_closing_date(self):
        for meeting in self:
            if meeting.start_datetime and meeting.stop_datetime and meeting.stop_datetime < meeting.start_datetime:
                raise ValidationError(
                    _('The ending date and time cannot be earlier than the starting date and time.') + '\n' +
                    _("Meeting '%s' starts '%s' and ends '%s'") % (meeting.name, meeting.start_datetime, meeting.stop_datetime)
                )
            if meeting.start_date and meeting.stop_date and meeting.stop_date < meeting.start_date:
                raise ValidationError(
                    _('The ending date cannot be earlier than the starting date.') + '\n' +
                    _("Meeting '%s' starts '%s' and ends '%s'") % (meeting.name, meeting.start_date, meeting.stop_date)
                )

    @api.onchange('start_datetime', 'duration')
    def _onchange_duration(self):
        if self.start_datetime:
            start = self.start_datetime
            self.start = self.start_datetime
            # Round the duration (in hours) to the minute to avoid weird situations where the event
            # stops at 4:19:59, later displayed as 4:19.
            self.stop = start + timedelta(minutes=round(self.duration * 60))
            if self.allday:
                self.stop -= timedelta(seconds=1)

    @api.onchange('start_date')
    def _onchange_start_date(self):
        if self.start_date:
            self.start = datetime.datetime.combine(self.start_date, datetime.time.min)

    @api.onchange('stop_date')
    def _onchange_stop_date(self):
        if self.stop_date:
            self.stop = datetime.datetime.combine(self.stop_date, datetime.time.max)

    ####################################################
    # Calendar Business, Reccurency, ...
    ####################################################

    @api.depends('recurrence_id', 'recurrency')
    def _compute_recurrence(self):
        recurrence_fields = self._get_recurrent_fields()
        false_values = {field: False for field in recurrence_fields}  # computes need to set a value
        defaults = self.env['calendar.recurrence'].default_get(recurrence_fields)
        for event in self:
            if event.recurrency:
                event_values = event._get_recurrence_params()
                rrule_values = {
                    field: event.recurrence_id[field]
                    for field in recurrence_fields
                    if event.recurrence_id[field]
                }
                event.update({**false_values, **defaults, **event_values, **rrule_values})
            else:
                event.update(false_values)

    def _get_ics_file(self):
        """ Returns iCalendar file for the event invitation.
            :returns a dict of .ics file content for each meeting
        """
        result = {}

        def ics_datetime(idate, allday=False):
            if idate:
                if allday:
                    return idate
                else:
                    return idate.replace(tzinfo=pytz.timezone('UTC'))
            return False

        try:
            # FIXME: why isn't this in CalDAV?
            import vobject
        except ImportError:
            _logger.warning("The `vobject` Python module is not installed, so iCal file generation is unavailable. Please install the `vobject` Python module")
            return result

        for meeting in self:
            cal = vobject.iCalendar()
            event = cal.add('vevent')

            if not meeting.start or not meeting.stop:
                raise UserError(_("First you have to specify the date of the invitation."))
            event.add('created').value = ics_datetime(fields.Datetime.now())
            event.add('dtstart').value = ics_datetime(meeting.start, meeting.allday)
            event.add('dtend').value = ics_datetime(meeting.stop, meeting.allday)
            event.add('summary').value = meeting.name
            if meeting.description:
                event.add('description').value = meeting.description
            if meeting.location:
                event.add('location').value = meeting.location
            if meeting.rrule:
                event.add('rrule').value = meeting.rrule

            if meeting.alarm_ids:
                for alarm in meeting.alarm_ids:
                    valarm = event.add('valarm')
                    interval = alarm.interval
                    duration = alarm.duration
                    trigger = valarm.add('TRIGGER')
                    trigger.params['related'] = ["START"]
                    if interval == 'days':
                        delta = timedelta(days=duration)
                    elif interval == 'hours':
                        delta = timedelta(hours=duration)
                    elif interval == 'minutes':
                        delta = timedelta(minutes=duration)
                    trigger.value = delta
                    valarm.add('DESCRIPTION').value = alarm.name or u'Odoo'
            for attendee in meeting.attendee_ids:
                attendee_add = event.add('attendee')
                attendee_add.value = u'MAILTO:' + (attendee.email or u'')
            result[meeting.id] = cal.serialize().encode('utf-8')

        return result

    def _attendees_values(self, partner_commands):
        """
        :param partner_commands: ORM commands for partner_id field (0 and 1 commands not supported)
        :return: associated attendee_ids ORM commands
        """
        attendee_commands = []

        removed_partner_ids = []
        added_partner_ids = []
        for command in partner_commands:
            op = command[0]
            if op in (2, 3):  # Remove partner
                removed_partner_ids += [command[1]]
            elif op == 6:  # Replace all
                removed_partner_ids += set(self.partner_ids.ids) - set(command[2])  # Don't recreate attendee if partner already attend the event
                added_partner_ids += set(command[2]) - set(self.partner_ids.ids)
            elif op == 4:
                added_partner_ids += [command[1]] if command[1] not in self.partner_ids.ids else []
            # commands 0 and 1 not supported

        attendees_to_unlink = self.env['calendar.attendee'].search([
            ('event_id', 'in', self.ids),
            ('partner_id', 'in', removed_partner_ids),
        ])
        attendee_commands += [[2, attendee.id] for attendee in attendees_to_unlink]  # Removes and delete

        attendee_commands += [
            [0, 0, dict(partner_id=partner_id)]
            for partner_id in added_partner_ids
        ]
        return attendee_commands

    def get_interval(self, interval, tz=None):
        """ Format and localize some dates to be used in email templates
            :param string interval: Among 'day', 'month', 'dayname' and 'time' indicating the desired formatting
            :param string tz: Timezone indicator (optional)
            :return unicode: Formatted date or time (as unicode string, to prevent jinja2 crash)
        """
        self.ensure_one()
        date = fields.Datetime.from_string(self.start)

        if tz:
            timezone = pytz.timezone(tz or 'UTC')
            date = date.replace(tzinfo=pytz.timezone('UTC')).astimezone(timezone)

        if interval == 'day':
            # Day number (1-31)
            result = str(date.day)

        elif interval == 'month':
            # Localized month name and year
            result = babel.dates.format_date(date=date, format='MMMM y', locale=get_lang(self.env).code)

        elif interval == 'dayname':
            # Localized day name
            result = babel.dates.format_date(date=date, format='EEEE', locale=get_lang(self.env).code)

        elif interval == 'time':
            # Localized time
            # FIXME: formats are specifically encoded to bytes, maybe use babel?
            dummy, format_time = self._get_date_formats()
            result = tools.ustr(date.strftime(format_time + " %Z"))

        return result

    def get_display_time_tz(self, tz=False):
        """ get the display_time of the meeting, forcing the timezone. This method is called from email template, to not use sudo(). """
        self.ensure_one()
        if tz:
            self = self.with_context(tz=tz)
        return self._get_display_time(self.start, self.stop, self.duration, self.allday)

    def action_open_calendar_event(self):
        if self.res_model and self.res_id:
            return self.env[self.res_model].browse(self.res_id).get_formview_action()
        return False

    def action_sendmail(self):
        email = self.env.user.email
        if email:
            for meeting in self:
                meeting.attendee_ids._send_mail_to_attendees('calendar.calendar_template_meeting_invitation')
        return True

    def _apply_recurrence_values(self, values, future=True):
        """Apply the new recurrence rules in `values`. Create a recurrence if it does not exist
        and create all missing events according to the rrule.
        If the changes are applied to future
        events only, a new recurrence is created with the updated rrule.

        :param values: new recurrence values to apply
        :param future: rrule values are applied to future events only if True.
                       Rrule changes are applied to all events in the recurrence otherwise.
                       (ignored if no recurrence exists yet).
        :return: events detached from the recurrence
        """
        if not values:
            return self.browse()
        recurrence_vals = []
        to_update = self.env['calendar.recurrence']
        for event in self:
            if not event.recurrence_id:
                recurrence_vals += [dict(values, base_event_id=event.id, calendar_event_ids=[(4, event.id)])]
            elif future:
                to_update |= event.recurrence_id._split_from(event, values)
        self.recurrency = True
        to_update |= self.env['calendar.recurrence'].create(recurrence_vals)
        return to_update._apply_recurrence()

    def _get_recurrence_params(self):
        if not self:
            return {}
        event_date = self._get_start_date()
        weekday_field_name = weekday_to_field(event_date.weekday())
        return {
            weekday_field_name: True,
            'weekday': weekday_field_name.upper(),
            'byday': str(get_weekday_occurence(event_date)),
            'day': event_date.day,
        }

    def _get_start_date(self):
        """Return the event starting date in the event's timezone.
        If no starting time is assigned (yet), return today as default
        :return: date
        """
        if not self.start:
            return fields.Date.today()
        if self.recurrence_id.event_tz:
            tz = pytz.timezone(self.recurrence_id.event_tz)
            return pytz.utc.localize(self.start).astimezone(tz).date()
        return self.start.date()

    def _split_recurrence(self, time_values):
        """Apply time changes to events and update the recurrence accordingly.

        :return: detached events
        """
        if not time_values:
            return self.browse()

        previous_week_day_field = weekday_to_field(self._get_start_date().weekday())
        self.write(time_values)
        return self._apply_recurrence_values({
            previous_week_day_field: False,
            **self._get_recurrence_params(),
        }, future=True)

    def _break_recurrence(self, future=True):
        """Breaks the event's recurrence.
        Stop the recurrence at the current event if `future` is True, leaving past events in the recurrence.
        If `future` is False, all events in the recurrence are detached and the recurrence itself is unlinked.
        :return: detached events excluding the current events
        """
        recurrences_to_unlink = self.env['calendar.recurrence']
        detached_events = self.env['calendar.event']
        for event in self:
            recurrence = event.recurrence_id
            if future:
                detached_events |= recurrence._stop_at(event)
            else:
                detached_events |= recurrence.calendar_event_ids
                recurrence.calendar_event_ids.recurrence_id = False
                recurrences_to_unlink |= recurrence
        recurrences_to_unlink.unlink()
        return detached_events - self

    def write(self, values):
        detached_events = self.env['calendar.event']
        recurrence_update_setting = values.pop('recurrence_update', None)
        update_recurrence = recurrence_update_setting in ('all_events', 'future_events') and len(self) == 1
        break_recurrence = values.get('recurrency') is False
        self._sync_activities(values)

        if 'partner_ids' in values:
            values['attendee_ids'] = self._attendees_values(values['partner_ids'])

        previous_attendees = self.attendee_ids

        recurrence_values = {field: values.pop(field) for field in self._get_recurrent_fields() if field in values}
        if update_recurrence:
            if break_recurrence:
                detached_events |= self._break_recurrence(future=recurrence_update_setting == 'future_events')
            else:
                update_start = self.start if recurrence_update_setting == 'future_events' else None
                time_values = {field: values.pop(field) for field in self.env['calendar.event']._get_time_fields() if field in values}
                if not update_start and (time_values or recurrence_values):
                    raise UserError(_("Updating All Events is not allowed when dates or time is modified. You can only update one particular event and following events."))
                detached_events |= self._split_recurrence(time_values)
                self.recurrence_id._write_events(values, dtstart=update_start)
        else:
            super().write(values)

        if recurrence_update_setting != 'self_only' and not break_recurrence:
            detached_events |= self._apply_recurrence_values(recurrence_values, future=recurrence_update_setting == 'future_events')

        (detached_events & self).active = False
        (detached_events - self).unlink()

        # Notify attendees if there is an alarm on the modified event, or if there was an alarm
        # that has just been removed, as it might have changed their next event notification
        if not self._context.get('dont_notify'):
            if self.alarm_ids or values.get('alarm_ids'):
                self.env['calendar.alarm_manager']._notify_next_alarm(self.partner_ids.ids)

        current_attendees = self.filtered('active').attendee_ids
        if 'partner_ids' in values:
            (current_attendees - previous_attendees)._send_mail_to_attendees('calendar.calendar_template_meeting_invitation')
        if 'start' in values:
            (current_attendees & previous_attendees)._send_mail_to_attendees('calendar.calendar_template_meeting_changedate', ignore_recurrence=not update_recurrence)

        return True

    @api.model  # LUL TODO create multi
    def create(self, values):
        if not 'user_id' in values:  # Else bug with quick_create when we are filter on an other user
            values['user_id'] = self.env.user.id

        # created from calendar: try to create an activity on the related record
        if not values.get('activity_ids'):
            defaults = self.default_get(['activity_ids', 'res_model_id', 'res_id', 'user_id'])
            res_model_id = values.get('res_model_id', defaults.get('res_model_id'))
            res_id = values.get('res_id', defaults.get('res_id'))
            user_id = values.get('user_id', defaults.get('user_id'))
            if not defaults.get('activity_ids') and res_model_id and res_id:
                if hasattr(self.env[self.env['ir.model'].sudo().browse(res_model_id).model], 'activity_ids'):
                    meeting_activity_type = self.env['mail.activity.type'].search([('category', '=', 'meeting')], limit=1)
                    if meeting_activity_type:
                        activity_vals = {
                            'res_model_id': res_model_id,
                            'res_id': res_id,
                            'activity_type_id': meeting_activity_type.id,
                        }
                        if user_id:
                            activity_vals['user_id'] = user_id
                        values['activity_ids'] = [(0, 0, activity_vals)]

        if 'partner_ids' in values:
            values['attendee_ids'] = self._attendees_values(values['partner_ids'])

        recurrence_values = {field: values.pop(field) for field in self._get_recurrent_fields() if field in values}
        meeting = super(Meeting, self).create(values)

        if values.get('recurrency'):
            detached_events = meeting._apply_recurrence_values(recurrence_values)
            detached_events.active = False

        meeting.attendee_ids._send_mail_to_attendees('calendar.calendar_template_meeting_invitation')
        meeting._sync_activities(values)

        # Notify attendees if there is an alarm on the created event, as it might have changed their
        # next event notification
        if not self._context.get('dont_notify'):
            if len(meeting.alarm_ids) > 0:
                self.env['calendar.alarm_manager']._notify_next_alarm(meeting.partner_ids.ids)
        return meeting

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'date' in groupby:
            raise UserError(_('Group by date is not supported, use the calendar view instead.'))
        return super(Meeting, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    def unlink(self):
        # Get concerned attendees to notify them if there is an alarm on the unlinked events,
        # as it might have changed their next event notification
        events = self.filtered_domain([('alarm_ids', '!=', False)])
        partner_ids = events.mapped('partner_ids').ids

        result = super().unlink()

        # Notify the concerned attendees (must be done after removing the events)
        self.env['calendar.alarm_manager']._notify_next_alarm(partner_ids)
        return result

    def _range(self):
        self.ensure_one()
        return (self.start, self.stop)

    def _sync_activities(self, values):
        # update activities
        if self.mapped('activity_ids'):
            activity_values = {}
            if values.get('name'):
                activity_values['summary'] = values['name']
            if values.get('description'):
                activity_values['note'] = values['description']
            if values.get('start'):
                # self.start is a datetime UTC *only when the event is not allday*
                # activty.date_deadline is a date (No TZ, but should represent the day in which the user's TZ is)
                # See 72254129dbaeae58d0a2055cba4e4a82cde495b7 for the same issue, but elsewhere
                deadline = fields.Datetime.from_string(values['start'])
                user_tz = self.env.context.get('tz')
                if user_tz and not self.allday:
                    deadline = pytz.UTC.localize(deadline)
                    deadline = deadline.astimezone(pytz.timezone(user_tz))
                activity_values['date_deadline'] = deadline.date()
            if values.get('user_id'):
                activity_values['user_id'] = values['user_id']
            if activity_values.keys():
                self.mapped('activity_ids').write(activity_values)

    def change_attendee_status(self, status):
        attendee = self.attendee_ids.filtered(lambda x: x.partner_id == self.env.user.partner_id)
        if status == 'accepted':
            return attendee.do_accept()
        elif status == 'declined':
            return attendee.do_decline()
        else:
            return attendee.do_tentative()
