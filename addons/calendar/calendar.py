# -*- coding: utf-8 -*-

import collections
import logging
import pytz
import re
import uuid

from babel.dates import format_date as babel_format_date
from datetime import datetime, timedelta
from dateutil import parser, rrule
from dateutil.relativedelta import relativedelta
from operator import itemgetter
from werkzeug.exceptions import BadRequest

from odoo import api, fields, models, registry, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


def calendar_id2real_id(calendar_id=None, with_date=False):
    """
    Convert a "virtual/recurring event id" (type string) into a real event id (type int).
    E.g. virtual/recurring event id is 4-20091201100000, so it will return 4.
    @param calendar_id: id of calendar
    @param with_date: if a value is passed to this param it will return dates based on value of withdate + calendar_id
    @return: real event id
    """
    if calendar_id and isinstance(calendar_id, (basestring)):
        res = calendar_id.split('-')
        if len(res) >= 2:
            real_id = res[0]
            if with_date:
                real_date = fields.Datetime.to_string(datetime.strptime(res[1], "%Y%m%d%H%M%S"))
                end = fields.Datetime.from_string(real_date) + timedelta(hours=with_date)
                return (int(real_id), real_date, fields.Datetime.to_string(end))
            return int(real_id)
    return calendar_id and int(calendar_id) or calendar_id


def get_real_ids(ids):
    if isinstance(ids, (basestring, int, long)):
        return calendar_id2real_id(ids)

    if isinstance(ids, (list, tuple)):
        return [calendar_id2real_id(id) for id in ids]


class CalendarAttendee(models.Model):
    """
    Calendar Attendee Information
    """
    _name = 'calendar.attendee'
    _rec_name = 'cn'
    _description = 'Attendee information'

    STATE_SELECTION = [
        ('needsAction', 'Needs Action'),
        ('tentative', 'Uncertain'),
        ('declined', 'Declined'),
        ('accepted', 'Accepted'),
    ]

    state = fields.Selection(STATE_SELECTION, string='Status', default='needsAction', readonly=True, help="Status of the attendee's participation")
    cn = fields.Char(compute='_compute_common_name', string='Common name', store=True)
    partner_id = fields.Many2one('res.partner', string='Contact', readonly="True")
    email = fields.Char(help="Email of Invited Person")
    availability = fields.Selection([('free', 'Free'), ('busy', 'Busy')], string='Free/Busy', readonly="True")
    access_token = fields.Char('Invitation Token')
    event_id = fields.Many2one('calendar.event', string='Meeting linked', ondelete='cascade')

    @api.depends('partner_id', 'email', 'partner_id.name')
    def _compute_common_name(self):
        for attendee in self:
            if attendee.partner_id:
                attendee.cn = attendee.partner_id.name
            else:
                attendee.cn = attendee.email

    @api.multi
    def copy(self, default=None):
        raise UserError(_('You cannot duplicate a calendar attendee.'))

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """
        Make entry on email and availability on change of partner_id field.
        """
        self.email = self.partner_id.email

    @api.model
    def get_ics_file(self, event_obj):
        """
        Returns iCalendar file for the event invitation.
        @param event_obj: event recordset
        @return: .ics file content
        """
        res = None

        def ics_datetime(idate, allday=False):
            if idate:
                if allday:
                    return fields.Date.from_string(idate)
                else:
                    return fields.Datetime.from_string(idate).replace(tzinfo=pytz.timezone('UTC'))
            return False

        try:
            import vobject
        except ImportError:
            return res

        cal = vobject.iCalendar()
        event = cal.add('vevent')
        if not event_obj.start or not event_obj.stop:
            raise UserError(_("First you have to specify the date of the invitation."))
        event.add('created').value = ics_datetime(fields.Datetime.now())
        event.add('dtstart').value = ics_datetime(event_obj.start, event_obj.allday)
        event.add('dtend').value = ics_datetime(event_obj.stop, event_obj.allday)
        event.add('summary').value = event_obj.name
        if event_obj.description:
            event.add('description').value = event_obj.description
        if event_obj.location:
            event.add('location').value = event_obj.location
        if event_obj.rrule:
            event.add('rrule').value = event_obj.rrule

        for alarm in event_obj.alarm_ids:
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
            valarm.add('DESCRIPTION').value = alarm.name or 'Odoo'
        for attendee in event_obj.attendee_ids:
            attendee_add = event.add('attendee')
            attendee_add.value = 'MAILTO:' + (attendee.email or '')
        return cal.serialize()

    @api.multi
    def _send_mail_to_attendees(self, email_from=tools.config.get('email_from', False),
                                template_xmlid='calendar_template_meeting_invitation', force=False):
        """
        Send mail for event invitation to event attendees.
        @param email_from: email address for user sending the mail
        @param force: If set to True, email will be sent to user himself. Usefull for example for alert, ...
        """
        res = False

        if self.env['ir.config_parameter'].get_param('calendar.block_mail') or self.env.context.get("no_mail_to_attendees"):
            return res

        mail_ids = []
        Mail = self.env['mail.mail']
        local_context = dict(self.env.context)
        color = {
            'needsAction': 'grey',
            'accepted': 'green',
            'tentative': '#FFFF00',
            'declined': 'red'
        }

        template = self.env.ref('calendar.%s' % template_xmlid)
        act_id = self.env.ref('calendar.view_calendar_event_calendar').id
        local_context.update({
            'color': color,
            'action_id': self.env['ir.actions.act_window'].search([('view_id', '=', act_id)], limit=1).id,
            'dbname': self.env.cr.dbname,
            'base_url': self.env['ir.config_parameter'].get_param('web.base.url', default='http://localhost:8069')
        })

        for attendee in self.filtered(lambda att: att.email and email_from and (att.email != email_from or force)):
            ics_file = self.get_ics_file(attendee.event_id)
            mail_id = template.with_context(local_context).send_mail(attendee.id)

            vals = {}
            if ics_file:
                vals['attachment_ids'] = [(0, 0, {'name': 'invitation.ics',
                                                  'datas_fname': 'invitation.ics',
                                                  'datas': str(ics_file).encode('base64')})]
            vals['model'] = None  # We don't want to have the mail in the tchatter while in queue!
            Mail.browse(mail_id).mail_message_id.write(vals)
            mail_ids.append(mail_id)

        if mail_ids:
            res = Mail.browse(mail_ids).send()

        return res

    @api.multi
    def do_tentative(self):
        """
        Makes event invitation as Tentative.
        """
        return self.write({'state': 'tentative'})

    @api.multi
    def do_accept(self):
        """
        Marks event invitation as Accepted.
        """
        self.write({'state': 'accepted'})
        for attendee in self:
            attendee.event_id.message_post(body=_("%s has accepted invitation") % (attendee.cn), subtype="calendar.subtype_invitation")
        return True

    @api.multi
    def do_decline(self):
        """
        Marks event invitation as Declined.
        """
        self.write({'state': 'declined'})
        for attendee in self:
            attendee.event_id.message_post(body=_("%s has declined invitation") % (attendee.cn), subtype="calendar.subtype_invitation")
        return True

    @api.model
    def create(self, vals):
        if not vals.get("email") and vals.get("cn"):
            cnval = vals.get("cn").split(':')
            email = filter(lambda x: '@' in x, cnval)
            vals['email'] = email and email[0] or ''
        return super(CalendarAttendee, self).create(vals)


