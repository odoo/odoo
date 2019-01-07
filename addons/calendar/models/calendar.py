# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

import babel.dates
import collections
from datetime import datetime, timedelta, MAXYEAR
from dateutil import parser
from dateutil import rrule
from dateutil.relativedelta import relativedelta
import logging
from operator import itemgetter
import pytz
import re
import time
import uuid

from odoo import api, fields, models
from odoo import tools
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, pycompat
from odoo.exceptions import UserError, ValidationError


_logger = logging.getLogger(__name__)

VIRTUALID_DATETIME_FORMAT = "%Y%m%d%H%M%S"


def calendar_id2real_id(calendar_id=None, with_date=False):
    """ Convert a "virtual/recurring event id" (type string) into a real event id (type int).
        E.g. virtual/recurring event id is 4-20091201100000, so it will return 4.
        :param calendar_id: id of calendar
        :param with_date: if a value is passed to this param it will return dates based on value of withdate + calendar_id
        :return: real event id
    """
    if calendar_id and isinstance(calendar_id, pycompat.string_types):
        res = [bit for bit in calendar_id.split('-') if bit]
        if len(res) == 2:
            real_id = res[0]
            if with_date:
                real_date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT, time.strptime(res[1], VIRTUALID_DATETIME_FORMAT))
                start = datetime.strptime(real_date, DEFAULT_SERVER_DATETIME_FORMAT)
                end = start + timedelta(hours=with_date)
                return (int(real_id), real_date, end.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            return int(real_id)
    return calendar_id and int(calendar_id) or calendar_id


def get_real_ids(ids):
    if isinstance(ids, (pycompat.string_types, pycompat.integer_types)):
        return calendar_id2real_id(ids)

    if isinstance(ids, (list, tuple)):
        return [calendar_id2real_id(_id) for _id in ids]


def real_id2calendar_id(record_id, date):
    return '%s-%s' % (record_id, date.strftime(VIRTUALID_DATETIME_FORMAT))

def any_id2key(record_id):
    """ Creates a (real_id: int, thing: str) pair which allows ordering mixed
    collections of real and virtual events.

    The first item of the pair is the event's real id, the second one is
    either an empty string (for real events) or the datestring (for virtual
    ones)

    :param record_id:
    :type record_id: int | str
    :rtype: (int, str)
    """
    if isinstance(record_id, pycompat.integer_types):
        return record_id, u''

    (real_id, virtual_id) = record_id.split('-')
    return int(real_id), virtual_id

def is_calendar_id(record_id):
    return len(str(record_id).split('-')) != 1


SORT_ALIASES = {
    'start': 'sort_start',
    'start_date': 'sort_start',
    'start_datetime': 'sort_start',
}
def sort_remap(f):
    return SORT_ALIASES.get(f, f)


class Contacts(models.Model):
    _name = 'calendar.contacts'

    user_id = fields.Many2one('res.users', 'Me', required=True, default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', 'Employee', required=True)
    active = fields.Boolean('Active', default=True)

    _sql_constraints = [
        ('user_id_partner_id_unique', 'UNIQUE(user_id,partner_id)', 'An user cannot have twice the same contact.')
    ]

    @api.model
    def unlink_from_partner_id(self, partner_id):
        return self.search([('partner_id', '=', partner_id)]).unlink()


class Attendee(models.Model):
    """ Calendar Attendee Information """

    _name = 'calendar.attendee'
    _rec_name = 'common_name'
    _description = 'Attendee information'

    def _default_access_token(self):
        return uuid.uuid4().hex

    STATE_SELECTION = [
        ('needsAction', 'Needs Action'),
        ('tentative', 'Uncertain'),
        ('declined', 'Declined'),
        ('accepted', 'Accepted'),
    ]

    state = fields.Selection(STATE_SELECTION, string='Status', readonly=True, default='needsAction',
        help="Status of the attendee's participation")
    common_name = fields.Char('Common name', compute='_compute_common_name', store=True)
    partner_id = fields.Many2one('res.partner', 'Contact', readonly="True")
    email = fields.Char('Email', help="Email of Invited Person")
    availability = fields.Selection([('free', 'Free'), ('busy', 'Busy')], 'Free/Busy', readonly="True")
    access_token = fields.Char('Invitation Token', default=_default_access_token)
    event_id = fields.Many2one('calendar.event', 'Meeting linked', ondelete='cascade')

    @api.depends('partner_id', 'partner_id.name', 'email')
    def _compute_common_name(self):
        for attendee in self:
            attendee.common_name = attendee.partner_id.name or attendee.email

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """ Make entry on email and availability on change of partner_id field. """
        self.email = self.partner_id.email

    @api.model
    def create(self, values):
        if not values.get("email") and values.get("common_name"):
            common_nameval = values.get("common_name").split(':')
            email = [x for x in common_nameval if '@' in x] # TODO JEM : should be refactored
            values['email'] = email and email[0] or ''
            values['common_name'] = values.get("common_name")
        return super(Attendee, self).create(values)

    @api.multi
    def copy(self, default=None):
        raise UserError(_('You cannot duplicate a calendar attendee.'))

    @api.multi
    def _send_mail_to_attendees(self, template_xmlid, force_send=False):
        """ Send mail for event invitation to event attendees.
            :param template_xmlid: xml id of the email template to use to send the invitation
            :param force_send: if set to True, the mail(s) will be sent immediately (instead of the next queue processing)
        """
        res = False

        if self.env['ir.config_parameter'].sudo().get_param('calendar.block_mail') or self._context.get("no_mail_to_attendees"):
            return res

        calendar_view = self.env.ref('calendar.view_calendar_event_calendar')
        invitation_template = self.env.ref(template_xmlid)

        # get ics file for all meetings
        ics_files = self.mapped('event_id').get_ics_file()

        # prepare rendering context for mail template
        colors = {
            'needsAction': 'grey',
            'accepted': 'green',
            'tentative': '#FFFF00',
            'declined': 'red'
        }
        rendering_context = dict(self._context)
        rendering_context.update({
            'color': colors,
            'action_id': self.env['ir.actions.act_window'].search([('view_id', '=', calendar_view.id)], limit=1).id,
            'dbname': self._cr.dbname,
            'base_url': self.env['ir.config_parameter'].sudo().get_param('web.base.url', default='http://localhost:8069')
        })
        invitation_template = invitation_template.with_context(rendering_context)

        # send email with attachments
        mails_to_send = self.env['mail.mail']
        for attendee in self:
            if attendee.email or attendee.partner_id.email:
                # FIXME: is ics_file text or bytes?
                ics_file = ics_files.get(attendee.event_id.id)
                mail_id = invitation_template.send_mail(attendee.id)

                vals = {}
                if ics_file:
                    vals['attachment_ids'] = [(0, 0, {'name': 'invitation.ics',
                                                      'mimetype': 'text/calendar',
                                                      'datas_fname': 'invitation.ics',
                                                      'datas': base64.b64encode(ics_file)})]
                vals['model'] = None  # We don't want to have the mail in the tchatter while in queue!
                vals['res_id'] = False
                current_mail = self.env['mail.mail'].browse(mail_id)
                current_mail.mail_message_id.write(vals)
                mails_to_send |= current_mail

        if force_send and mails_to_send:
            res = mails_to_send.send()

        return res

    @api.multi
    def do_tentative(self):
        """ Makes event invitation as Tentative. """
        return self.write({'state': 'tentative'})

    @api.multi
    def do_accept(self):
        """ Marks event invitation as Accepted. """
        result = self.write({'state': 'accepted'})
        for attendee in self:
            attendee.event_id.message_post(body=_("%s has accepted invitation") % (attendee.common_name), subtype="calendar.subtype_invitation")
        return result

    @api.multi
    def do_decline(self):
        """ Marks event invitation as Declined. """
        res = self.write({'state': 'declined'})
        for attendee in self:
            attendee.event_id.message_post(body=_("%s has declined invitation") % (attendee.common_name), subtype="calendar.subtype_invitation")
        return res


class AlarmManager(models.AbstractModel):

    _name = 'calendar.alarm_manager'

    def get_next_potential_limit_alarm(self, alarm_type, seconds=None, partner_id=None):
        result = {}
        delta_request = """
            SELECT
                rel.calendar_event_id, max(alarm.duration_minutes) AS max_delta,min(alarm.duration_minutes) AS min_delta
            FROM
                calendar_alarm_calendar_event_rel AS rel
            LEFT JOIN calendar_alarm AS alarm ON alarm.id = rel.calendar_alarm_id
            WHERE alarm.type = %s
            GROUP BY rel.calendar_event_id
        """
        base_request = """
                    SELECT
                        cal.id,
                        cal.start - interval '1' minute  * calcul_delta.max_delta AS first_alarm,
                        CASE
                            WHEN cal.recurrency THEN cal.final_date - interval '1' minute  * calcul_delta.min_delta
                            ELSE cal.stop - interval '1' minute  * calcul_delta.min_delta
                        END as last_alarm,
                        cal.start as first_event_date,
                        CASE
                            WHEN cal.recurrency THEN cal.final_date
                            ELSE cal.stop
                        END as last_event_date,
                        calcul_delta.min_delta,
                        calcul_delta.max_delta,
                        cal.rrule AS rule
                    FROM
                        calendar_event AS cal
                    RIGHT JOIN calcul_delta ON calcul_delta.calendar_event_id = cal.id
             """

        filter_user = """
                RIGHT JOIN calendar_event_res_partner_rel AS part_rel ON part_rel.calendar_event_id = cal.id
                    AND part_rel.res_partner_id = %s
        """

        # Add filter on alarm type
        tuple_params = (alarm_type,)

        # Add filter on partner_id
        if partner_id:
            base_request += filter_user
            tuple_params += (partner_id, )

        # Upper bound on first_alarm of requested events
        first_alarm_max_value = ""
        if seconds is None:
            # first alarm in the future + 3 minutes if there is one, now otherwise
            first_alarm_max_value = """
                COALESCE((SELECT MIN(cal.start - interval '1' minute  * calcul_delta.max_delta)
                FROM calendar_event cal
                RIGHT JOIN calcul_delta ON calcul_delta.calendar_event_id = cal.id
                WHERE cal.start - interval '1' minute  * calcul_delta.max_delta > now() at time zone 'utc'
            ) + interval '3' minute, now() at time zone 'utc')"""
        else:
            # now + given seconds
            first_alarm_max_value = "(now() at time zone 'utc' + interval '%s' second )"
            tuple_params += (seconds,)

        self._cr.execute("""
                    WITH calcul_delta AS (%s)
                    SELECT *
                        FROM ( %s WHERE cal.active = True ) AS ALL_EVENTS
                       WHERE ALL_EVENTS.first_alarm < %s
                         AND ALL_EVENTS.last_event_date > (now() at time zone 'utc')
                   """ % (delta_request, base_request, first_alarm_max_value), tuple_params)

        for event_id, first_alarm, last_alarm, first_meeting, last_meeting, min_duration, max_duration, rule in self._cr.fetchall():
            result[event_id] = {
                'event_id': event_id,
                'first_alarm': first_alarm,
                'last_alarm': last_alarm,
                'first_meeting': first_meeting,
                'last_meeting': last_meeting,
                'min_duration': min_duration,
                'max_duration': max_duration,
                'rrule': rule
            }

        return result

    def do_check_alarm_for_one_date(self, one_date, event, event_maxdelta, in_the_next_X_seconds, alarm_type, after=False, missing=False):
        """ Search for some alarms in the interval of time determined by some parameters (after, in_the_next_X_seconds, ...)
            :param one_date: date of the event to check (not the same that in the event browse if recurrent)
            :param event: Event browse record
            :param event_maxdelta: biggest duration from alarms for this event
            :param in_the_next_X_seconds: looking in the future (in seconds)
            :param after: if not False: will return alert if after this date (date as string - todo: change in master)
            :param missing: if not False: will return alert even if we are too late
            :param notif: Looking for type notification
            :param mail: looking for type email
        """
        result = []
        # TODO: remove event_maxdelta and if using it
        if one_date - timedelta(minutes=(missing and 0 or event_maxdelta)) < datetime.now() + timedelta(seconds=in_the_next_X_seconds):  # if an alarm is possible for this date
            for alarm in event.alarm_ids:
                if alarm.type == alarm_type and \
                    one_date - timedelta(minutes=(missing and 0 or alarm.duration_minutes)) < datetime.now() + timedelta(seconds=in_the_next_X_seconds) and \
                        (not after or one_date - timedelta(minutes=alarm.duration_minutes) > fields.Datetime.from_string(after)):
                        alert = {
                            'alarm_id': alarm.id,
                            'event_id': event.id,
                            'notify_at': one_date - timedelta(minutes=alarm.duration_minutes),
                        }
                        result.append(alert)
        return result

    @api.model
    def get_next_mail(self):
        now = fields.Datetime.now()
        last_notif_mail = self.env['ir.config_parameter'].sudo().get_param('calendar.last_notif_mail', default=now)

        try:
            cron = self.env['ir.model.data'].sudo().get_object('calendar', 'ir_cron_scheduler_alarm')
        except ValueError:
            _logger.error("Cron for " + self._name + " can not be identified !")
            return False

        interval_to_second = {
            "weeks": 7 * 24 * 60 * 60,
            "days": 24 * 60 * 60,
            "hours": 60 * 60,
            "minutes": 60,
            "seconds": 1
        }

        if cron.interval_type not in interval_to_second:
            _logger.error("Cron delay can not be computed !")
            return False

        cron_interval = cron.interval_number * interval_to_second[cron.interval_type]

        all_meetings = self.get_next_potential_limit_alarm('email', seconds=cron_interval)

        for meeting in self.env['calendar.event'].browse(all_meetings):
            max_delta = all_meetings[meeting.id]['max_duration']

            if meeting.recurrency:
                at_least_one = False
                last_found = False
                for one_date in meeting._get_recurrent_date_by_event():
                    in_date_format = one_date.replace(tzinfo=None)
                    last_found = self.do_check_alarm_for_one_date(in_date_format, meeting, max_delta, 0, 'email', after=last_notif_mail, missing=True)
                    for alert in last_found:
                        self.do_mail_reminder(alert)
                        at_least_one = True  # if it's the first alarm for this recurrent event
                    if at_least_one and not last_found:  # if the precedent event had an alarm but not this one, we can stop the search for this event
                        break
            else:
                in_date_format = datetime.strptime(meeting.start, DEFAULT_SERVER_DATETIME_FORMAT)
                last_found = self.do_check_alarm_for_one_date(in_date_format, meeting, max_delta, 0, 'email', after=last_notif_mail, missing=True)
                for alert in last_found:
                    self.do_mail_reminder(alert)
        self.env['ir.config_parameter'].sudo().set_param('calendar.last_notif_mail', now)

    @api.model
    def get_next_notif(self):
        partner = self.env.user.partner_id
        all_notif = []

        if not partner:
            return []

        all_meetings = self.get_next_potential_limit_alarm('notification', partner_id=partner.id)
        time_limit = 3600 * 24  # return alarms of the next 24 hours
        for event_id in all_meetings:
            max_delta = all_meetings[event_id]['max_duration']
            meeting = self.env['calendar.event'].browse(event_id)
            if meeting.recurrency:
                b_found = False
                last_found = False
                for one_date in meeting._get_recurrent_date_by_event():
                    in_date_format = one_date.replace(tzinfo=None)
                    last_found = self.do_check_alarm_for_one_date(in_date_format, meeting, max_delta, time_limit, 'notification', after=partner.calendar_last_notif_ack)
                    if last_found:
                        for alert in last_found:
                            all_notif.append(self.do_notif_reminder(alert))
                        if not b_found:  # if it's the first alarm for this recurrent event
                            b_found = True
                    if b_found and not last_found:  # if the precedent event had alarm but not this one, we can stop the search fot this event
                        break
            else:
                in_date_format = fields.Datetime.from_string(meeting.start)
                last_found = self.do_check_alarm_for_one_date(in_date_format, meeting, max_delta, time_limit, 'notification', after=partner.calendar_last_notif_ack)
                if last_found:
                    for alert in last_found:
                        all_notif.append(self.do_notif_reminder(alert))
        return all_notif

    def do_mail_reminder(self, alert):
        meeting = self.env['calendar.event'].browse(alert['event_id'])
        alarm = self.env['calendar.alarm'].browse(alert['alarm_id'])

        result = False
        if alarm.type == 'email':
            result = meeting.attendee_ids.filtered(lambda r: r.state != 'declined')._send_mail_to_attendees('calendar.calendar_template_meeting_reminder', force_send=True)
        return result

    def do_notif_reminder(self, alert):
        alarm = self.env['calendar.alarm'].browse(alert['alarm_id'])
        meeting = self.env['calendar.event'].browse(alert['event_id'])

        if alarm.type == 'notification':
            message = meeting.display_time

            delta = alert['notify_at'] - datetime.now()
            delta = delta.seconds + delta.days * 3600 * 24

            return {
                'event_id': meeting.id,
                'title': meeting.name,
                'message': message,
                'timer': delta,
                'notify_at': fields.Datetime.to_string(alert['notify_at']),
            }

    def notify_next_alarm(self, partner_ids):
        """ Sends through the bus the next alarm of given partners """
        notifications = []
        users = self.env['res.users'].search([('partner_id', 'in', tuple(partner_ids))])
        for user in users:
            notif = self.sudo(user.id).get_next_notif()
            notifications.append([(self._cr.dbname, 'calendar.alarm', user.partner_id.id), notif])
        if len(notifications) > 0:
            self.env['bus.bus'].sendmany(notifications)


class Alarm(models.Model):
    _name = 'calendar.alarm'
    _description = 'Event alarm'

    @api.depends('interval', 'duration')
    def _compute_duration_minutes(self):
        for alarm in self:
            if alarm.interval == "minutes":
                alarm.duration_minutes = alarm.duration
            elif alarm.interval == "hours":
                alarm.duration_minutes = alarm.duration * 60
            elif alarm.interval == "days":
                alarm.duration_minutes = alarm.duration * 60 * 24
            else:
                alarm.duration_minutes = 0

    _interval_selection = {'minutes': 'Minute(s)', 'hours': 'Hour(s)', 'days': 'Day(s)'}

    name = fields.Char('Name', translate=True, required=True)
    type = fields.Selection([('notification', 'Notification'), ('email', 'Email')], 'Type', required=True, default='email')
    duration = fields.Integer('Remind Before', required=True, default=1)
    interval = fields.Selection(list(_interval_selection.items()), 'Unit', required=True, default='hours')
    duration_minutes = fields.Integer('Duration in minutes', compute='_compute_duration_minutes', store=True, help="Duration in minutes")

    @api.onchange('duration', 'interval')
    def _onchange_duration_interval(self):
        display_interval = self._interval_selection.get(self.interval, '')
        self.name = str(self.duration) + ' ' + display_interval

    def _update_cron(self):
        try:
            cron = self.env['ir.model.data'].sudo().get_object('calendar', 'ir_cron_scheduler_alarm')
        except ValueError:
            return False
        return cron.toggle(model=self._name, domain=[('type', '=', 'email')])

    @api.model
    def create(self, values):
        result = super(Alarm, self).create(values)
        self._update_cron()
        return result

    @api.multi
    def write(self, values):
        result = super(Alarm, self).write(values)
        self._update_cron()
        return result

    @api.multi
    def unlink(self):
        result = super(Alarm, self).unlink()
        self._update_cron()
        return result


class MeetingType(models.Model):

    _name = 'calendar.event.type'
    _description = 'Meeting Type'

    name = fields.Char('Name', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class Meeting(models.Model):
    """ Model for Calendar Event

        Special context keys :
            - `no_mail_to_attendees` : disabled sending email to attendees when creating/editing a meeting
    """

    _name = 'calendar.event'
    _description = "Event"
    _order = "id desc"
    _inherit = ["mail.thread"]

    @api.model
    def default_get(self, fields):
        # super default_model='crm.lead' for easier use in adddons
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

    @api.multi
    def _get_recurrent_dates_by_event(self):
        """ Get recurrent start and stop dates based on Rule string"""
        start_dates = self._get_recurrent_date_by_event(date_field='start')
        stop_dates = self._get_recurrent_date_by_event(date_field='stop')
        return list(pycompat.izip(start_dates, stop_dates))

    @api.multi
    def _get_recurrent_date_by_event(self, date_field='start'):
        """ Get recurrent dates based on Rule string and all event where recurrent_id is child

        date_field: the field containing the reference date information for recurrence computation
        """
        self.ensure_one()
        if date_field in self._fields and self._fields[date_field].type in ('date', 'datetime'):
            reference_date = self[date_field]
        else:
            reference_date = self.start

        def todate(date):
            val = parser.parse(''.join((re.compile('\d')).findall(date)))
            ## Dates are localized to saved timezone if any, else current timezone.
            if not val.tzinfo:
                val = pytz.UTC.localize(val)
            return val.astimezone(timezone)

        timezone = pytz.timezone(self._context.get('tz') or 'UTC')
        event_date = pytz.UTC.localize(fields.Datetime.from_string(reference_date))  # Add "+hh:mm" timezone
        if not event_date:
            event_date = datetime.now()

        use_naive_datetime = self.allday and self.rrule and 'UNTIL' in self.rrule and 'Z' not in self.rrule
        if not use_naive_datetime:
            # Convert the event date to saved timezone (or context tz) as it'll
            # define the correct hour/day asked by the user to repeat for recurrence.
            event_date = event_date.astimezone(timezone)

        # The start date is naive
        # the timezone will be applied, if necessary, at the very end of the process
        # to allow for DST timezone reevaluation
        rset1 = rrule.rrulestr(str(self.rrule), dtstart=event_date.replace(tzinfo=None), forceset=True, ignoretz=True)

        recurring_meetings = self.search([('recurrent_id', '=', self.id), '|', ('active', '=', False), ('active', '=', True)])

        # We handle a maximum of 50,000 meetings at a time, and clear the cache at each step to
        # control the memory usage.
        invalidate = False
        for meetings in self.env.cr.split_for_in_conditions(recurring_meetings, size=50000):
            if invalidate:
                self.invalidate_cache()
            for meeting in meetings:
                recurring_date = fields.Datetime.from_string(meeting.recurrent_id_date)
                if use_naive_datetime:
                    recurring_date = recurring_date.replace(tzinfo=None)
                else:
                    recurring_date = todate(meeting.recurrent_id_date).replace(tzinfo=None)
                if date_field == "stop":
                    recurring_date += timedelta(hours=self.duration)
                rset1.exdate(recurring_date)
            invalidate = True

        def naive_tz_to_utc(d):
            return timezone.localize(d).astimezone(pytz.UTC)
        return [naive_tz_to_utc(d) if not use_naive_datetime else d for d in rset1 if d.year < MAXYEAR]

    @api.multi
    def _get_recurrency_end_date(self):
        """ Return the last date a recurring event happens, according to its end_type. """
        self.ensure_one()
        data = self.read(['final_date', 'recurrency', 'rrule_type', 'count', 'end_type', 'stop', 'interval'])[0]

        if not data.get('recurrency'):
            return False

        end_type = data.get('end_type')
        final_date = data.get('final_date')
        if end_type == 'count' and all(data.get(key) for key in ['count', 'rrule_type', 'stop', 'interval']):
            count = (data['count'] + 1) * data['interval']
            delay, mult = {
                'daily': ('days', 1),
                'weekly': ('days', 7),
                'monthly': ('months', 1),
                'yearly': ('years', 1),
            }[data['rrule_type']]

            deadline = fields.Datetime.from_string(data['stop'])
            computed_final_date = False
            while not computed_final_date and count > 0:
                try:  # may crash if year > 9999 (in case of recurring events)
                    computed_final_date = deadline + relativedelta(**{delay: count * mult})
                except ValueError:
                    count -= data['interval']
            return computed_final_date or deadline
        return final_date

    @api.multi
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
        lang = self._context.get("lang")
        lang_params = {}
        if lang:
            record_lang = self.env['res.lang'].search([("code", "=", lang)], limit=1)
            lang_params = {
                'date_format': record_lang.date_format,
                'time_format': record_lang.time_format
            }

        # formats will be used for str{f,p}time() which do not support unicode in Python 2, coerce to str
        format_date = pycompat.to_native(lang_params.get("date_format", '%B-%d-%Y'))
        format_time = pycompat.to_native(lang_params.get("time_format", '%I-%M %p'))
        return (format_date, format_time)

    @api.model
    def _get_recurrent_fields(self):
        return ['byday', 'recurrency', 'final_date', 'rrule_type', 'month_by',
                'interval', 'count', 'end_type', 'mo', 'tu', 'we', 'th', 'fr', 'sa',
                'su', 'day', 'week_list']

    @api.model
    def _get_display_time(self, start, stop, zduration, zallday):
        """ Return date and time (from to from) based on duration with timezone in string. Eg :
                1) if user add duration for 2 hours, return : August-23-2013 at (04-30 To 06-30) (Europe/Brussels)
                2) if event all day ,return : AllDay, July-31-2013
        """
        timezone = self._context.get('tz') or self.env.user.partner_id.tz or 'UTC'
        timezone = pycompat.to_native(timezone)  # make safe for str{p,f}time()

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
            duration = date + timedelta(hours=zduration)
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

    name = fields.Char('Meeting Subject', required=True, states={'done': [('readonly', True)]})
    state = fields.Selection([('draft', 'Unconfirmed'), ('open', 'Confirmed')], string='Status', readonly=True, track_visibility='onchange', default='draft')

    is_attendee = fields.Boolean('Attendee', compute='_compute_attendee')
    attendee_status = fields.Selection(Attendee.STATE_SELECTION, string='Attendee Status', compute='_compute_attendee')
    display_time = fields.Char('Event Time', compute='_compute_display_time')
    display_start = fields.Char('Date', compute='_compute_display_start', store=True)
    start = fields.Datetime('Start', required=True, help="Start date of an event, without time for full days events")
    stop = fields.Datetime('Stop', required=True, help="Stop date of an event, without time for full days events")

    allday = fields.Boolean('All Day', states={'done': [('readonly', True)]}, default=False)
    start_date = fields.Date('Start Date', compute='_compute_dates', inverse='_inverse_dates', store=True, states={'done': [('readonly', True)]}, track_visibility='onchange')
    start_datetime = fields.Datetime('Start DateTime', compute='_compute_dates', inverse='_inverse_dates', store=True, states={'done': [('readonly', True)]}, track_visibility='onchange')
    stop_date = fields.Date('End Date', compute='_compute_dates', inverse='_inverse_dates', store=True, states={'done': [('readonly', True)]}, track_visibility='onchange')
    stop_datetime = fields.Datetime('End Datetime', compute='_compute_dates', inverse='_inverse_dates', store=True, states={'done': [('readonly', True)]}, track_visibility='onchange')  # old date_deadline
    duration = fields.Float('Duration', states={'done': [('readonly', True)]})
    description = fields.Text('Description', states={'done': [('readonly', True)]})
    privacy = fields.Selection([('public', 'Everyone'), ('private', 'Only me'), ('confidential', 'Only internal users')], 'Privacy', default='public', states={'done': [('readonly', True)]}, oldname="class")
    location = fields.Char('Location', states={'done': [('readonly', True)]}, track_visibility='onchange', help="Location of Event")
    show_as = fields.Selection([('free', 'Free'), ('busy', 'Busy')], 'Show Time as', states={'done': [('readonly', True)]}, default='busy')

    # linked document
    res_id = fields.Integer('Document ID')
    res_model_id = fields.Many2one('ir.model', 'Document Model', ondelete='cascade')
    res_model = fields.Char('Document Model Name', related='res_model_id.model', readonly=True, store=True)
    activity_ids = fields.One2many('mail.activity', 'calendar_event_id', string='Activities')

    # RECURRENCE FIELD
    rrule = fields.Char('Recurrent Rule', compute='_compute_rrule', inverse='_inverse_rrule', store=True)
    rrule_type = fields.Selection([
        ('daily', 'Day(s)'),
        ('weekly', 'Week(s)'),
        ('monthly', 'Month(s)'),
        ('yearly', 'Year(s)')
    ], string='Recurrence', states={'done': [('readonly', True)]}, help="Let the event automatically repeat at that interval")
    recurrency = fields.Boolean('Recurrent', help="Recurrent Meeting")
    recurrent_id = fields.Integer('Recurrent ID')
    recurrent_id_date = fields.Datetime('Recurrent ID date')
    end_type = fields.Selection([
        ('count', 'Number of repetitions'),
        ('end_date', 'End date')
    ], string='Recurrence Termination', default='count')
    interval = fields.Integer(string='Repeat Every', default=1, help="Repeat every (Days/Week/Month/Year)")
    count = fields.Integer(string='Repeat', help="Repeat x times", default=1)
    mo = fields.Boolean('Mon')
    tu = fields.Boolean('Tue')
    we = fields.Boolean('Wed')
    th = fields.Boolean('Thu')
    fr = fields.Boolean('Fri')
    sa = fields.Boolean('Sat')
    su = fields.Boolean('Sun')
    month_by = fields.Selection([
        ('date', 'Date of month'),
        ('day', 'Day of month')
    ], string='Option', default='date', oldname='select1')
    day = fields.Integer('Date of month', default=1)
    week_list = fields.Selection([
        ('MO', 'Monday'),
        ('TU', 'Tuesday'),
        ('WE', 'Wednesday'),
        ('TH', 'Thursday'),
        ('FR', 'Friday'),
        ('SA', 'Saturday'),
        ('SU', 'Sunday')
    ], string='Weekday')
    byday = fields.Selection([
        ('1', 'First'),
        ('2', 'Second'),
        ('3', 'Third'),
        ('4', 'Fourth'),
        ('5', 'Fifth'),
        ('-1', 'Last')
    ], string='By day')
    final_date = fields.Date('Repeat Until')
    user_id = fields.Many2one('res.users', 'Responsible', states={'done': [('readonly', True)]}, default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', string='Responsible', related='user_id.partner_id', readonly=True)
    active = fields.Boolean('Active', default=True, help="If the active field is set to false, it will allow you to hide the event alarm information without removing it.")
    categ_ids = fields.Many2many('calendar.event.type', 'meeting_category_rel', 'event_id', 'type_id', 'Tags')
    attendee_ids = fields.One2many('calendar.attendee', 'event_id', 'Participant', ondelete='cascade')
    partner_ids = fields.Many2many('res.partner', 'calendar_event_res_partner_rel', string='Attendees', states={'done': [('readonly', True)]}, default=_default_partners)
    alarm_ids = fields.Many2many('calendar.alarm', 'calendar_alarm_calendar_event_rel', string='Reminders', ondelete="restrict", copy=False)
    is_highlighted = fields.Boolean(compute='_compute_is_highlighted', string='Is the Event Highlighted')

    @api.multi
    def _compute_attendee(self):
        for meeting in self:
            attendee = meeting._find_my_attendee()
            meeting.is_attendee = bool(attendee)
            meeting.attendee_status = attendee.state if attendee else 'needsAction'

    @api.multi
    def _compute_display_time(self):
        for meeting in self:
            meeting.display_time = self._get_display_time(meeting.start, meeting.stop, meeting.duration, meeting.allday)

    @api.multi
    @api.depends('allday', 'start_date', 'start_datetime')
    def _compute_display_start(self):
        for meeting in self:
            meeting.display_start = meeting.start_date if meeting.allday else meeting.start_datetime

    @api.multi
    @api.depends('allday', 'start', 'stop')
    def _compute_dates(self):
        """ Adapt the value of start_date(time)/stop_date(time) according to start/stop fields and allday. Also, compute
            the duration for not allday meeting ; otherwise the duration is set to zero, since the meeting last all the day.
        """
        for meeting in self:
            if meeting.allday:
                meeting.start_date = meeting.start
                meeting.start_datetime = False
                meeting.stop_date = meeting.stop
                meeting.stop_datetime = False

                meeting.duration = 0.0
            else:
                meeting.start_date = False
                meeting.start_datetime = meeting.start
                meeting.stop_date = False
                meeting.stop_datetime = meeting.stop

                meeting.duration = self._get_duration(meeting.start, meeting.stop)

    @api.multi
    def _inverse_dates(self):
        for meeting in self:
            if meeting.allday:

                # Convention break:
                # stop and start are NOT in UTC in allday event
                # in this case, they actually represent a date
                # i.e. Christmas is on 25/12 for everyone
                # even if people don't celebrate it simultaneously
                enddate = fields.Datetime.from_string(meeting.stop_date)
                enddate = enddate.replace(hour=18)
                meeting.stop = fields.Datetime.to_string(enddate)

                startdate = fields.Datetime.from_string(meeting.start_date)
                startdate = startdate.replace(hour=8)  # Set 8 AM
                meeting.start = fields.Datetime.to_string(startdate)
            else:
                meeting.write({'start': meeting.start_datetime,
                               'stop': meeting.stop_datetime})

    @api.depends('byday', 'recurrency', 'final_date', 'rrule_type', 'month_by', 'interval', 'count', 'end_type', 'mo', 'tu', 'we', 'th', 'fr', 'sa', 'su', 'day', 'week_list')
    def _compute_rrule(self):
        """ Gets Recurrence rule string according to value type RECUR of iCalendar from the values given.
            :return dictionary of rrule value.
        """
        for meeting in self:
            if meeting.recurrency:
                meeting.rrule = meeting._rrule_serialize()
            else:
                meeting.rrule = ''

    @api.multi
    def _inverse_rrule(self):
        for meeting in self:
            if meeting.rrule:
                data = self._rrule_default_values()
                data['recurrency'] = True
                data.update(self._rrule_parse(meeting.rrule, data, meeting.start))
                meeting.update(data)

    @api.constrains('start_datetime', 'stop_datetime', 'start_date', 'stop_date')
    def _check_closing_date(self):
        for meeting in self:
            if meeting.start_datetime and meeting.stop_datetime and meeting.stop_datetime < meeting.start_datetime:
                raise ValidationError(_('Ending datetime cannot be set before starting datetime.') + "\n" +
                                      _("Meeting '%s' starts '%s' and ends '%s'") % (meeting.name, meeting.start_datetime, meeting.stop_datetime)
                    )
            if meeting.start_date and meeting.stop_date and meeting.stop_date < meeting.start_date:
                raise ValidationError(_('Ending date cannot be set before starting date.') + "\n" +
                                      _("Meeting '%s' starts '%s' and ends '%s'") % (meeting.name, meeting.start_date, meeting.stop_date)
                    )

    @api.onchange('start_datetime', 'duration')
    def _onchange_duration(self):
        if self.start_datetime:
            start = fields.Datetime.from_string(self.start_datetime)
            self.start = self.start_datetime
            self.stop = fields.Datetime.to_string(start + timedelta(hours=self.duration))

    @api.onchange('start_date')
    def _onchange_start_date(self):
        if self.start_date:
            self.start = self.start_date

    @api.onchange('stop_date')
    def _onchange_stop_date(self):
        if self.stop_date:
            self.stop = self.stop_date

    ####################################################
    # Calendar Business, Reccurency, ...
    ####################################################

    @api.multi
    def get_ics_file(self):
        """ Returns iCalendar file for the event invitation.
            :returns a dict of .ics file content for each meeting
        """
        result = {}

        def ics_datetime(idate, allday=False):
            if idate:
                if allday:
                    return fields.Date.from_string(idate)
                else:
                    return fields.Datetime.from_string(idate).replace(tzinfo=pytz.timezone('UTC'))
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
            event.add('created').value = ics_datetime(time.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
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

    @api.multi
    def create_attendees(self):
        current_user = self.env.user
        result = {}
        for meeting in self:
            alreay_meeting_partners = meeting.attendee_ids.mapped('partner_id')
            meeting_attendees = self.env['calendar.attendee']
            meeting_partners = self.env['res.partner']
            for partner in meeting.partner_ids.filtered(lambda partner: partner not in alreay_meeting_partners):
                values = {
                    'partner_id': partner.id,
                    'email': partner.email,
                    'event_id': meeting.id,
                }

                # current user don't have to accept his own meeting
                if partner == self.env.user.partner_id:
                    values['state'] = 'accepted'

                attendee = self.env['calendar.attendee'].create(values)

                meeting_attendees |= attendee
                meeting_partners |= partner

            if meeting_attendees:
                to_notify = meeting_attendees.filtered(lambda a: a.email != current_user.email)
                to_notify._send_mail_to_attendees('calendar.calendar_template_meeting_invitation')

                meeting.write({'attendee_ids': [(4, meeting_attendee.id) for meeting_attendee in meeting_attendees]})
            if meeting_partners:
                meeting.message_subscribe(partner_ids=meeting_partners.ids)

            # We remove old attendees who are not in partner_ids now.
            all_partners = meeting.partner_ids
            all_partner_attendees = meeting.attendee_ids.mapped('partner_id')
            old_attendees = meeting.attendee_ids
            partners_to_remove = all_partner_attendees + meeting_partners - all_partners

            attendees_to_remove = self.env["calendar.attendee"]
            if partners_to_remove:
                attendees_to_remove = self.env["calendar.attendee"].search([('partner_id', 'in', partners_to_remove.ids), ('event_id', '=', meeting.id)])
                attendees_to_remove.unlink()

            result[meeting.id] = {
                'new_attendees': meeting_attendees,
                'old_attendees': old_attendees,
                'removed_attendees': attendees_to_remove,
                'removed_partners': partners_to_remove
            }
        return result

    @api.multi
    def get_search_fields(self, order_fields, r_date=None):
        sort_fields = {}
        for field in order_fields:
            if field == 'id' and r_date:
                sort_fields[field] = real_id2calendar_id(self.id, r_date)
            else:
                sort_fields[field] = self[field]
                if isinstance(self[field], models.BaseModel):
                    name_get = self[field].mapped('display_name')
                    sort_fields[field] = name_get and name_get[0] or ''
        if r_date:
            sort_fields['sort_start'] = r_date.strftime(VIRTUALID_DATETIME_FORMAT)
        else:
            display_start = self.display_start
            sort_fields['sort_start'] = display_start.replace(' ', '').replace('-', '') if display_start else False
        return sort_fields

    @api.multi
    def get_recurrent_ids(self, domain, order=None):
        """ Gives virtual event ids for recurring events. This method gives ids of dates
            that comes between start date and end date of calendar views
            :param order:   The fields (comma separated, format "FIELD {DESC|ASC}") on which
                            the events should be sorted
        """
        if order:
            order_fields = [field.split()[0] for field in order.split(',')]
        else:
            # fallback on self._order defined on the model
            order_fields = [field.split()[0] for field in self._order.split(',')]

        if 'id' not in order_fields:
            order_fields.append('id')

        result_data = []
        result = []
        for meeting in self:
            if not meeting.recurrency or not meeting.rrule:
                result.append(meeting.id)
                result_data.append(meeting.get_search_fields(order_fields))
                continue
            rdates = meeting._get_recurrent_dates_by_event()

            for r_start_date, r_stop_date in rdates:
                # fix domain evaluation
                # step 1: check date and replace expression by True or False, replace other expressions by True
                # step 2: evaluation of & and |
                # check if there are one False
                pile = []
                ok = True
                r_date = r_start_date  # default for empty domain
                for arg in domain:
                    if str(arg[0]) in ('start', 'stop', 'final_date'):
                        if str(arg[0]) == 'start':
                            r_date = r_start_date
                        else:
                            r_date = r_stop_date
                        if arg[2] and len(arg[2]) > len(r_date.strftime(DEFAULT_SERVER_DATE_FORMAT)):
                            dformat = DEFAULT_SERVER_DATETIME_FORMAT
                        else:
                            dformat = DEFAULT_SERVER_DATE_FORMAT
                        if (arg[1] == '='):
                            ok = r_date.strftime(dformat) == arg[2]
                        if (arg[1] == '>'):
                            ok = r_date.strftime(dformat) > arg[2]
                        if (arg[1] == '<'):
                            ok = r_date.strftime(dformat) < arg[2]
                        if (arg[1] == '>='):
                            ok = r_date.strftime(dformat) >= arg[2]
                        if (arg[1] == '<='):
                            ok = r_date.strftime(dformat) <= arg[2]
                        if (arg[1] == '!='):
                            ok = r_date.strftime(dformat) != arg[2]
                        pile.append(ok)
                    elif str(arg) == str('&') or str(arg) == str('|'):
                        pile.append(arg)
                    else:
                        pile.append(True)
                pile.reverse()
                new_pile = []
                for item in pile:
                    if not isinstance(item, pycompat.string_types):
                        res = item
                    elif str(item) == str('&'):
                        first = new_pile.pop()
                        second = new_pile.pop()
                        res = first and second
                    elif str(item) == str('|'):
                        first = new_pile.pop()
                        second = new_pile.pop()
                        res = first or second
                    new_pile.append(res)

                if [True for item in new_pile if not item]:
                    continue
                result_data.append(meeting.get_search_fields(order_fields, r_date=r_start_date))

        # seq of (field, should_reverse)
        sort_spec = list(tools.unique(
            (sort_remap(key.split()[0]), key.lower().endswith(' desc'))
            for key in (order or self._order).split(',')
        ))
        def key(record):
            # we need to deal with undefined fields, as sorted requires an homogeneous iterable
            def boolean_product(x):
                x = False if (isinstance(x, models.Model) and not x) else x
                if isinstance(x, bool):
                    return (x, x)
                return (True, x)
            # first extract the values for each key column (ids need special treatment)
            vals_spec = (
                (any_id2key(record[name]) if name == 'id' else boolean_product(record[name]), desc)
                for name, desc in sort_spec
            )
            # then Reverse if the value matches a "desc" column
            return [
                (tools.Reverse(v) if desc else v)
                for v, desc in vals_spec
            ]
        return [r['id'] for r in sorted(result_data, key=key)]

    @api.multi
    def _rrule_serialize(self):
        """ Compute rule string according to value type RECUR of iCalendar
            :return: string containing recurring rule (empty if no rule)
        """
        if self.interval and self.interval < 0:
            raise UserError(_('interval cannot be negative.'))
        if self.count and self.count <= 0:
            raise UserError(_('Event recurrence interval cannot be negative.'))

        def get_week_string(freq):
            weekdays = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
            if freq == 'weekly':
                byday = [field.upper() for field in weekdays if self[field]]
                if byday:
                    return ';BYDAY=' + ','.join(byday)
            return ''

        def get_month_string(freq):
            if freq == 'monthly':
                if self.month_by == 'date' and (self.day < 1 or self.day > 31):
                    raise UserError(_("Please select a proper day of the month."))

                if self.month_by == 'day' and self.byday and self.week_list:  # Eg : Second Monday of the month
                    return ';BYDAY=' + self.byday + self.week_list
                elif self.month_by == 'date':  # Eg : 16th of the month
                    return ';BYMONTHDAY=' + str(self.day)
            return ''

        def get_end_date():
            end_date_new = ''.join((re.compile('\d')).findall(self.final_date)) + 'T235959Z' if self.final_date else False
            return (self.end_type == 'count' and (';COUNT=' + str(self.count)) or '') +\
                ((end_date_new and self.end_type == 'end_date' and (';UNTIL=' + end_date_new)) or '')

        freq = self.rrule_type  # day/week/month/year
        result = ''
        if freq:
            interval_srting = self.interval and (';INTERVAL=' + str(self.interval)) or ''
            result = 'FREQ=' + freq.upper() + get_week_string(freq) + interval_srting + get_end_date() + get_month_string(freq)
        return result

    def _rrule_default_values(self):
        return {
            'byday': False,
            'recurrency': False,
            'final_date': False,
            'rrule_type': False,
            'month_by': False,
            'interval': 0,
            'count': False,
            'end_type': False,
            'mo': False,
            'tu': False,
            'we': False,
            'th': False,
            'fr': False,
            'sa': False,
            'su': False,
            'day': False,
            'week_list': False
        }

    def _rrule_parse(self, rule_str, data, date_start):
        day_list = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
        rrule_type = ['yearly', 'monthly', 'weekly', 'daily']
        ddate = fields.Datetime.from_string(date_start)
        if 'Z' in rule_str and not ddate.tzinfo:
            ddate = ddate.replace(tzinfo=pytz.timezone('UTC'))
            rule = rrule.rrulestr(rule_str, dtstart=ddate)
        else:
            rule = rrule.rrulestr(rule_str, dtstart=ddate)

        if rule._freq > 0 and rule._freq < 4:
            data['rrule_type'] = rrule_type[rule._freq]
        data['count'] = rule._count
        data['interval'] = rule._interval
        data['final_date'] = rule._until and rule._until.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        #repeat weekly
        if rule._byweekday:
            for i in range(0, 7):
                if i in rule._byweekday:
                    data[day_list[i]] = True
            data['rrule_type'] = 'weekly'
        #repeat monthly by nweekday ((weekday, weeknumber), )
        if rule._bynweekday:
            data['week_list'] = day_list[list(rule._bynweekday)[0][0]].upper()
            data['byday'] = str(list(rule._bynweekday)[0][1])
            data['month_by'] = 'day'
            data['rrule_type'] = 'monthly'

        if rule._bymonthday:
            data['day'] = list(rule._bymonthday)[0]
            data['month_by'] = 'date'
            data['rrule_type'] = 'monthly'

        #repeat yearly but for odoo it's monthly, take same information as monthly but interval is 12 times
        if rule._bymonth:
            data['interval'] = data['interval'] * 12

        #FIXEME handle forever case
        #end of recurrence
        #in case of repeat for ever that we do not support right now
        if not (data.get('count') or data.get('final_date')):
            data['count'] = 100
        if data.get('count'):
            data['end_type'] = 'count'
        else:
            data['end_type'] = 'end_date'
        return data

    @api.multi
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
            result = pycompat.text_type(date.day)

        elif interval == 'month':
            # Localized month name and year
            result = babel.dates.format_date(date=date, format='MMMM y', locale=self._context.get('lang') or 'en_US')

        elif interval == 'dayname':
            # Localized day name
            result = babel.dates.format_date(date=date, format='EEEE', locale=self._context.get('lang') or 'en_US')

        elif interval == 'time':
            # Localized time
            # FIXME: formats are specifically encoded to bytes, maybe use babel?
            dummy, format_time = self._get_date_formats()
            result = tools.ustr(date.strftime(format_time + " %Z"))

        return result

    @api.multi
    def get_display_time_tz(self, tz=False):
        """ get the display_time of the meeting, forcing the timezone. This method is called from email template, to not use sudo(). """
        self.ensure_one()
        if tz:
            self = self.with_context(tz=tz)
        return self._get_display_time(self.start, self.stop, self.duration, self.allday)

    @api.multi
    def detach_recurring_event(self, values=None):
        """ Detach a virtual recurring event by duplicating the original and change reccurent values
            :param values : dict of value to override on the detached event
        """
        if not values:
            values = {}

        real_id = calendar_id2real_id(self.id)
        meeting_origin = self.browse(real_id)

        data = self.read(['allday', 'start', 'stop', 'rrule', 'duration'])[0]
        if data.get('rrule'):
            data.update(
                values,
                recurrent_id=real_id,
                recurrent_id_date=data.get('start'),
                rrule_type=False,
                rrule='',
                recurrency=False,
                final_date=False,
                end_type=False
            )

            # do not copy the id
            if data.get('id'):
                del data['id']
            return meeting_origin.copy(default=data)

    @api.multi
    def action_detach_recurring_event(self):
        meeting = self.detach_recurring_event()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.event',
            'view_mode': 'form',
            'res_id': meeting.id,
            'target': 'current',
            'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}}
        }

    @api.multi
    def action_open_calendar_event(self):
        if self.res_model and self.res_id:
            return self.env[self.res_model].browse(self.res_id).get_formview_action()
        return False

    @api.multi
    def action_sendmail(self):
        email = self.env.user.email
        if email:
            for meeting in self:
                meeting.attendee_ids._send_mail_to_attendees('calendar.calendar_template_meeting_invitation')
        return True

    ####################################################
    # Messaging
    ####################################################

    @api.multi
    def _get_message_unread(self):
        id_map = {x: calendar_id2real_id(x) for x in self.ids}
        real = self.browse(set(id_map.values()))
        super(Meeting, real)._get_message_unread()
        for event in self:
            if event.id == id_map[event.id]:
                continue
            rec = self.browse(id_map[event.id])
            event.message_unread_counter = rec.message_unread_counter
            event.message_unread = rec.message_unread

    @api.multi
    def _get_message_needaction(self):
        id_map = {x: calendar_id2real_id(x) for x in self.ids}
        real = self.browse(set(id_map.values()))
        super(Meeting, real)._get_message_needaction()
        for event in self:
            if event.id == id_map[event.id]:
                continue
            rec = self.browse(id_map[event.id])
            event.message_needaction_counter = rec.message_needaction_counter
            event.message_needaction = rec.message_needaction

    @api.multi
    @api.returns('self', lambda value: value.id)
    def message_post(self, **kwargs):
        thread_id = self.id
        if isinstance(self.id, pycompat.string_types):
            thread_id = get_real_ids(self.id)
        if self.env.context.get('default_date'):
            context = dict(self.env.context)
            del context['default_date']
            self = self.with_context(context)
        return super(Meeting, self.browse(thread_id)).message_post(**kwargs)

    @api.multi
    def message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None, force=True):
        records = self.browse(get_real_ids(self.ids))
        return super(Meeting, records).message_subscribe(
            partner_ids=partner_ids,
            channel_ids=channel_ids,
            subtype_ids=subtype_ids,
            force=force)

    @api.multi
    def message_unsubscribe(self, partner_ids=None, channel_ids=None):
        records = self.browse(get_real_ids(self.ids))
        return super(Meeting, records).message_unsubscribe(partner_ids=partner_ids, channel_ids=channel_ids)

    ####################################################
    # ORM Overrides
    ####################################################

    @api.multi
    def get_metadata(self):
        real = self.browse({calendar_id2real_id(x) for x in self.ids})
        return super(Meeting, real).get_metadata()

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        for arg in args:
            if arg[0] == 'id':
                for n, calendar_id in enumerate(arg[2]):
                    if isinstance(calendar_id, pycompat.string_types):
                        arg[2][n] = calendar_id.split('-')[0]
        return super(Meeting, self)._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

    @api.multi
    def write(self, values):
        # FIXME: neverending recurring events
        if 'rrule' in values:
            values['rrule'] = self._fix_rrule(values)

        # compute duration, only if start and stop are modified
        if not 'duration' in values and 'start' in values and 'stop' in values:
            values['duration'] = self._get_duration(values['start'], values['stop'])

        self._sync_activities(values)

        # process events one by one
        for meeting in self:
            # special write of complex IDS
            real_ids = []
            new_ids = []
            if not is_calendar_id(meeting.id):
                real_ids = [int(meeting.id)]
            else:
                real_event_id = calendar_id2real_id(meeting.id)

                # if we are setting the recurrency flag to False or if we are only changing fields that
                # should be only updated on the real ID and not on the virtual (like message_follower_ids):
                # then set real ids to be updated.
                blacklisted = any(key in values for key in ('start', 'stop', 'active'))
                if not values.get('recurrency', True) or not blacklisted:
                    real_ids = [real_event_id]
                else:
                    data = meeting.read(['start', 'stop', 'rrule', 'duration'])[0]
                    if data.get('rrule'):
                        new_ids = meeting.with_context(dont_notify=True).detach_recurring_event(values).ids  # to prevent multiple notify_next_alarm

            new_meetings = self.browse(new_ids)
            real_meetings = self.browse(real_ids)
            all_meetings = real_meetings + new_meetings
            super(Meeting, real_meetings).write(values)

            # set end_date for calendar searching
            if any(field in values for field in ['recurrency', 'end_type', 'count', 'rrule_type', 'start', 'stop']):
                for real_meeting in real_meetings:
                    if real_meeting.recurrency and real_meeting.end_type == u'count':
                        final_date = real_meeting._get_recurrency_end_date()
                        super(Meeting, real_meeting).write({'final_date': final_date})

            attendees_create = False
            if values.get('partner_ids', False):
                attendees_create = all_meetings.with_context(dont_notify=True).create_attendees()  # to prevent multiple notify_next_alarm

            # Notify attendees if there is an alarm on the modified event, or if there was an alarm
            # that has just been removed, as it might have changed their next event notification
            if not self._context.get('dont_notify'):
                if len(meeting.alarm_ids) > 0 or values.get('alarm_ids'):
                    partners_to_notify = meeting.partner_ids.ids
                    event_attendees_changes = attendees_create and real_ids and attendees_create[real_ids[0]]
                    if event_attendees_changes:
                        partners_to_notify.extend(event_attendees_changes['removed_partners'].ids)
                    self.env['calendar.alarm_manager'].notify_next_alarm(partners_to_notify)

            if (values.get('start_date') or values.get('start_datetime') or
                    (values.get('start') and self.env.context.get('from_ui'))) and values.get('active', True):
                for current_meeting in all_meetings:
                    if attendees_create:
                        attendees_create = attendees_create[current_meeting.id]
                        attendee_to_email = attendees_create['old_attendees'] - attendees_create['removed_attendees']
                    else:
                        attendee_to_email = current_meeting.attendee_ids

                    if attendee_to_email:
                        attendee_to_email._send_mail_to_attendees('calendar.calendar_template_meeting_changedate')
        return True

    @api.model
    def create(self, values):
        # FIXME: neverending recurring events
        if 'rrule' in values:
            values['rrule'] = self._fix_rrule(values)

        if not 'user_id' in values:  # Else bug with quick_create when we are filter on an other user
            values['user_id'] = self.env.user.id

        # compute duration, if not given
        if not 'duration' in values:
            values['duration'] = self._get_duration(values['start'], values['stop'])

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

        meeting = super(Meeting, self).create(values)
        meeting._sync_activities(values)

        final_date = meeting._get_recurrency_end_date()
        # `dont_notify=True` in context to prevent multiple notify_next_alarm
        meeting.with_context(dont_notify=True).write({'final_date': final_date})
        meeting.with_context(dont_notify=True).create_attendees()

        # Notify attendees if there is an alarm on the created event, as it might have changed their
        # next event notification
        if not self._context.get('dont_notify'):
            if len(meeting.alarm_ids) > 0:
                self.env['calendar.alarm_manager'].notify_next_alarm(meeting.partner_ids.ids)
        return meeting

    @api.multi
    def export_data(self, fields_to_export, raw_data=False):
        """ Override to convert virtual ids to ids """
        records = self.browse(set(get_real_ids(self.ids)))
        return super(Meeting, records).export_data(fields_to_export, raw_data)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'date' in groupby:
            raise UserError(_('Group by date is not supported, use the calendar view instead.'))
        return super(Meeting, self.with_context(virtual_id=False)).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        if not fields:
            fields = list(self._fields)
        fields2 = fields and fields[:]
        EXTRAFIELDS = ('privacy', 'user_id', 'duration', 'allday', 'start', 'rrule')
        for f in EXTRAFIELDS:
            if fields and (f not in fields):
                fields2.append(f)

        select = [(x, calendar_id2real_id(x)) for x in self.ids]
        real_events = self.browse([real_id for calendar_id, real_id in select])
        real_data = super(Meeting, real_events).read(fields=fields2, load=load)
        real_data = dict((d['id'], d) for d in real_data)

        result = []
        for calendar_id, real_id in select:
            if not real_data.get(real_id):
                continue
            res = real_data[real_id].copy()
            ls = calendar_id2real_id(calendar_id, with_date=res and res.get('duration', 0) > 0 and res.get('duration') or 1)
            if not isinstance(ls, (pycompat.string_types, pycompat.integer_types)) and len(ls) >= 2:
                res['start'] = ls[1]
                res['stop'] = ls[2]

                if res['allday']:
                    res['start_date'] = ls[1]
                    res['stop_date'] = ls[2]
                else:
                    res['start_datetime'] = ls[1]
                    res['stop_datetime'] = ls[2]

                if 'display_time' in fields:
                    res['display_time'] = self._get_display_time(ls[1], ls[2], res['duration'], res['allday'])

            res['id'] = calendar_id
            result.append(res)

        for r in result:
            if r['user_id']:
                user_id = type(r['user_id']) in (tuple, list) and r['user_id'][0] or r['user_id']
                partner_id = self.env.user.partner_id.id
                if user_id == self.env.user.id or partner_id in r.get("partner_ids", []):
                    continue
            if r['privacy'] == 'private':
                for f in r:
                    recurrent_fields = self._get_recurrent_fields()
                    public_fields = list(set(recurrent_fields + ['id', 'allday', 'start', 'stop', 'display_start', 'display_stop', 'duration', 'user_id', 'state', 'interval', 'count', 'recurrent_id_date', 'rrule']))
                    if f not in public_fields:
                        if isinstance(r[f], list):
                            r[f] = []
                        else:
                            r[f] = False
                    if f == 'name':
                        r[f] = _('Busy')

        for r in result:
            for k in EXTRAFIELDS:
                if (k in r) and (fields and (k not in fields)):
                    del r[k]
        return result

    @api.multi
    def unlink(self, can_be_deleted=True):
        # Get concerned attendees to notify them if there is an alarm on the unlinked events,
        # as it might have changed their next event notification
        events = self.search([('id', 'in', self.ids), ('alarm_ids', '!=', False)])
        partner_ids = events.mapped('partner_ids').ids

        records_to_exclude = self.env['calendar.event']
        records_to_unlink = self.env['calendar.event'].with_context(recompute=False)

        for meeting in self:
            if can_be_deleted and not is_calendar_id(meeting.id):  # if  ID REAL
                if meeting.recurrent_id:
                    records_to_exclude |= meeting
                else:
                    # int() required because 'id' from calendar view is a string, since it can be calendar virtual id
                    records_to_unlink |= self.browse(int(meeting.id))
            else:
                records_to_exclude |= meeting

        result = False
        if records_to_unlink:
            result = super(Meeting, records_to_unlink).unlink()
        if records_to_exclude:
            result = records_to_exclude.with_context(dont_notify=True).write({'active': False})

        # Notify the concerned attendees (must be done after removing the events)
        self.env['calendar.alarm_manager'].notify_next_alarm(partner_ids)
        return result

    @api.model
    def search(self, args, offset=0, limit=0, order=None, count=False):
        if self._context.get('mymeetings'):
            args += [('partner_ids', 'in', self.env.user.partner_id.ids)]

        new_args = []
        for arg in args:
            new_arg = arg
            if arg[0] in ('stop_date', 'stop_datetime', 'stop',) and arg[1] == ">=":
                if self._context.get('virtual_id', True):
                    new_args += ['|', '&', ('recurrency', '=', 1), ('final_date', arg[1], arg[2])]
            elif arg[0] == "id":
                new_arg = (arg[0], arg[1], get_real_ids(arg[2]))
            new_args.append(new_arg)

        if not self._context.get('virtual_id', True):
            return super(Meeting, self).search(new_args, offset=offset, limit=limit, order=order, count=count)

        if any(arg[0] == 'start' for arg in args) and \
           not any(arg[0] in ('stop', 'final_date') for arg in args):
            # domain with a start filter but with no stop clause should be extended
            # e.g. start=2017-01-01, count=5 => virtual occurences must be included in ('start', '>', '2017-01-02')
            start_args = new_args
            new_args = []
            for arg in start_args:
                new_arg = arg
                if arg[0] in ('start_date', 'start_datetime', 'start',):
                    new_args += ['|', '&', ('recurrency', '=', 1), ('final_date', arg[1], arg[2])]
                new_args.append(new_arg)

        # offset, limit, order and count must be treated separately as we may need to deal with virtual ids
        events = super(Meeting, self).search(new_args, offset=0, limit=0, order=None, count=False)
        events = self.browse(events.get_recurrent_ids(args, order=order))
        if count:
            return len(events)
        elif limit:
            return events[offset: offset + limit]
        return events

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        default = default or {}
        return super(Meeting, self.browse(calendar_id2real_id(self.id))).copy(default)

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

    @api.model
    def _fix_rrule(self, values):
        rule_str = values.get('rrule')
        if rule_str:
            if 'UNTIL' not in rule_str and 'COUNT' not in rule_str:
                rule_str += ';COUNT=100'
        return rule_str
