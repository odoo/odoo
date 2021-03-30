# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
import math
from uuid import uuid4
import logging
import pytz
from werkzeug.urls import url_join

from odoo import api, fields, models
from odoo import tools
from odoo.addons.base.models.res_partner import _tz_get
from odoo.addons.calendar.models.calendar_attendee import Attendee
from odoo.addons.calendar.models.calendar_recurrence import weekday_to_field, RRULE_TYPE_SELECTION, END_TYPE_SELECTION, MONTH_BY_SELECTION, WEEKDAY_SELECTION, BYDAY_SELECTION
from odoo.tools.translate import _
from odoo.tools.misc import get_lang
from odoo.tools import pycompat, html_escape
from odoo.exceptions import UserError, ValidationError, AccessError

_logger = logging.getLogger(__name__)

try:
    import vobject
except ImportError:
    _logger.warning("`vobject` Python module not found, iCal file generation disabled. Consider installing this module if you want to generate iCal files")
    vobject = None

SORT_ALIASES = {
    'start': 'sort_start',
    'start_date': 'sort_start',
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

    @api.model
    def _default_videocall_location(self):
        if self.env.context.get('calendar_no_videocall'):
            return False
        jitsi_url = self.env['ir.config_parameter'].sudo().get_param('website_jitsi.jitsi_server_domain', 'meet.jit.si')
        if not jitsi_url.startswith('http'):
            jitsi_url = 'https://' + jitsi_url
        return url_join(jitsi_url, 'odoo-%s' % (uuid4().hex[:12]))

    # description
    name = fields.Char('Meeting Subject', required=True)
    description = fields.Text('Description')
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user)
    partner_id = fields.Many2one(
        'res.partner', string='Responsible Contact', related='user_id.partner_id', readonly=True)
    location = fields.Char('Location', tracking=True, help="Location of Event")
    videocall_location = fields.Char('Join Video Call', default=_default_videocall_location)
    # visibility
    privacy = fields.Selection(
        [('public', 'Public'),
         ('private', 'Private'),
         ('confidential', 'Only internal users')],
        'Privacy', default='public', required=True,
        help="People to whom this event will be visible.")
    show_as = fields.Selection(
        [('free', 'Available'),
         ('busy', 'Busy')], 'Show as', default='busy', required=True,
        help="If the time is shown as 'busy', this event will be visible to other people with either the full \
        information or simply 'busy' written depending on its privacy. Use this option to let other people know \
        that you are unavailable during that period of time. \n If the time is shown as 'free', this event won't \
        be visible to other people at all. Use this option to let other people know that you are available during \
        that period of time.")
    is_highlighted = fields.Boolean(
        compute='_compute_is_highlighted', string='Is the Event Highlighted')
    # filtering
    active = fields.Boolean(
        'Active', default=True,
        help="If the active field is set to false, it will allow you to hide the event alarm information without removing it.")
    categ_ids = fields.Many2many(
        'calendar.event.type', 'meeting_category_rel', 'event_id', 'type_id', 'Tags')
    # timing
    start = fields.Datetime(
        'Start', required=True, tracking=True, default=fields.Date.today,
        help="Start date of an event, without time for full days events")
    stop = fields.Datetime(
        'Stop', required=True, tracking=True, default=lambda self: fields.Datetime.today() + timedelta(hours=1),
        compute='_compute_stop', readonly=False, store=True,
        help="Stop date of an event, without time for full days events")
    display_time = fields.Char('Event Time', compute='_compute_display_time')
    allday = fields.Boolean('All Day', default=False)
    start_date = fields.Date(
        'Start Date', store=True, tracking=True,
        compute='_compute_dates', inverse='_inverse_dates')
    stop_date = fields.Date(
        'End Date', store=True, tracking=True,
        compute='_compute_dates', inverse='_inverse_dates')
    duration = fields.Float('Duration', compute='_compute_duration', store=True, readonly=False)
    # linked document
    # LUL TODO use fields.Reference ?
    res_id = fields.Integer('Document ID')
    res_model_id = fields.Many2one('ir.model', 'Document Model', ondelete='cascade')
    res_model = fields.Char(
        'Document Model Name', related='res_model_id.model', readonly=True, store=True)
    # messaging
    activity_ids = fields.One2many('mail.activity', 'calendar_event_id', string='Activities')
    #redifine message_ids to remove autojoin to avoid search to crash in get_recurrent_ids
    message_ids = fields.One2many(auto_join=False)
    # attendees
    attendee_ids = fields.One2many(
        'calendar.attendee', 'event_id', 'Participant')
    attendee_status = fields.Selection(
        Attendee.STATE_SELECTION, string='Attendee Status', compute='_compute_attendee')
    partner_ids = fields.Many2many(
        'res.partner', 'calendar_event_res_partner_rel',
        string='Attendees', default=_default_partners)
    # alarms
    alarm_ids = fields.Many2many(
        'calendar.alarm', 'calendar_alarm_calendar_event_rel',
        string='Reminders', ondelete="restrict",
        help="Notifications sent to all attendees to remind of the meeting.")
    # RECURRENCE FIELD
    recurrency = fields.Boolean('Recurrent')
    recurrence_id = fields.Many2one(
        'calendar.recurrence', string="Recurrence Rule", index=True)
    follow_recurrence = fields.Boolean(default=False) # Indicates if an event follows the recurrence, i.e. is not an exception
    recurrence_update = fields.Selection([
        ('self_only', "This event"),
        ('future_events', "This and following events"),
        ('all_events', "All events"),
    ], store=False, copy=False, default='self_only',
       help="Choose what to do with other events in the recurrence. Updating All Events is not allowed when dates or time is modified")
    # Those field are pseudo-related fields of recurrence_id.
    # They can't be "real" related fields because it should work at record creation
    # when recurrence_id is not created yet.
    # If some of these fields are set and recurrence_id does not exists,
    # a `calendar.recurrence.rule` will be dynamically created.
    rrule = fields.Char('Recurrent Rule', compute='_compute_recurrence', readonly=False)
    rrule_type = fields.Selection(RRULE_TYPE_SELECTION, string='Recurrence',
                                  help="Let the event automatically repeat at that interval",
                                  compute='_compute_recurrence', readonly=False)
    event_tz = fields.Selection(
        _tz_get, string='Timezone', compute='_compute_recurrence', readonly=False)
    end_type = fields.Selection(
        END_TYPE_SELECTION, string='Recurrence Termination',
        compute='_compute_recurrence', readonly=False)
    interval = fields.Integer(
        string='Repeat Every', compute='_compute_recurrence', readonly=False,
        help="Repeat every (Days/Week/Month/Year)")
    count = fields.Integer(
        string='Repeat', help="Repeat x times", compute='_compute_recurrence', readonly=False)
    mon = fields.Boolean(compute='_compute_recurrence', readonly=False)
    tue = fields.Boolean(compute='_compute_recurrence', readonly=False)
    wed = fields.Boolean(compute='_compute_recurrence', readonly=False)
    thu = fields.Boolean(compute='_compute_recurrence', readonly=False)
    fri = fields.Boolean(compute='_compute_recurrence', readonly=False)
    sat = fields.Boolean(compute='_compute_recurrence', readonly=False)
    sun = fields.Boolean(compute='_compute_recurrence', readonly=False)
    month_by = fields.Selection(
        MONTH_BY_SELECTION, string='Option', compute='_compute_recurrence', readonly=False)
    day = fields.Integer('Date of month', compute='_compute_recurrence', readonly=False)
    weekday = fields.Selection(WEEKDAY_SELECTION, compute='_compute_recurrence', readonly=False)
    byday = fields.Selection(BYDAY_SELECTION, compute='_compute_recurrence', readonly=False)
    until = fields.Date(compute='_compute_recurrence', readonly=False)

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

    def _compute_display_time(self):
        for meeting in self:
            meeting.display_time = self._get_display_time(meeting.start, meeting.stop, meeting.duration, meeting.allday)

    @api.depends('allday', 'start', 'stop')
    def _compute_dates(self):
        """ Adapt the value of start_date(time)/stop_date(time)
            according to start/stop fields and allday. Also, compute
            the duration for not allday meeting ; otherwise the
            duration is set to zero, since the meeting last all the day.
        """
        for meeting in self:
            if meeting.allday and meeting.start and meeting.stop:
                meeting.start_date = meeting.start.date()
                meeting.stop_date = meeting.stop.date()
            else:
                meeting.start_date = False
                meeting.stop_date = False

    @api.depends('stop', 'start')
    def _compute_duration(self):
        for event in self:
            event.duration = self._get_duration(event.start, event.stop)

    @api.depends('start', 'duration')
    def _compute_stop(self):
        # stop and duration fields both depends on the start field.
        # But they also depends on each other.
        # When start is updated, we want to update the stop datetime based on
        # the *current* duration. In other words, we want: change start => keep the duration fixed and
        # recompute stop accordingly.
        # However, while computing stop, duration is marked to be recomputed. Calling `event.duration` would trigger
        # its recomputation. To avoid this we manually mark the field as computed.
        duration_field = self._fields['duration']
        self.env.remove_to_compute(duration_field, self)
        for event in self:
            # Round the duration (in hours) to the minute to avoid weird situations where the event
            # stops at 4:19:59, later displayed as 4:19.
            event.stop = event.start + timedelta(minutes=round((event.duration or 1.0) * 60))
            if event.allday:
                event.stop -= timedelta(seconds=1)

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

    def _compute_attendee(self):
        for meeting in self:
            attendee = next(
                (attendee for attendee in self.attendee_ids
                 if attendee.partner_id == self.env.user.partner_id),
                self.env['calendar.attendee']
            )
            meeting.attendee_status = attendee.state if attendee else 'needsAction'

    @api.constrains('start', 'stop', 'start_date', 'stop_date')
    def _check_closing_date(self):
        for meeting in self:
            if not meeting.allday and meeting.start and meeting.stop and meeting.stop < meeting.start:
                raise ValidationError(
                    _('The ending date and time cannot be earlier than the starting date and time.') + '\n' +
                    _("Meeting '%(name)s' starts '%(start_datetime)s' and ends '%(end_datetime)s'",
                      name=meeting.name,
                      start_datetime=meeting.start,
                      end_datetime=meeting.stop
                    )
                )
            if meeting.allday and meeting.start_date and meeting.stop_date and meeting.stop_date < meeting.start_date:
                raise ValidationError(
                    _('The ending date cannot be earlier than the starting date.') + '\n' +
                    _("Meeting '%(name)s' starts '%(start_datetime)s' and ends '%(end_datetime)s'",
                      name=meeting.name,
                      start_datetime=meeting.start,
                      end_datetime=meeting.stop
                    )
                )

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

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [  # Else bug with quick_create when we are filter on an other user
            dict(vals, user_id=self.env.user.id) if not 'user_id' in vals else vals
            for vals in vals_list
        ]

        for values in vals_list:
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

        vals_list = [
            dict(vals, attendee_ids=self._attendees_values(vals['partner_ids'])) if 'partner_ids' in vals else vals
            for vals in vals_list
        ]
        recurrence_fields = self._get_recurrent_fields()
        recurring_vals = [vals for vals in vals_list if vals.get('recurrency')]
        other_vals = [vals for vals in vals_list if not vals.get('recurrency')]
        events = super().create(other_vals)

        for vals in recurring_vals:

            recurrence_values = {field: vals.pop(field) for field in recurrence_fields if field in vals}
            vals['follow_recurrence'] = True
            event = super().create(vals)
            events |= event
            if vals.get('recurrency'):
                detached_events = event._apply_recurrence_values(recurrence_values)
                detached_events.active = False

        events.filtered(lambda event: event.start > fields.Datetime.now()).attendee_ids._send_mail_to_attendees(
            self.env.ref('calendar.calendar_template_meeting_invitation', raise_if_not_found=False)
        )
        events._sync_activities(fields={f for vals in vals_list for f in vals.keys()})

        events._setup_alarms()

        return events

    def read(self, fields=None, load='_classic_read'):
        def hide(field, value):
            """
            :param field: field name
            :param value: field value
            :return: obfuscated field value
            """
            if field in {'name', 'display_name'}:
                return _('Busy')
            return [] if isinstance(value, list) else False

        def split_privacy(events):
            """
            :param events: list of event values (dict)
            :return: tuple(private events, public events)
            """
            private = [event for event in events if event.get('privacy') == 'private']
            public = [event for event in events if event.get('privacy') != 'private']
            return private, public

        def my_events(events):
            """
            :param events: list of event values (dict)
            :return: tuple(my events, other events)
            """
            my = [event for event in events if event.get('user_id') and event.get('user_id')[0] == self.env.uid]
            others = [event for event in events if not event.get('user_id') or event.get('user_id')[0] != self.env.uid]
            return my, others

        def obfuscated(events):
            """
            :param events: list of event values (dict)
            :return: events with private field values obfuscated
            """
            public_fields = self._get_public_fields()
            return [{
                field: hide(field, value) if field not in public_fields else value
                for field, value in event.items()
            } for event in events]

        events = super().read(fields=fields + ['privacy', 'user_id'], load=load)
        private_events, public_events = split_privacy(events)
        my_private_events, others_private_events = my_events(private_events)

        return public_events + my_private_events + obfuscated(others_private_events)

    def write(self, values):
        detached_events = self.env['calendar.event']
        recurrence_update_setting = values.pop('recurrence_update', None)
        update_recurrence = recurrence_update_setting in ('all_events', 'future_events') and len(self) == 1
        break_recurrence = values.get('recurrency') is False

        if 'partner_ids' in values:
            values['attendee_ids'] = self._attendees_values(values['partner_ids'])

        if (not recurrence_update_setting or recurrence_update_setting == 'self_only' and len(self) == 1) and 'follow_recurrence' not in values:
            if any({field: values.get(field) for field in self.env['calendar.event']._get_time_fields() if field in values}):
                values['follow_recurrence'] = False

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
            self._sync_activities(fields=values.keys())

        if recurrence_update_setting != 'self_only' and not break_recurrence:
            detached_events |= self._apply_recurrence_values(recurrence_values, future=recurrence_update_setting == 'future_events')

        (detached_events & self).active = False
        (detached_events - self).with_context(archive_on_error=True).unlink()

        self._setup_alarms()

        current_attendees = self.filtered('active').attendee_ids
        if 'partner_ids' in values:
            (current_attendees - previous_attendees)._send_mail_to_attendees(
                self.env.ref('calendar.calendar_template_meeting_invitation', raise_if_not_found=False)
            )
        if 'start' in values:
            start_date = fields.Datetime.to_datetime(values.get('start'))
            # Only notify on future events
            if start_date and start_date >= fields.Datetime.now():
                (current_attendees & previous_attendees).with_context(
                    calendar_template_ignore_recurrence=not update_recurrence
                )._send_mail_to_attendees(
                    self.env.ref('calendar.calendar_template_meeting_changedate', raise_if_not_found=False)
                )

        return True

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        groupby = [groupby] if isinstance(groupby, str) else groupby
        grouped_fields = set(group_field.split(':')[0] for group_field in groupby)
        private_fields = grouped_fields - self._get_public_fields()
        if not self.env.su and private_fields:
            raise AccessError(_(
                "Grouping by %s is not allowed.",
                ', '.join([self._fields[field_name].string for field_name in private_fields])
            ))
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

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------

    def action_open_calendar_event(self):
        if self.res_model and self.res_id:
            return self.env[self.res_model].browse(self.res_id).get_formview_action()
        return False

    def action_sendmail(self):
        email = self.env.user.email
        if email:
            for meeting in self:
                meeting.attendee_ids._send_mail_to_attendees(
                    self.env.ref('calendar.calendar_template_meeting_invitation', raise_if_not_found=False)
                )
        return True

    def action_mass_mailing(self):
        partners_ids = self.mapped('partner_ids')
        if not partners_ids:
            raise UserError(_("There are no attendees on these events"))
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        default_partners = partners_ids and partners_ids.ids
        compose_ctx = dict(
            default_use_template=False,
            default_composition_mode='mass_mail',
            default_partner_ids=default_partners,
            default_subject=_("Event update")
        )
        return {
            'name': _('Contact Attendees'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': compose_ctx,
        }

    # ------------------------------------------------------------
    # MAILING
    # ------------------------------------------------------------

    def _sync_activities(self, fields):
        # update activities
        for event in self:
            if event.activity_ids:
                activity_values = {}
                if 'name' in fields:
                    activity_values['summary'] = event.name
                if 'description' in fields:
                    activity_values['note'] = tools.plaintext2html(event.description)
                if 'start' in fields:
                    # self.start is a datetime UTC *only when the event is not allday*
                    # activty.date_deadline is a date (No TZ, but should represent the day in which the user's TZ is)
                    # See 72254129dbaeae58d0a2055cba4e4a82cde495b7 for the same issue, but elsewhere
                    deadline = event.start
                    user_tz = self.env.context.get('tz')
                    if user_tz and not event.allday:
                        deadline = pytz.utc.localize(deadline)
                        deadline = deadline.astimezone(pytz.timezone(user_tz))
                    activity_values['date_deadline'] = deadline.date()
                if 'user_id' in fields:
                    activity_values['user_id'] = event.user_id.id
                if activity_values.keys():
                    event.activity_ids.write(activity_values)

    # ------------------------------------------------------------
    # ALARMS
    # ------------------------------------------------------------

    def _get_trigger_alarm_types(self):
        return ['email']

    def _setup_alarms(self):
        """ Schedule cron triggers for future events """
        cron = self.env.ref('calendar.ir_cron_scheduler_alarm')
        alarm_manager = self.env['calendar.alarm_manager']
        alarm_types = self._get_trigger_alarm_types()

        for event in self:
            for alarm in (alarm for alarm in event.alarm_ids if alarm.alarm_type in alarm_types):
                at = event.start - timedelta(minutes=alarm.duration_minutes)
                if not cron.lastcall or at > cron.lastcall:
                    # Don't trigger for past alarms, they would be skipped by design
                    cron._trigger(at=at)
            if any(alarm.alarm_type == 'notification' for alarm in event.alarm_ids):
                alarm_manager._notify_next_alarm(event.partner_ids.ids)

    # ------------------------------------------------------------
    # RECURRENCY
    # ------------------------------------------------------------

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
        self.write({'recurrency': True, 'follow_recurrence': True})
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
        recurrences_to_unlink.with_context(archive_on_error=True).unlink()
        return detached_events - self

    # ------------------------------------------------------------
    # MANAGEMENT
    # ------------------------------------------------------------

    def change_attendee_status(self, status):
        attendee = self.attendee_ids.filtered(lambda x: x.partner_id == self.env.user.partner_id)
        if status == 'accepted':
            return attendee.do_accept()
        if status == 'declined':
            return attendee.do_decline()
        return attendee.do_tentative()

    def find_partner_customer(self):
        self.ensure_one()
        return next(
            (attendee.partner_id for attendee in self.attendee_ids.sorted('create_date')
             if attendee.partner_id != self.user_id.partner_id),
            self.env['calendar.attendee']
        )

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

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

    def _range(self):
        self.ensure_one()
        return (self.start, self.stop)

    def get_display_time_tz(self, tz=False):
        """ get the display_time of the meeting, forcing the timezone. This method is called from email template, to not use sudo(). """
        self.ensure_one()
        if tz:
            self = self.with_context(tz=tz)
        return self._get_display_time(self.start, self.stop, self.duration, self.allday)

    def _get_ics_file(self):
        """ Returns iCalendar file for the event invitation.
            :returns a dict of .ics file content for each meeting
        """
        result = {}

        def ics_datetime(idate, allday=False):
            if idate:
                if allday:
                    return idate
                return idate.replace(tzinfo=pytz.timezone('UTC'))
            return False

        if not vobject:
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
            display_time = _("All Day, %(day)s", day=date_str)
        elif zduration < 24:
            duration = date + timedelta(minutes=round(zduration*60))
            duration_time = to_text(duration.strftime(format_time))
            display_time = _(
                u"%(day)s at (%(start)s To %(end)s) (%(timezone)s)",
                day=date_str,
                start=time_str,
                end=duration_time,
                timezone=timezone,
            )
        else:
            dd_date = to_text(date_deadline.strftime(format_date))
            dd_time = to_text(date_deadline.strftime(format_time))
            display_time = _(
                u"%(date_start)s at %(time_start)s To\n %(date_end)s at %(time_end)s (%(timezone)s)",
                date_start=date_str,
                time_start=time_str,
                date_end=dd_date,
                time_end=dd_time,
                timezone=timezone,
            )
        return display_time

    def _get_duration(self, start, stop):
        """ Get the duration value between the 2 given dates. """
        if not start or not stop:
            return 0
        duration = (stop - start).total_seconds() / 3600
        return round(duration, 2)

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
                'interval', 'count', 'end_type', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat',
                'sun', 'day', 'weekday'}

    @api.model
    def _get_time_fields(self):
        return {'start', 'stop', 'start_date', 'stop_date'}

    @api.model
    def _get_custom_fields(self):
        all_fields = self.fields_get(attributes=['manual'])
        return {fname for fname in all_fields if all_fields[fname]['manual']}

    @api.model
    def _get_public_fields(self):
        return self._get_recurrent_fields() | self._get_time_fields() | self._get_custom_fields() | {
            'id', 'active', 'allday',
            'duration', 'user_id', 'interval',
            'count', 'rrule', 'recurrence_id', 'show_as', 'privacy'}

    def description_to_html_lines(self):
        """ Description could contain some structure content, depending on
        its use. Notably appointment could add some structured data in it
        in addition to free text. Purpose of this method is to generate a
        simple html.

        Input (self.description) example:
Some free text salespeople added
as multi line
 * Mobile: +320475000000
 * Email: my.email@test.example.com
 * SingleLine: answer
 * MultiLine:
Answer1
Answer2
Answer3
 * Dropdown: answer
 * Radio: answer
 * Checkboxes: answer1, answer2
Some free text salespeople added
as multi line

        Output: a list of items[
'Some free text salespeople added<br />as multi line',
'Mobile: +320475000000',
'Email: my.email@test.example.com',
'SingleLine: answer',
'MultiLine:<br />Answer1<br />Answer2<br />Answer3',
'Dropdown: answer',
'Radio: answer',
'Checkboxes: answer1, answer2',
'Some free text salespeople added<br .>as multi line']

        Each item of returned list is escaped so that only our intended <br />
        are html tags. It should therefore be safe.
        """

        final_lines = []
        parsed_lines = []
        for line in self.description.split('\n'):
            if not line.strip():
                continue
            # new line
            if line.startswith(' *'):
                if parsed_lines:
                    final_lines.append('<br />'.join(html_escape(line) for line in parsed_lines))
                parsed_lines = [line.lstrip(' *')]
            else:
                parsed_lines.append(line)
        if parsed_lines:
            final_lines.append('<br />'.join(html_escape(line) for line in parsed_lines))
        return final_lines