class Partner(models.Model):
    _inherit = 'res.partner'

    calendar_last_notif_ack = fields.Datetime(string='Last notification marked as read from base Calendar')

    @api.multi
    def get_attendee_detail(self, meeting_id):
        """
        Return a list of tuple (id, name, status)
        Used by web_calendar.js : Many2ManyAttendee
        """
        datas = []
        meeting = self.env['calendar.event'].browse(get_real_ids(meeting_id))
        for partner in self:
            data = [partner.id, partner.display_name, False, partner.color]
            if meeting:
                for attendee in meeting.attendee_ids.filtered(lambda att: att.partner_id == partner):
                    data[2] = attendee.state
            datas.append(data)
        return datas

    @api.model
    def _set_calendar_last_notif_ack(self):
        self.env.user.partner_id.write({'calendar_last_notif_ack': fields.Datetime.now()})


class CalendarAlarmManager(models.AbstractModel):
    _name = 'calendar.alarm_manager'

    @api.model
    def get_next_potential_limit_alarm(self, seconds, notif=True, mail=True, partner_id=None):
        res = {}
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
                        RIGHT JOIN
                            (
                                SELECT
                                    rel.calendar_event_id, max(alarm.duration_minutes) AS max_delta,min(alarm.duration_minutes) AS min_delta
                                FROM
                                    calendar_alarm_calendar_event_rel AS rel
                                        LEFT JOIN calendar_alarm AS alarm ON alarm.id = rel.calendar_alarm_id
                                WHERE alarm.type in %s
                                GROUP BY rel.calendar_event_id
                            ) AS calcul_delta ON calcul_delta.calendar_event_id = cal.id
             """

        filter_user = """
                RIGHT JOIN calendar_event_res_partner_rel AS part_rel ON part_rel.calendar_event_id = cal.id
                    AND part_rel.res_partner_id = %s
        """

        #Add filter on type
        type_to_read = ()
        if notif:
            type_to_read += ('notification',)
        if mail:
            type_to_read += ('email',)

        tuple_params = (type_to_read,)

        # ADD FILTER ON PARTNER_ID
        if partner_id:
            base_request += filter_user
            tuple_params += (partner_id, )

        #Add filter on hours
        tuple_params += (seconds,)

        self.env.cr.execute("""SELECT *
                        FROM ( %s WHERE cal.active = True ) AS ALL_EVENTS
                       WHERE ALL_EVENTS.first_alarm < (now() at time zone 'utc' + interval '%%s' second )
                         AND ALL_EVENTS.last_event_date > (now() at time zone 'utc')
                   """ % base_request, tuple_params)

        for event_id, first_alarm, last_alarm, first_meeting, last_meeting, min_duration, max_duration, rule in self.env.cr.fetchall():
            res[event_id] = {
                'event_id': event_id,
                'first_alarm': first_alarm,
                'last_alarm': last_alarm,
                'first_meeting': first_meeting,
                'last_meeting': last_meeting,
                'min_duration': min_duration,
                'max_duration': max_duration,
                'rrule': rule
            }

        return res

    @api.model
    def do_check_alarm_for_one_date(self, one_date, event, event_maxdelta, in_the_next_X_seconds, after=False, notif=True, mail=True, missing=False):
        # one_date: date of the event to check (not the same that in the event browse if recurrent)
        # event: Event browse record
        # event_maxdelta: biggest duration from alarms for this event
        # in_the_next_X_seconds: looking in the future (in seconds)
        # after: if not False: will return alert if after this date (date as string - todo: change in master)
        # missing: if not False: will return alert even if we are too late
        # notif: Looking for type notification
        # mail: looking for type email

        res = []

        # TODO: replace notif and email in master by alarm_type + remove event_maxdelta and if using it
        alarm_type = []
        if notif:
            alarm_type.append('notification')
        if mail:
            alarm_type.append('email')

        if one_date - timedelta(minutes=(missing and 0 or event_maxdelta)) < datetime.now() + timedelta(seconds=in_the_next_X_seconds):  # if an alarm is possible for this date
            for alarm in event.alarm_ids.filtered(lambda x: x.type in alarm_type and \
                    one_date - timedelta(minutes=(missing and 0 or x.duration_minutes)) < datetime.now() + timedelta(seconds=in_the_next_X_seconds) and \
                    (not after or one_date - timedelta(minutes=alarm.duration_minutes) > fields.Datetime.from_string(after))):
                alert = {
                    'alarm': alarm.id,
                    'event': event.id,
                    'notify_at': one_date - timedelta(minutes=alarm.duration_minutes),
                }
                res.append(alert)
        return res

    @api.model
    def get_next_mail(self):
        now = fields.Datetime.now()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        last_notif_mail = ICPSudo.get_param('calendar.last_notif_mail', default=False) or now

        cron = self.env.ref('calendar.ir_cron_scheduler_alarm', False)
        if not cron:
            _logger.error("Cron for " + self._name + " can not be identified !")
            return False

        interval_to_second = {
            "weeks": 7 * 24 * 60 * 60,
            "days": 24 * 60 * 60,
            "hours": 60 * 60,
            "minutes": 60,
            "seconds": 1
        }

        if cron.interval_type not in interval_to_second.keys():
            _logger.error("Cron delay can not be computed !")
            return False

        cron_interval = cron.interval_number * interval_to_second[cron.interval_type]

        all_events = self.get_next_potential_limit_alarm(cron_interval, notif=False)

        for curEvent in self.env['calendar.event'].browse(all_events.keys()):
            max_delta = all_events[curEvent.id]['max_duration']

            if curEvent.recurrency:
                at_least_one = False
                last_found = False
                for one_date in curEvent.get_recurrent_date_by_event():
                    in_date_format = one_date.replace(tzinfo=None)
                    last_found = self.do_check_alarm_for_one_date(in_date_format, curEvent, max_delta, 0, after=last_notif_mail, notif=False, missing=True)
                    for alert in last_found:
                        self.do_mail_reminder(alert)
                        at_least_one = True  # if it's the first alarm for this recurrent event
                    if at_least_one and not last_found:  # if the precedent event had an alarm but not this one, we can stop the search for this event
                        break
            else:
                in_date_format = fields.Datetime.from_string(curEvent.start)
                last_found = self.do_check_alarm_for_one_date(in_date_format, curEvent, max_delta, 0, after=last_notif_mail, notif=False, missing=True)
                for alert in last_found:
                    self.do_mail_reminder(alert)
        ICPSudo.set_param('calendar.last_notif_mail', now)

    @api.model
    def get_next_notif(self):
        user = self.env.user
        cal_last_notif_ack = user.calendar_last_notif_ack

        ajax_check_every_seconds = 300
        all_notif = []

        all_events = self.get_next_potential_limit_alarm(ajax_check_every_seconds, partner_id=user.partner_id.id, mail=False)

        for event in all_events:  # .values()
            max_delta = all_events[event]['max_duration']
            curEvent = self.env['calendar.event'].browse(event)
            if curEvent.recurrency:
                bFound = False
                LastFound = False
                for one_date in curEvent.get_recurrent_date_by_event():
                    in_date_format = one_date.replace(tzinfo=None)
                    LastFound = self.do_check_alarm_for_one_date(in_date_format, curEvent, max_delta, ajax_check_every_seconds, after=cal_last_notif_ack, mail=False)
                    if LastFound:
                        for alert in LastFound:
                            all_notif.append(self.do_notif_reminder(alert))
                        if not bFound:  # if it's the first alarm for this recurrent event
                            bFound = True
                    if bFound and not LastFound:  # if the precedent event had alarm but not this one, we can stop the search fot this event
                        break
            else:
                in_date_format = fields.Datetime.from_string(curEvent.start)
                LastFound = self.do_check_alarm_for_one_date(in_date_format, curEvent, max_delta, ajax_check_every_seconds, after=cal_last_notif_ack, mail=False)
                if LastFound:
                    for alert in LastFound:
                        all_notif.append(self.do_notif_reminder(alert))
        return all_notif

    @api.model
    def do_mail_reminder(self, alert):
        res = False

        alarm = self.env['calendar.alarm'].browse(alert['alarm_id'])

        if alarm.type == 'email':
            event = self.env['calendar.event'].browse(alert['event_id'])
            res = event.attendee_ids._send_mail_to_attendees(
                email_from=event.user_id.partner_id.email,
                template_xmlid='calendar_template_meeting_reminder',
                force=True,
            )

        return res

    @api.multi
    def do_notif_reminder(self, alert):
        alarm = self.env['calendar.alarm'].browse(alert['alarm_id'])

        if alarm.type == 'notification':
            event = self.env['calendar.event'].browse(alert['event_id'])
            message = event.display_time

            delta = alert['notify_at'] - datetime.now()
            delta = delta.seconds + delta.days * 3600 * 24

            return {
                'event_id': event.id,
                'title': event.name,
                'message': message,
                'timer': delta,
                'notify_at': fields.Datetime.to_string(alert['notify_at']),
            }


class CalendarAlarm(models.Model):
    _name = 'calendar.alarm'
    _description = 'Event alarm'

    _interval_selection = {'minutes': 'Minute(s)', 'hours': 'Hour(s)', 'days': 'Day(s)'}

    name = fields.Char(required=True)
    type = fields.Selection([('notification', 'Notification'), ('email', 'Email')], default='email', required=True)
    duration = fields.Integer(string='Amount', default=1, required=True)
    interval = fields.Selection(list(_interval_selection.iteritems()), string='Unit', default='hours', required=True)
    duration_minutes = fields.Integer(compute='_compute_duration', string='Duration in minutes', store=True, help="Duration in minutes")

    @api.depends('interval', 'duration')
    def _compute_duration(self):
        for alarm in self:
            if alarm.interval == "minutes":
                alarm.duration_minutes = alarm.duration
            elif alarm.interval == "hours":
                alarm.duration_minutes = alarm.duration * 60
            elif alarm.interval == "days":
                alarm.duration_minutes = alarm.duration * 60 * 24
            else:
                alarm.duration_minutes = 0

    @api.onchange('duration', 'interval')
    def _onchange_duration_interval(self):
        display_interval = self._interval_selection.get(self.interval, '')
        self.name = str(self.duration) + ' ' + display_interval

    def _update_cron(self):
        cron = self.env.ref('calendar.ir_cron_scheduler_alarm', False)
        return cron and cron.toggle(model=self._name, domain=[('type', '=', 'email')])

    @api.model
    def create(self, values):
        res = super(CalendarAlarm, self).create(values)
        self._update_cron()
        return res

    @api.multi
    def write(self, values):
        res = super(CalendarAlarm, self).write(values)
        self._update_cron()
        return res

    @api.multi
    def unlink(self):
        res = super(CalendarAlarm, self).unlink()
        self._update_cron()
        return res


class IrValues(models.Model):
    _inherit = 'ir.values'

    @api.model
    def set(self, key, key2, name, models, value, replace=True, isobject=False, meta=False, preserve_user=False, company=False):
        new_models = []
        for data in models:
            if isinstance(data, (list, tuple)):
                new_models.append((data[0], calendar_id2real_id(data[1])))
            else:
                new_models.append(data)
        return super(IrValues, self).set(key, key2, name, new_models, value, replace, isobject, meta, preserve_user, company)

    @api.model
    def get(self, key, key2, models, meta=False, res_id_req=False, without_user=True, key2_req=True):
        new_models = []
        for data in models:
            if isinstance(data, (list, tuple)):
                new_models.append((data[0], calendar_id2real_id(data[1])))
            else:
                new_models.append(data)
        return super(IrValues, self).get(key, key2, new_models, meta, res_id_req, without_user, key2_req)


class CalendarEventType(models.Model):
    _name = 'calendar.event.type'
    _description = 'Meeting Type'

    name = fields.Char(required=True)

    _sql_constraints = [
            ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class CalendarEvent(models.Model):
    """ Model for Calendar Event """
    _name = 'calendar.event'
    _description = "Event"
    _order = "id desc"
    _inherit = ["mail.thread", "ir.needaction_mixin"]

    @api.model
    def do_run_scheduler(self):
        self.env['calendar.alarm_manager'].get_next_mail()

    @api.v7
    def get_recurrent_date_by_event(self, cr, uid, event, context=None):
        return CalendarEvent.get_recurrent_date_by_event(self.browse(cr, uid, event.id, context=context))

    @api.v8
    def get_recurrent_date_by_event(self):
        """Get recurrent dates based on Rule string and all event where recurrent_id is child
        """
        self.ensure_one()
        timezone = pytz.timezone(self.env.context.get('tz') or 'UTC')

        def todate(date):
            val = parser.parse(''.join((re.compile('\d')).findall(date)))
            ## Dates are localized to saved timezone if any, else current timezone.
            if not val.tzinfo:
                val = pytz.UTC.localize(val)
            return val.astimezone(timezone)

        startdate = pytz.UTC.localize(fields.Datetime.from_string(self.start))  # Add "+hh:mm" timezone
        if not startdate:
            startdate = datetime.now()

        ## Convert the start date to saved timezone (or context tz) as it'll
        ## define the correct hour/day asked by the user to repeat for recurrence.
        startdate = startdate.astimezone(timezone)  # transform "+hh:mm" timezone
        rset1 = rrule.rrulestr(str(self.rrule), dtstart=startdate, forceset=True)
        all_events = self.search([('recurrent_id', '=', self.id), '|', ('active', '=', False), ('active', '=', True)])
        for ev in all_events:
            rset1._exdate.append(todate(ev.recurrent_id_date))
        return [d.astimezone(pytz.UTC) for d in rset1]

    def _get_recurrency_end_date(self):
        self.ensure_one()
        if not self.recurrency:
            return False
        if self.end_type == 'count' and self.count and self.rrule_type and self.stop:
            count = self.count + 1
            delay, mult = {
                'daily': ('days', 1),
                'weekly': ('days', 7),
                'monthly': ('months', 1),
                'yearly': ('years', 1),
            }[self.rrule_type]

            deadline = fields.Datetime.from_string(self.stop)
            return deadline + relativedelta(**{delay: count * mult})
        return self.final_date

    def _find_my_attendee(self):
        """
            Return the first attendee where the user connected has been invited from all the events in `self`.
        """
        for attendee in self.mapped('attendee_ids'):
            if self.env.user.partner_id == attendee.partner_id:
                return attendee
        return False

    @api.model
    def get_date_formats(self):
        lang_params = {}
        if self.env.context.get('lang'):
            lang = self.env['res.lang'].search([("code", "=", self.env.context['lang'])], limit=1)
            if lang:
                lang_params.update(date_format=lang.date_format, time_format=lang.time_format)

        # formats will be used for str{f,p}time() which do not support unicode in Python 2, coerce to str
        format_date = lang_params.get("date_format", '%B-%d-%Y').encode('utf-8')
        format_time = lang_params.get("time_format", '%I-%M %p').encode('utf-8')
        return (format_date, format_time)

    @api.multi
    def get_display_time_tz(self, tz=False):
        self.ensure_one()
        return self.with_context(tz=tz or self.env.context.get('tz'))._get_display_time(self.start, self.stop, self.duration, self.allday)

    @api.model
    def _get_display_time(self, start, stop, zduration, zallday):
        """
            Return date and time (from to from) based on duration with timezone in string :
            eg.
            1) if user add duration for 2 hours, return : August-23-2013 at (04-30 To 06-30) (Europe/Brussels)
            2) if event all day ,return : AllDay, July-31-2013
        """
        tz = self.env.context.get('tz') or self.env.user.tz
        tz = tools.ustr(tz).encode('utf-8')  # make safe for str{p,f}time()
        self = self.with_context(tz=tz)

        format_date, format_time = self.get_date_formats()
        date = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(start))
        date_deadline = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(stop))
        event_date = date.strftime(format_date)
        display_time = date.strftime(format_time)

        if zallday:
            time = _("AllDay , %s") % (event_date)
        elif zduration < 24:
            duration = date + timedelta(hours=zduration)
            time = _("%s at (%s To %s) (%s)") % (event_date, display_time, duration.strftime(format_time), tz)
        else:
            time = _("%s at %s To\n %s at %s (%s)") % (event_date, display_time, date_deadline.strftime(format_date), date_deadline.strftime(format_time), tz)
        return time

    @api.model
    def _get_recurrent_fields(self):
        return ['byday', 'recurrency', 'final_date', 'rrule_type', 'month_by',
                'interval', 'count', 'end_type', 'mo', 'tu', 'we', 'th', 'fr', 'sa',
                'su', 'day', 'week_list']

    @api.depends('final_date')
    def _compute_rulestring(self):
        """
        Gets Recurrence rule string according to value type RECUR of iCalendar from the values given.
        """
        #read these fields as SUPERUSER because if the record is private a normal search could raise an error
        recurrent_fields = self._get_recurrent_fields()
        for event_dict in self.sudo().read(recurrent_fields):
            event = self.browse(event_dict['id'])
            if event_dict['recurrency']:
                event.rrule = self.compute_rule_string(event_dict)
            else:
                event.rrule = ''

    @api.multi
    def _inverse_rulestring(self):
        data = self._get_empty_rrule_data()
        data['recurrency'] = True
        for event in self.filtered(lambda x: x.rrule):
            update_data = self._parse_rrule(event.rrule, dict(data), event.start)
            data.update(update_data)
            for field, value in data.iteritems():
                setattr(event, field, value)

    @api.v7
    def _set_date(self, cr, uid, values, id=False, context=None):
        return CalendarEvent._set_date(self.browse(cr, uid, id, context=context), values)

    @api.v8
    def _set_date(self, values):
        if values.get('start_datetime') or values.get('start_date') or values.get('start') \
                or values.get('stop_datetime') or values.get('stop_date') or values.get('stop'):
            allday = values.get("allday")
            if allday is None:
                if self:
                    allday = self.allday
                else:
                    allday = False
                    _logger.debug("Calendar - All day is not specified, arbitrarily set to False")
                    #raise UserError(_("Need to know if it's an allday or not..."))

            key = "date" if allday else "datetime"
            notkey = "datetime" if allday else "date"

            for fld in ('start', 'stop'):
                if values.get('%s_%s' % (fld, key)) or values.get(fld):
                    values['%s_%s' % (fld, key)] = values.get('%s_%s' % (fld, key)) or values.get(fld)
                    values['%s_%s' % (fld, notkey)] = None
                    if fld not in values.keys():
                        values[fld] = values['%s_%s' % (fld, key)]

            diff = False
            if allday and (values.get('stop_date') or values.get('start_date')):
                stop_date = values.get('stop_date') or self.stop_date
                start_date = values.get('start_date') or self.start_date
                if stop_date and start_date:
                    diff = fields.Date.from_string(stop_date) - fields.Date.from_string(start_date)
            elif values.get('stop_datetime') or values.get('start_datetime'):
                stop_datetime = values.get('stop_datetime') or self.stop_datetime
                start_datetime = values.get('start_datetime') or self.start_datetime
                if stop_datetime and start_datetime:
                    diff = fields.Datetime.from_string(stop_datetime) - fields.Datetime.from_string(start_datetime)
            if diff:
                duration = float(diff.days) * 24 + (float(diff.seconds) / 3600)
                values['duration'] = round(duration, 2)

    def _get_default_partners(self):
        partner_ids = self.env.user.partner_id.ids
        active_id = self.env.context.get('active_id')
        if self.env.context.get('active_model') == 'res.partner' and active_id:
            if active_id not in partner_ids:
                partner_ids.append(active_id)
        return partner_ids

    state = fields.Selection([('draft', 'Unconfirmed'), ('open', 'Confirmed')], string='Status', readonly=True, default='draft', track_visibility='onchange')
    name = fields.Char(string='Meeting Subject', required=True, states={'done': [('readonly', True)]})
    is_attendee = fields.Boolean(compute='_compute_is_attendee', string='Attendee')
    attendee_status = fields.Selection(compute='_compute_attendee_status', string='Attendee Status', selection=CalendarAttendee.STATE_SELECTION)
    display_time = fields.Char(compute='_compute_display_time', string='Event Time')
    display_start = fields.Char(compute='_compute_start', string='Date', store=True)
    allday = fields.Boolean(string='All Day', states={'done': [('readonly', True)]})
    start = fields.Datetime(compute='_compute_start', string='Start', store=True, required=True, help="Start date of an event, without time for full days events")
    stop = fields.Datetime(compute='_compute_stop', string='Stop', store=True, required=True, help="Stop date of an event, without time for full days events")
    start_date = fields.Date(string='Start Date', states={'done': [('readonly', True)]}, track_visibility='onchange')
    start_datetime = fields.Datetime(string='Start DateTime', states={'done': [('readonly', True)]}, track_visibility='onchange')
    stop_date = fields.Date(string='End Date', states={'done': [('readonly', True)]}, track_visibility='onchange')
    stop_datetime = fields.Datetime(string='End Datetime', states={'done': [('readonly', True)]}, track_visibility='onchange')  # old date_deadline
    duration = fields.Float(string='Duration', states={'done': [('readonly', True)]})
    description = fields.Text(string='Description', states={'done': [('readonly', True)]})
    privacy = fields.Selection([('public', 'Everyone'), ('private', 'Only me'), ('confidential', 'Only internal users')], default='public', oldname='class', states={'done': [('readonly', True)]})
    location = fields.Char(help="Location of Event", track_visibility='onchange', states={'done': [('readonly', True)]})
    show_as = fields.Selection([('free', 'Free'), ('busy', 'Busy')], string='Show Time as', default='busy', states={'done': [('readonly', True)]})

    # RECURRENCE FIELD
    rrule = fields.Char(compute='_compute_rulestring', inverse='_inverse_rulestring', store=True, string='Recurrent Rule')
    rrule_type = fields.Selection([('daily', 'Day(s)'), ('weekly', 'Week(s)'), ('monthly', 'Month(s)'), ('yearly', 'Year(s)')], string='Recurrency', states={'done': [('readonly', True)]}, help="Let the event automatically repeat at that interval")
    recurrency = fields.Boolean(string='Recurrent', help="Recurrent Meeting")
    recurrent_id = fields.Integer(string='Recurrent ID')
    recurrent_id_date = fields.Datetime(string='Recurrent ID date')
    end_type = fields.Selection([('count', 'Number of repetitions'), ('end_date', 'End date')], string='Recurrence Termination', default='count')
    interval = fields.Integer(string='Repeat Every', default=1, help="Repeat every (Days/Week/Month/Year)")
    count = fields.Integer(string='Repeat', default=1, help="Repeat x times")
    mo = fields.Boolean(string='Mon')
    tu = fields.Boolean(string='Tue')
    we = fields.Boolean(string='Wed')
    th = fields.Boolean(string='Thu')
    fr = fields.Boolean(string='Fri')
    sa = fields.Boolean(string='Sat')
    su = fields.Boolean(string='Sun')
    month_by = fields.Selection([('date', 'Date of month'), ('day', 'Day of month')], string='Option', default='date', oldname='select1')
    day = fields.Integer(string='Date of month')
    week_list = fields.Selection([('MO', 'Monday'), ('TU', 'Tuesday'), ('WE', 'Wednesday'), ('TH', 'Thursday'), ('FR', 'Friday'), ('SA', 'Saturday'), ('SU', 'Sunday')], string='Weekday')
    byday = fields.Selection([('1', 'First'), ('2', 'Second'), ('3', 'Third'), ('4', 'Fourth'), ('5', 'Fifth'), ('-1', 'Last')], string='By day')
    final_date = fields.Date(string='Repeat Until')  # The last event of a recurrence

    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.uid, states={'done': [('readonly', True)]})
    color_partner_id = fields.Integer(related='user_id.partner_id.id', string="Color index of creator")  # Color of creator
    active = fields.Boolean(default=True, help="If the active field is set to false, it will allow you to hide the event alarm information without removing it.")
    categ_ids = fields.Many2many('calendar.event.type', 'meeting_category_rel', 'event_id', 'type_id', 'Tags')
    attendee_ids = fields.One2many('calendar.attendee', 'event_id', string='Attendees', ondelete='cascade')
    partner_ids = fields.Many2many('res.partner', 'calendar_event_res_partner_rel', string='Attendees', default=_get_default_partners, states={'done': [('readonly', True)]})
    alarm_ids = fields.Many2many('calendar.alarm', 'calendar_alarm_calendar_event_rel', string='Reminders', ondelete="restrict", copy=False)

    @api.depends('attendee_ids', 'attendee_ids.partner_id')
    def _compute_is_attendee(self):
        for meeting in self:
            meeting.is_attendee = bool(meeting._find_my_attendee())

    @api.depends('attendee_ids', 'attendee_ids.partner_id', 'state')
    def _compute_attendee_status(self):
        for meeting in self:
            attendee = meeting._find_my_attendee()
            meeting.attendee_status = attendee.state if attendee else 'needsAction'

    @api.depends('allday', 'duration', 'start', 'stop')
    def _compute_display_time(self):
        for meeting in self:
            meeting.display_time = self._get_display_time(meeting.start, meeting.stop, meeting.duration, meeting.allday)

    @api.depends('allday', 'start_date', 'start_datetime')
    def _compute_start(self):
        for meeting in self:
            meeting.display_start = meeting.start = meeting.start_date if meeting.allday else meeting.start_datetime

    @api.depends('allday', 'stop_date', 'stop_datetime')
    def _compute_stop(self):
        for meeting in self:
            meeting.stop = meeting.stop_date if meeting.allday else meeting.stop_datetime

    @api.constrains('start_date', 'stop_date', 'start_datetime', 'stop_datetime')
    def _check_closing_date(self):
        if self.filtered(lambda x: x.stop < x.start):
            raise ValidationError(_('Error ! End date cannot be set before start date.'))

    @api.onchange('allday')
    def _onchange_allday(self):
        if ((self.start_date and self.stop_date) or (self.start and self.stop)):  # At first intialize, we have not datetime
            if self.allday:  # from datetime to date
                start_datetime = self.start_datetime or self.start

                if start_datetime:
                    self.start_date = start_datetime

                stop_datetime = self.stop_datetime or self.stop
                if stop_datetime:
                    self.stop_date = stop_datetime
            else:  # from date to datetime
                user_tz = self.env.user.tz
                tz = pytz.timezone(user_tz) if user_tz else pytz.utc

                if self.start_date:
                    start = fields.Datetime.from_string(self.start_date)
                    startdate = tz.localize(start)  # Add "+hh:mm" timezone
                    startdate =  startdate.replace(hour=8)  # Set 8 AM in localtime
                    startdate =  startdate.astimezone(pytz.utc)  # Convert to UTC
                    self.start_datetime = fields.Datetime.to_string(startdate)
                elif self.start:
                    self.start_datetime = self.start

                if self.stop_date:
                    stop = fields.Datetime.from_string(self.stop_date)
                    stop_date = tz.localize(stop).replace(hour=18).astimezone(pytz.utc)

                    self.stop_datetime = fields.Datetime.to_string(stop_date)
                elif self.stop:
                    self.stop_datetime = self.stop

    @api.onchange('duration', 'start_datetime')
    def _onchange_duration_start_datetime(self):
        if self.start_datetime and self.duration:
            start = fields.Datetime.from_string(self.start_datetime) + timedelta(hours=self.duration)
            self.stop_date = self.stop = self.stop_datetime = fields.Datetime.to_string(start)
            self.start_date = self.start = self.start_datetime

    @api.onchange('start_date', 'stop_date')
    def _onchange_dates(self):
        if self.allday:
            if self.start_date:
                self.start_datetime = self.start = self.start_date

            if self.stop_date:
                self.stop_datetime = self.stop = self.stop_date

    def new_invitation_token(self):
        return uuid.uuid4().hex

    @api.multi
    def create_attendees(self):
        res = {}
        CalendarAttendee = self.env['calendar.attendee']
        Partner = self.env['res.partner']
        Attendee = self.env["calendar.attendee"]
        current_user = self.env.user
        for event in self:
            attendees = event.attendee_ids.mapped("partner_id")
            new_attendee_ids = []
            res_partner = Partner.browse()
            for partner in event.partner_ids.filtered(lambda x: x not in attendees):
                values = {
                    'partner_id': partner.id,
                    'event_id': event.id,
                    'access_token': self.new_invitation_token(),
                    'email': partner.email,
                }

                if partner == current_user.partner_id:
                    values['state'] = 'accepted'

                attendee = CalendarAttendee.create(values)
                new_attendee_ids.append(attendee.id)
                res_partner += partner

                if not current_user.email or current_user.email != partner.email:
                    mail_from = current_user.email or tools.config.get('email_from')
                    if not self.env.context.get('no_email'):
                        attendee._send_mail_to_attendees(email_from=mail_from)

            if new_attendee_ids:
                event.write({'attendee_ids': [(4, att) for att in new_attendee_ids]})
            if res_partner:
                event.message_subscribe(res_partner.ids)

            # We remove old attendees who are not in partner_ids now.
            all_partners = event.partner_ids
            all_attendees = event.attendee_ids
            all_part_attendees = all_attendees.mapped('partner_id')
            partners_to_remove = (all_part_attendees | res_partner) - all_partners

            attendee_to_remove = Attendee.browse()

            if partners_to_remove:
                attendee_to_remove = attendee_to_remove.search([('partner_id', 'in', partners_to_remove.ids), ('event_id', '=', event.id)])
                if attendee_to_remove:
                    attendee_to_remove.unlink()
            res[event.id] = {
                'new_attendee_ids': new_attendee_ids,
                'old_attendee_ids': all_attendees.ids,
                'removed_attendee_ids': attendee_to_remove.ids
            }
        return res

    @api.v7
    def get_search_fields(self, browse_event, order_fields, r_date=None):
        return CalendarEvent.get_search_fields(browse_event, order_fields, r_date)

    @api.v8
    def get_search_fields(self, order_fields, r_date=None):
        sort_fields = {}
        for ord_field in order_fields:
            if ord_field == 'id' and r_date:
                sort_fields[ord_field] = '%s-%s' % (self[ord_field], r_date.strftime("%Y%m%d%H%M%S"))
            else:
                sort_fields[ord_field] = self[ord_field]
                if isinstance(self[ord_field], models.BaseModel):
                    name_get = self[ord_field].name_get()
                    if len(name_get) and len(name_get[0]) >= 2:
                        sort_fields[ord_field] = name_get[0][1]
        if r_date:
            sort_fields['sort_start'] = r_date.strftime("%Y%m%d%H%M%S")
        else:
            sort_fields['sort_start'] = self.display_start and self.display_start.replace(' ', '').replace('-', '')
        return sort_fields

    @api.multi
    def get_recurrent_ids(self, domain, order=None):

        """Gives virtual event ids for recurring events
        This method gives ids of dates that comes between start date and end date of calendar views

        @param order: The fields (comma separated, format "FIELD {DESC|ASC}") on which the events should be sorted
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
        for event in self:
            if not event.recurrency or not event.rrule:
                result.append(event.id)
                result_data.append(event.get_search_fields(order_fields))
                continue
            rdates = event.get_recurrent_date_by_event()

            for r_date in rdates:
                # fix domain evaluation
                # step 1: check date and replace expression by True or False, replace other expressions by True
                # step 2: evaluation of & and |
                # check if there are one False
                pile = []
                ok = True
                str_r_date = fields.Date.to_string(r_date)
                for arg in domain:
                    if str(arg[0]) in ('start', 'stop', 'final_date'):
                        if (arg[1] == '='):
                            ok = str_r_date == arg[2]
                        if (arg[1] == '>'):
                            ok = str_r_date > arg[2]
                        if (arg[1] == '<'):
                            ok = str_r_date < arg[2]
                        if (arg[1] == '>='):
                            ok = str_r_date >= arg[2]
                        if (arg[1] == '<='):
                            ok = str_r_date <= arg[2]
                        pile.append(ok)
                    elif str(arg) == str('&') or str(arg) == str('|'):
                        pile.append(arg)
                    else:
                        pile.append(True)
                pile.reverse()
                new_pile = []
                for item in pile:
                    if not isinstance(item, basestring):
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
                result_data.append(event.get_search_fields(order_fields, r_date=r_date))

        if order_fields:
            uniq = lambda it: collections.OrderedDict((id(x), x) for x in it).values()

            def comparer(left, right):
                for fn, mult in comparers:
                    result = cmp(fn(left), fn(right))
                    if result:
                        return mult * result
                return 0

            sort_params = [key.split()[0] if key[-4:].lower() != 'desc' else '-%s' % key.split()[0] for key in (order or self._order).split(',')]
            sort_params = uniq([comp if comp not in ['start', 'start_date', 'start_datetime'] else 'sort_start' for comp in sort_params])
            sort_params = uniq([comp if comp not in ['-start', '-start_date', '-start_datetime'] else '-sort_start' for comp in sort_params])
            comparers = [((itemgetter(col[1:]), -1) if col[0] == '-' else (itemgetter(col), 1)) for col in sort_params]
            return [r['id'] for r in sorted(result_data, cmp=comparer)]

    def compute_rule_string(self, data):
        """
        Compute rule string according to value type RECUR of iCalendar from the values given.
        @param self: the object pointer
        @param data: dictionary of freq and interval value
        @return: string containing recurring rule (empty if no rule)
        """
        if data['interval'] and data['interval'] < 0:
            raise UserError(_('interval cannot be negative.'))
        if data['count'] and data['count'] <= 0:
            raise UserError(_('Event recurrence interval cannot be negative.'))

        def get_week_string(freq, data):
            weekdays = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
            if freq == 'weekly':
                byday = map(lambda x: x.upper(), filter(lambda x: data.get(x) and x in weekdays, data))
                if byday:
                    return ';BYDAY=' + ','.join(byday)
            return ''

        def get_month_string(freq, data):
            if freq == 'monthly':
                if data.get('month_by') == 'date' and (data.get('day') < 1 or data.get('day') > 31):
                    raise UserError(_("Please select a proper day of the month."))

                if data.get('month_by') == 'day':  # Eg : Second Monday of the month
                    return ';BYDAY=' + data.get('byday') + data.get('week_list')
                elif data.get('month_by') == 'date':  # Eg : 16th of the month
                    return ';BYMONTHDAY=' + str(data.get('day'))
            return ''

        def get_end_date(data):
            if data.get('final_date'):
                data['end_date_new'] = ''.join((re.compile('\d')).findall(data.get('final_date'))) + 'T235959Z'

            return (data.get('end_type') == 'count' and (';COUNT=' + str(data.get('count'))) or '') +\
                ((data.get('end_date_new') and data.get('end_type') == 'end_date' and (';UNTIL=' + data.get('end_date_new'))) or '')

        freq = data.get('rrule_type')  # day/week/month/year
        res = ''
        if freq:
            interval_srting = data.get('interval') and (';INTERVAL=' + str(data.get('interval'))) or ''
            res = 'FREQ=' + freq.upper() + get_week_string(freq, data) + interval_srting + get_end_date(data) + get_month_string(freq, data)
        return res

    def _get_empty_rrule_data(self):
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

    def _parse_rrule(self, rule, data, date_start):
        day_list = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
        rrule_type = ['yearly', 'monthly', 'weekly', 'daily']
        r = rrule.rrulestr(rule, dtstart=fields.Datetime.from_string(date_start))

        if r._freq > 0 and r._freq < 4:
            data['rrule_type'] = rrule_type[r._freq]
        data['count'] = r._count
        data['interval'] = r._interval
        data['final_date'] = r._until and fields.Datetime.to_string(r._until)
        #repeat weekly
        if r._byweekday:
            for i in xrange(0, 7):
                if i in r._byweekday:
                    data[day_list[i]] = True
            data['rrule_type'] = 'weekly'
        #repeat monthly by nweekday ((weekday, weeknumber), )
        if r._bynweekday:
            data['week_list'] = day_list[r._bynweekday[0][0]].upper()
            data['byday'] = str(r._bynweekday[0][1])
            data['month_by'] = 'day'
            data['rrule_type'] = 'monthly'

        if r._bymonthday:
            data['day'] = r._bymonthday[0]
            data['month_by'] = 'date'
            data['rrule_type'] = 'monthly'

        #repeat yearly but for openerp it's monthly, take same information as monthly but interval is 12 times
        if r._bymonth:
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

    @api.onchange('partner_ids')
    def _onchange_partner_ids(self):
        """ The basic purpose of this method is to check that destination partners
            effectively have email addresses. Otherwise a warning is thrown.
        """
        return self.check_partners_email(self.partner_ids.ids)

    @api.model
    def check_partners_email(self, partner_ids):
        """ Verify that selected partner_ids have an email_address defined.
            Otherwise throw a warning. """
        partners_wo_email = self.env['res.partner'].browse(partner_ids).filtered(lambda x: not x.email)
        if not partners_wo_email:
            return {}
        warning_msg = _('The following contacts have no email address :')
        for partner in partners_wo_email:
            warning_msg += '\n- %s' % (partner.name)
        return {'warning': {
                'title': _('Email addresses not found'),
                'message': warning_msg,
                }}

    # shows events of the day for this user
    @api.model
    def _needaction_domain_get(self):
        return [
            ('stop', '<=', fields.Date.today() + ' 23:59:59'),
            ('start', '>=', fields.Date.today() + ' 00:00:00'),
            ('user_id', '=', self.env.uid),
        ]

    @api.multi
    def message_post(self, **kwargs):
        ctx = self.env.context
        if self.env.context.get('default_date'):
            del ctx['default_date']
        return super(CalendarEvent, self.with_context(ctx).browse(get_real_ids(self.ids))).message_post(**kwargs)

    @api.multi
    def message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None, force=True):
        return super(CalendarEvent, self.browse(get_real_ids(self.ids))).message_subscribe(
            partner_ids=partner_ids,
            channel_ids=channel_ids,
            subtype_ids=subtype_ids,
            force=force)

    @api.multi
    def message_unsubscribe(self, partner_ids=None, channel_ids=None):
        return super(CalendarEvent, self.browse(get_real_ids(self.ids))).message_unsubscribe(partner_ids=partner_ids, channel_ids=channel_ids)

    @api.multi
    def do_sendmail(self):
        my_email = self.env.user.email
        if my_email:
            self.mapped('attendee_ids')._send_mail_to_attendees(email_from=my_email)
        return True

    @api.multi
    def get_attendee(self):
        self.ensure_one()
        # Used for view in controller
        invitation = {'meeting': {}, 'attendee': []}

        invitation['meeting'] = {
            'event': self.name,
            'where': self.location,
            'when': self.display_time
        }

        for attendee in self.attendee_ids:
            invitation['attendee'].append({'name': attendee.cn, 'status': attendee.state})
        return invitation

    @api.model
    def get_interval(self, date, interval, tz=None):
        ''' Format and localize some dates to be used in email templates

            :param string date: date/time to be formatted
            :param string interval: Among 'day', 'month', 'dayname' and 'time' indicating the desired formatting
            :param string tz: Timezone indicator (optional)

            :return unicode: Formatted date or time (as unicode string, to prevent jinja2 crash)

            (Function used only in calendar_event_data.xml) '''

        date = fields.Datetime.from_string(date)

        if tz:
            timezone = pytz.timezone(tz or 'UTC')
            date = date.replace(tzinfo=pytz.timezone('UTC')).astimezone(timezone)

        if interval == 'day':
            # Day number (1-31)
            res = unicode(date.day)

        elif interval == 'month':
            # Localized month name and year
            res = babel_format_date(date=date, format='MMMM y', locale=self.env.context.get('lang', 'en_US'))

        elif interval == 'dayname':
            # Localized day name
            res = babel_format_date(date=date, format='EEEE', locale=self.env.context.get('lang', 'en_US'))

        elif interval == 'time':
            # Localized time

            dummy, format_time = self.get_date_formats()
            res = tools.ustr(date.strftime(format_time + " %Z"))

        return res

    @api.model
    def search(self, args, offset=0, limit=0, order=None, count=False):

        if self.env.context.get('mymeetings'):
            args += [('partner_ids', 'in', [self.env.user.partner_id.id])]

        new_args = []
        for arg in args:
            new_arg = arg

            if arg[0] in ('stop_date', 'stop_datetime', 'stop',) and arg[1] == ">=":
                if self.env.context.get('virtual_id', True):
                    new_args += ['|', '&', ('recurrency', '=', 1), ('final_date', arg[1], arg[2])]
            elif arg[0] == "id":
                new_id = get_real_ids(arg[2])
                new_arg = (arg[0], arg[1], new_id)
            new_args.append(new_arg)

        if not self.env.context.get('virtual_id', True):
            return super(CalendarEvent, self).search(new_args, offset=offset, limit=limit, order=order, count=count)
        # offset, limit, order and count must be treated separately as we may need to deal with virtual ids
        res = super(CalendarEvent, self).search(new_args, offset=0, limit=0, order=None, count=False)
        res = self.browse(res.get_recurrent_ids(args, order=order))
        if count:
            return len(res)
        elif limit:
            return res[offset: offset + limit]
        return res

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        default = default or {}
        self._set_date(default)
        return super(CalendarEvent, self.browse(calendar_id2real_id(self.id))).copy(default)

    @api.multi
    def _detach_one_event(self, values=None):
        values = values or {}
        real_event_id = calendar_id2real_id(self.id)
        data = {
            'allday': self.allday,
            'start': self.start,
            'stop': self.stop,
            'rrule': self.rrule,
            'duration': self.duration
        }
        data['start_date' if data['allday'] else 'start_datetime'] = data['start']
        data['stop_date' if data['allday'] else 'stop_datetime'] = data['stop']
        if data.get('rrule'):
            data.update(
                values,
                recurrent_id=real_event_id,
                recurrent_id_date=data['start'],
                rrule_type=False,
                rrule='',
                recurrency=False,
                final_date=fields.Datetime.from_string(data['start']) + timedelta(hours=values.get('duration') or data['duration'])
            )

            #do not copy the id
            if data.get('id'):
                del(data['id'])
            return self.browse(real_event_id).copy(default=data).id

    @api.multi
    def open_after_detach_event(self):
        self.ensure_one()
        new_id = self._detach_one_event()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.event',
            'view_mode': 'form',
            'res_id': new_id,
            'target': 'current',
            'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}}
        }

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        for arg in args:
            if arg[0] == 'id':
                for n, calendar_id in enumerate(arg[2]):
                    if isinstance(calendar_id, basestring):
                        arg[2][n] = calendar_id.split('-')[0]
        return super(CalendarEvent, self)._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

    @api.multi
    def write(self, values):
        Attendee = self.env['calendar.attendee']
        values0 = values
        # process events one by one
        for event in self:
            # make a copy, since _set_date() modifies values depending on event
            values = dict(values0)
            event._set_date(values)

            # special write of complex IDS
            real_events = new_events = self.browse()
            if '-' not in str(event.id):
                real_events += event
            else:
                real_event = self.browse(calendar_id2real_id(event.id))

                # if we are setting the recurrency flag to False or if we are only changing fields that
                # should be only updated on the real `event` and not on the virtual (like message_follower_ids):
                # then set real `events` to be updated.
                blacklisted = any(key in values for key in ('start', 'stop', 'active'))
                if not values.get('recurrency', True) or not blacklisted:
                    real_events += real_event
                else:
                    if event.rrule:
                        new_events = self.browse(event._detach_one_event(values))
            super(CalendarEvent, real_events).write(values)

            # set end_date for calendar searching
            if values.get('recurrency') and values.get('end_type', 'count') in ('count', unicode('count')) and \
                    (values.get('rrule_type') or values.get('count') or values.get('start') or values.get('stop')):
                for real_cal_event in real_events:
                    final_date = real_cal_event._get_recurrency_end_date()
                    super(CalendarEvent, real_cal_event).write({'final_date': final_date})

            attendees_create = False
            all_events = real_events | new_events
            if values.get('partner_ids'):
                attendees_create = all_events.create_attendees()

            if (values.get('start_date') or values.get('start_datetime')) and values.get('active', True):
                for the_event in all_events:
                    if attendees_create:
                        attendees_create = attendees_create[the_event.id]
                        mail_to_attendees = Attendee.browse(set(attendees_create['old_attendee_ids']) - set(attendees_create['removed_attendee_ids']))
                    else:
                        mail_to_attendees = the_event.attendee_ids

                    if mail_to_attendees:
                        mail_to_attendees._send_mail_to_attendees(template_xmlid='calendar_template_meeting_changedate', email_from=self.env.user.email)

        return True

    @api.model
    def create(self, vals):
        self._set_date(vals)
        if not 'user_id' in vals:  # Else bug with quick_create when we are filter on an other user
            vals['user_id'] = self.env.uid

        event = super(CalendarEvent, self).create(vals)

        final_date = event._get_recurrency_end_date()
        event.write({'final_date': final_date})

        event.create_attendees()
        return event

    @api.multi
    def export_data(self, *args, **kwargs):
        """ Override to convert virtual ids to ids """
        return super(CalendarEvent, self.browse(set(get_real_ids(self.ids)))).export_data(*args, **kwargs)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'date' in groupby:
            raise UserError(_('Group by date is not supported, use the calendar view instead.'))
        return super(CalendarEvent, self.with_context({'virtual_id': False})).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        fields2 = fields or []
        EXTRAFIELDS = ('privacy', 'user_id', 'duration', 'allday', 'start', 'start_date', 'start_datetime', 'rrule')
        for f in EXTRAFIELDS:
            if fields and (f not in fields):
                fields2.append(f)
        select = map(lambda x: (x, calendar_id2real_id(x)), self.ids)
        result = []
        # clearing the cache is required before reading the `message_needaction` compute field(present in event tree view) of inherited `mail.thread` model.
        # This is needed to prevent the traceback(faced only when there are recurrent events defined) when opening the event tree view because the virtual ids
        # will be added back to the `self` of related compute function(thanks to the prefetching mechnism).

        # Note: I think we should call invalidate_cache() from calendar_id2real_id().
        if any(True for id in self.ids if isinstance(id, basestring)):
            self.invalidate_cache()
        real_data = super(CalendarEvent, self.browse([real_id for calendar_id, real_id in select])).read(fields=fields2, load=load)
        real_data = dict(zip([x['id'] for x in real_data], real_data))

        for calendar_id, real_id in select:
            res = real_data[real_id].copy()
            ls = calendar_id2real_id(calendar_id, with_date=res and res.get('duration', 0) > 0 and res.get('duration') or 1)
            if not isinstance(ls, (basestring, int, long)) and len(ls) >= 2:
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
                user_id = isinstance(r['user_id'], (tuple, list)) and r['user_id'][0] or r['user_id']
                if user_id == self.env.uid:
                    continue
            if r['privacy'] == 'private':
                for f in r.keys():
                    recurrent_fields = self._get_recurrent_fields(cr, uid, context=context)
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
        res = False

        events_to_exclude = events_to_unlink = self.browse()

        for event in self:
            if can_be_deleted and len(str(event.id).split('-')) == 1:  # if  ID REAL
                if event.recurrent_id:
                    events_to_exclude += event
                else:
                    events_to_unlink += event
            else:
                events_to_exclude += event

        if events_to_unlink:
            res = super(CalendarEvent, events_to_unlink).unlink()

        if events_to_exclude:
            res = events_to_exclude.write({'active': False})

        return res


class MailMessage(models.Model):
    _inherit = "mail.message"

    @api.model
    def search(self, args, offset=0, limit=0, order=None, count=False):
        '''
        convert the search on real ids in the case it was asked on virtual ids, then call super()
        '''
        for index in range(len(args)):
            if args[index][0] == "res_id":
                if isinstance(args[index][2], basestring):
                    args[index][2] = get_real_ids(args[index][2])
                elif isinstance(args[index][2], list):
                    args[index] = (args[index][0], args[index][1], map(lambda x: get_real_ids(x), args[index][2]))
        return super(MailMessage, self).search(args, offset=offset, limit=limit, order=order, count=count)

    @api.model
    def _find_allowed_model_wise(self, doc_model, doc_dict):
        if doc_model == 'calendar.event':
            order = self.env.context.get('order', self._order)
            recurrent_event_ids = self.env[doc_model].browse(doc_dict.keys()).get_recurrent_ids([], order=order)
            for recurrent_event in self.env[doc_model].browse(recurrent_event_ids):
                doc_dict.setdefault(recurrent_event.id, doc_dict[get_real_ids(recurrent_event.id)])
        return super(MailMessage, self)._find_allowed_model_wise(doc_model, doc_dict)


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model
    def search(self, args, offset=0, limit=0, order=None, count=False):
        '''
        convert the search on real ids in the case it was asked on virtual ids, then call super()
        '''
        for index in range(len(args)):
            if args[index][0] == "res_id" and isinstance(args[index][2], basestring):
                args[index][2] = get_real_ids(args[index][2])
        return super(IrAttachment, self).search(args, offset=offset, limit=limit, order=order, count=count)

    @api.multi
    def write(self, vals):
        '''
        when posting an attachment (new or not), convert the virtual ids in real ids.
        '''
        if isinstance(vals.get('res_id'), basestring):
            vals['res_id'] = get_real_ids(vals['res_id'])
        return super(IrAttachment, self).write(vals)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def _auth_method_calendar(self):
        token = request.params['token']
        db = request.params['db']

        error_message = False
        with registry(db).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, context={})
            attendee = env['calendar.attendee'].search([('access_token', '=', token)], limit=1)
            if not attendee:
                error_message = _("Invalid Invitation Token.")
            elif request.session.uid and request.session.login != 'anonymous':
                # if valid session but user is not match
                user = env['res.users'].browse(request.session.uid)
                if attendee.partner_id != user.partner_id:
                    error_message = _("Invitation cannot be forwarded via email. This event/meeting belongs to %s and you are logged in as %s. Please ask organizer to add you.") % (attendee.email, user.email)

        if error_message:
            raise BadRequest(error_message)

        return True


class InviteWizard(models.TransientModel):
    _inherit = 'mail.wizard.invite'

    @api.model
    def default_get(self, fields):
        '''
        in case someone clicked on 'invite others' wizard in the followers widget, transform virtual ids in real ids
        '''
        context = dict(self.env.context)
        if 'default_res_id' in context:
            context.update(default_res_id=get_real_ids(context['default_res_id']))
        result = super(InviteWizard, self.with_context(context)).default_get(fields)
        if 'res_id' in result:
            result['res_id'] = get_real_ids(result['res_id'])
        return result
