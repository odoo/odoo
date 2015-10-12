# -*- coding: utf-8 -*-

import pytz
import re
import time
import openerp
import openerp.service.report
import uuid
import collections
import babel.dates
from datetime import datetime, timedelta
from dateutil import parser
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from openerp import api
from openerp import tools, SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
from openerp.http import request
from operator import itemgetter
from openerp.exceptions import UserError
from openerp.addons.calendar.models.calendar_attendee import calendar_attendee

import logging
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
                real_date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT, time.strptime(res[1], "%Y%m%d%H%M%S"))
                start = datetime.strptime(real_date, DEFAULT_SERVER_DATETIME_FORMAT)
                end = start + timedelta(hours=with_date)
                return (int(real_id), real_date, end.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            return int(real_id)
    return calendar_id and int(calendar_id) or calendar_id


def get_real_ids(ids):
    if isinstance(ids, (basestring, int, long)):
        return calendar_id2real_id(ids)

    if isinstance(ids, (list, tuple)):
        return [calendar_id2real_id(id) for id in ids]


class calendar_event_type(osv.Model):
    _name = 'calendar.event.type'
    _description = 'Meeting Type'
    _columns = {
        'name': fields.char('Name', required=True),
    }
    _sql_constraints = [
            ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class calendar_event(osv.Model):
    """ Model for Calendar Event """
    _name = 'calendar.event'
    _description = "Event"
    _order = "id desc"
    _inherit = ["mail.thread", "ir.needaction_mixin"]

    def do_run_scheduler(self, cr, uid, id, context=None):
        self.pool['calendar.alarm_manager'].get_next_mail(cr, uid, context=context)

    def get_recurrent_date_by_event(self, cr, uid, event, context=None):
        """Get recurrent dates based on Rule string and all event where recurrent_id is child
        """
        def todate(date):
            val = parser.parse(''.join((re.compile('\d')).findall(date)))
            ## Dates are localized to saved timezone if any, else current timezone.
            if not val.tzinfo:
                val = pytz.UTC.localize(val)
            return val.astimezone(timezone)

        if context is None:
            context = {}

        timezone = pytz.timezone(context.get('tz') or 'UTC')
        startdate = pytz.UTC.localize(datetime.strptime(event.start, DEFAULT_SERVER_DATETIME_FORMAT))  # Add "+hh:mm" timezone
        if not startdate:
            startdate = datetime.now()

        ## Convert the start date to saved timezone (or context tz) as it'll
        ## define the correct hour/day asked by the user to repeat for recurrence.
        startdate = startdate.astimezone(timezone)  # transform "+hh:mm" timezone
        rset1 = rrule.rrulestr(str(event.rrule), dtstart=startdate, forceset=True)
        ids_depending = self.search(cr, uid, [('recurrent_id', '=', event.id), '|', ('active', '=', False), ('active', '=', True)], context=context)
        all_events = self.browse(cr, uid, ids_depending, context=context)
        for ev in all_events:
            rset1._exdate.append(todate(ev.recurrent_id_date))
        return [d.astimezone(pytz.UTC) for d in rset1]

    def _get_recurrency_end_date(self, cr, uid, id, context=None):
        data = self.read(cr, uid, id, ['final_date', 'recurrency', 'rrule_type', 'count', 'end_type', 'stop'], context=context)

        if not data.get('recurrency'):
            return False

        end_type = data.get('end_type')
        final_date = data.get('final_date')
        if end_type == 'count' and all(data.get(key) for key in ['count', 'rrule_type', 'stop']):
            count = data['count'] + 1
            delay, mult = {
                'daily': ('days', 1),
                'weekly': ('days', 7),
                'monthly': ('months', 1),
                'yearly': ('years', 1),
            }[data['rrule_type']]

            deadline = datetime.strptime(data['stop'], tools.DEFAULT_SERVER_DATETIME_FORMAT)
            return deadline + relativedelta(**{delay: count * mult})
        return final_date

    def _find_my_attendee(self, cr, uid, meeting_ids, context=None):
        """
            Return the first attendee where the user connected has been invited from all the meeting_ids in parameters
        """
        user = self.pool['res.users'].browse(cr, uid, uid, context=context)
        for meeting_id in meeting_ids:
            for attendee in self.browse(cr, uid, meeting_id, context).attendee_ids:
                if user.partner_id.id == attendee.partner_id.id:
                    return attendee
        return False

    def get_date_formats(self, cr, uid, context):
        lang = context.get("lang")
        res_lang = self.pool.get('res.lang')
        lang_params = {}
        if lang:
            ids = res_lang.search(request.cr, uid, [("code", "=", lang)])
            if ids:
                lang_params = res_lang.read(request.cr, uid, ids[0], ["date_format", "time_format"])

        # formats will be used for str{f,p}time() which do not support unicode in Python 2, coerce to str
        format_date = lang_params.get("date_format", '%B-%d-%Y').encode('utf-8')
        format_time = lang_params.get("time_format", '%I-%M %p').encode('utf-8')
        return (format_date, format_time)

    def get_display_time_tz(self, cr, uid, ids, tz=False, context=None):
        context = dict(context or {})
        if tz:
            context["tz"] = tz
        ev = self.browse(cr, uid, ids, context=context)[0]
        return self._get_display_time(cr, uid, ev.start, ev.stop, ev.duration, ev.allday, context=context)

    def _get_display_time(self, cr, uid, start, stop, zduration, zallday, context=None):
        """
            Return date and time (from to from) based on duration with timezone in string :
            eg.
            1) if user add duration for 2 hours, return : August-23-2013 at (04-30 To 06-30) (Europe/Brussels)
            2) if event all day ,return : AllDay, July-31-2013
        """
        context = dict(context or {})

        tz = context.get('tz', False)
        if not tz:  # tz can have a value False, so dont do it in the default value of get !
            context['tz'] = self.pool.get('res.users').read(cr, SUPERUSER_ID, uid, ['tz'])['tz']
            tz = context['tz']
        tz = tools.ustr(tz).encode('utf-8') # make safe for str{p,f}time()

        format_date, format_time = self.get_date_formats(cr, uid, context=context)
        date = fields.datetime.context_timestamp(cr, uid, datetime.strptime(start, tools.DEFAULT_SERVER_DATETIME_FORMAT), context=context)
        date_deadline = fields.datetime.context_timestamp(cr, uid, datetime.strptime(stop, tools.DEFAULT_SERVER_DATETIME_FORMAT), context=context)
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

    def _compute(self, cr, uid, ids, fields, arg, context=None):
        res = {}
        if not isinstance(fields, list):
            fields = [fields]
        for meeting in self.browse(cr, uid, ids, context=context):
            meeting_data = {}
            res[meeting.id] = meeting_data
            attendee = self._find_my_attendee(cr, uid, [meeting.id], context)
            for field in fields:
                if field == 'is_attendee':
                    meeting_data[field] = bool(attendee)
                elif field == 'attendee_status':
                    meeting_data[field] = attendee.state if attendee else 'needsAction'
                elif field == 'display_time':
                    meeting_data[field] = self._get_display_time(cr, uid, meeting.start, meeting.stop, meeting.duration, meeting.allday, context=context)
                elif field == "display_start":
                    meeting_data[field] = meeting.start_date if meeting.allday else meeting.start_datetime
                elif field == 'start':
                    meeting_data[field] = meeting.start_date if meeting.allday else meeting.start_datetime
                elif field == 'stop':
                    meeting_data[field] = meeting.stop_date if meeting.allday else meeting.stop_datetime
        return res

    def _get_recurrent_fields(self, cr, uid, context=None):
        return ['byday', 'recurrency', 'final_date', 'rrule_type', 'month_by',
                'interval', 'count', 'end_type', 'mo', 'tu', 'we', 'th', 'fr', 'sa',
                'su', 'day', 'week_list']

    def _get_rulestring(self, cr, uid, ids, name, arg, context=None):
        """
        Gets Recurrence rule string according to value type RECUR of iCalendar from the values given.
        @return: dictionary of rrule value.
        """
        result = {}
        if not isinstance(ids, list):
            ids = [ids]

        #read these fields as SUPERUSER because if the record is private a normal search could raise an error
        recurrent_fields = self._get_recurrent_fields(cr, uid, context=context)
        events = self.read(cr, SUPERUSER_ID, ids, recurrent_fields, context=context)
        for event in events:
            if event['recurrency']:
                result[event['id']] = self.compute_rule_string(event)
            else:
                result[event['id']] = ''

        return result

    # retro compatibility function
    def _rrule_write(self, cr, uid, ids, field_name, field_value, args, context=None):
        return self._set_rulestring(self, cr, uid, ids, field_name, field_value, args, context=context)

    def _set_rulestring(self, cr, uid, ids, field_name, field_value, args, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        data = self._get_empty_rrule_data()
        if field_value:
            data['recurrency'] = True
            for event in self.browse(cr, uid, ids, context=context):
                rdate = event.start
                update_data = self._parse_rrule(field_value, dict(data), rdate)
                data.update(update_data)
                self.write(cr, uid, ids, data, context=context)
        return True

    def _set_date(self, cr, uid, values, id=False, context=None):

        if context is None:
            context = {}

        if values.get('start_datetime') or values.get('start_date') or values.get('start') \
                or values.get('stop_datetime') or values.get('stop_date') or values.get('stop'):
            allday = values.get("allday", None)
            event = self.browse(cr, uid, id, context=context)

            if allday is None:
                if id:
                    allday = event.allday
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
                stop_date = values.get('stop_date') or event.stop_date
                start_date = values.get('start_date') or event.start_date
                if stop_date and start_date:
                    diff = openerp.fields.Date.from_string(stop_date) - openerp.fields.Date.from_string(start_date)
            elif values.get('stop_datetime') or values.get('start_datetime'):
                stop_datetime = values.get('stop_datetime') or event.stop_datetime
                start_datetime = values.get('start_datetime') or event.start_datetime
                if stop_datetime and start_datetime:
                    diff = openerp.fields.Datetime.from_string(stop_datetime) - openerp.fields.Datetime.from_string(start_datetime)
            if diff:
                duration = float(diff.days) * 24 + (float(diff.seconds) / 3600)
                values['duration'] = round(duration, 2)

    _columns = {
        'id': fields.integer('ID', readonly=True),
        'state': fields.selection([('draft', 'Unconfirmed'), ('open', 'Confirmed')], string='Status', readonly=True, track_visibility='onchange'),
        'name': fields.char('Meeting Subject', required=True, states={'done': [('readonly', True)]}),
        'is_attendee': fields.function(_compute, string='Attendee', type="boolean", multi='attendee'),
        'attendee_status': fields.function(_compute, string='Attendee Status', type="selection", selection=calendar_attendee.STATE_SELECTION, multi='attendee'),
        'display_time': fields.function(_compute, string='Event Time', type="char", multi='attendee'),
        'display_start': fields.function(_compute, string='Date', type="char", multi='attendee', store=True),
        'allday': fields.boolean('All Day', states={'done': [('readonly', True)]}),
        'start': fields.function(_compute, fnct_inv=lambda *args: None, string='Start', type="datetime", multi='attendee', store=True, required=True, help="Start date of an event, without time for full days events"),
        'stop': fields.function(_compute, string='Stop', type="datetime", multi='attendee', store=True, required=True, help="Stop date of an event, without time for full days events"),
        'start_date': fields.date('Start Date', states={'done': [('readonly', True)]}, track_visibility='onchange'),
        'start_datetime': fields.datetime('Start DateTime', states={'done': [('readonly', True)]}, track_visibility='onchange'),
        'stop_date': fields.date('End Date', states={'done': [('readonly', True)]}, track_visibility='onchange'),
        'stop_datetime': fields.datetime('End Datetime', states={'done': [('readonly', True)]}, track_visibility='onchange'),  # old date_deadline
        'duration': fields.float('Duration', states={'done': [('readonly', True)]}),
        'description': fields.text('Description', states={'done': [('readonly', True)]}),
        'class': fields.selection([('public', 'Everyone'), ('private', 'Only me'), ('confidential', 'Only internal users')], 'Privacy', states={'done': [('readonly', True)]}),
        'location': fields.char('Location', help="Location of Event", track_visibility='onchange', states={'done': [('readonly', True)]}),
        'show_as': fields.selection([('free', 'Free'), ('busy', 'Busy')], 'Show Time as', states={'done': [('readonly', True)]}),

        # RECURRENCE FIELD
        'rrule': fields.function(_get_rulestring, type='char', fnct_inv=_set_rulestring, store=True, string='Recurrent Rule'),
        'rrule_type': fields.selection([('daily', 'Day(s)'), ('weekly', 'Week(s)'), ('monthly', 'Month(s)'), ('yearly', 'Year(s)')], 'Recurrency', states={'done': [('readonly', True)]}, help="Let the event automatically repeat at that interval"),
        'recurrency': fields.boolean('Recurrent', help="Recurrent Meeting"),
        'recurrent_id': fields.integer('Recurrent ID'),
        'recurrent_id_date': fields.datetime('Recurrent ID date'),
        'end_type': fields.selection([('count', 'Number of repetitions'), ('end_date', 'End date')], 'Recurrence Termination'),
        'interval': fields.integer('Repeat Every', help="Repeat every (Days/Week/Month/Year)"),
        'count': fields.integer('Repeat', help="Repeat x times"),
        'mo': fields.boolean('Mon'),
        'tu': fields.boolean('Tue'),
        'we': fields.boolean('Wed'),
        'th': fields.boolean('Thu'),
        'fr': fields.boolean('Fri'),
        'sa': fields.boolean('Sat'),
        'su': fields.boolean('Sun'),
        'month_by': fields.selection([('date', 'Date of month'), ('day', 'Day of month')], 'Option', oldname='select1'),
        'day': fields.integer('Date of month'),
        'week_list': fields.selection([('MO', 'Monday'), ('TU', 'Tuesday'), ('WE', 'Wednesday'), ('TH', 'Thursday'), ('FR', 'Friday'), ('SA', 'Saturday'), ('SU', 'Sunday')], 'Weekday'),
        'byday': fields.selection([('1', 'First'), ('2', 'Second'), ('3', 'Third'), ('4', 'Fourth'), ('5', 'Fifth'), ('-1', 'Last')], 'By day'),
        'final_date': fields.date('Repeat Until'),  # The last event of a recurrence

        'user_id': fields.many2one('res.users', 'Responsible', states={'done': [('readonly', True)]}),
        'color_partner_id': fields.related('user_id', 'partner_id', 'id', type="integer", string="Color index of creator", store=False),  # Color of creator
        'active': fields.boolean('Active', help="If the active field is set to false, it will allow you to hide the event alarm information without removing it."),
        'categ_ids': fields.many2many('calendar.event.type', 'meeting_category_rel', 'event_id', 'type_id', 'Tags'),
        'attendee_ids': fields.one2many('calendar.attendee', 'event_id', 'Attendees', ondelete='cascade'),
        'partner_ids': fields.many2many('res.partner', 'calendar_event_res_partner_rel', string='Attendees', states={'done': [('readonly', True)]}),
        'alarm_ids': fields.many2many('calendar.alarm', 'calendar_alarm_calendar_event_rel', string='Reminders', ondelete="restrict", copy=False),
    }

    def _get_default_partners(self, cr, uid, ctx=None):
        ret = [self.pool['res.users'].browse(cr, uid, uid, context=ctx).partner_id.id]
        active_id = ctx.get('active_id')
        if ctx.get('active_model') == 'res.partner' and active_id:
            if active_id not in ret:
                ret.append(active_id)
        return ret

    _defaults = {
        'end_type': 'count',
        'count': 1,
        'rrule_type': False,
        'allday': False,
        'state': 'draft',
        'class': 'public',
        'show_as': 'busy',
        'month_by': 'date',
        'interval': 1,
        'active': 1,
        'user_id': lambda self, cr, uid, ctx: uid,
        'partner_ids': _get_default_partners,
    }

    def _check_closing_date(self, cr, uid, ids, context=None):
        for event in self.browse(cr, uid, ids, context=context):
            if event.stop < event.start:
                return False
        return True

    _constraints = [
        (_check_closing_date, 'Error ! End date cannot be set before start date.', ['start_datetime', 'stop_datetime', 'start_date', 'stop_date'])
    ]

    def onchange_allday(self, cr, uid, ids, start=False, end=False, starttime=False, endtime=False, startdatetime=False, enddatetime=False, checkallday=False, context=None):

        value = {}

        if not ((starttime and endtime) or (start and end)):  # At first intialize, we have not datetime
            return value

        if checkallday:  # from datetime to date
            startdatetime = startdatetime or start
            if startdatetime:
                start = datetime.strptime(startdatetime, DEFAULT_SERVER_DATETIME_FORMAT)
                value['start_date'] = datetime.strftime(start, DEFAULT_SERVER_DATE_FORMAT)

            enddatetime = enddatetime or end
            if enddatetime:
                end = datetime.strptime(enddatetime, DEFAULT_SERVER_DATETIME_FORMAT)
                value['stop_date'] = datetime.strftime(end, DEFAULT_SERVER_DATE_FORMAT)
        else:  # from date to datetime
            user = self.pool['res.users'].browse(cr, uid, uid, context)
            tz = pytz.timezone(user.tz) if user.tz else pytz.utc

            if starttime:
                start = openerp.fields.Datetime.from_string(starttime)
                startdate = tz.localize(start)  # Add "+hh:mm" timezone
                startdate = startdate.replace(hour=8)  # Set 8 AM in localtime
                startdate = startdate.astimezone(pytz.utc)  # Convert to UTC
                value['start_datetime'] = datetime.strftime(startdate, DEFAULT_SERVER_DATETIME_FORMAT)
            elif start:
                value['start_datetime'] = start

            if endtime:
                end = datetime.strptime(endtime.split(' ')[0], DEFAULT_SERVER_DATE_FORMAT)
                enddate = tz.localize(end).replace(hour=18).astimezone(pytz.utc)

                value['stop_datetime'] = datetime.strftime(enddate, DEFAULT_SERVER_DATETIME_FORMAT)
            elif end:
                value['stop_datetime'] = end

        return {'value': value}

    def onchange_duration(self, cr, uid, ids, start=False, duration=False, context=None):
        value = {}
        if not (start and duration):
            return value
        start = datetime.strptime(start, DEFAULT_SERVER_DATETIME_FORMAT)
        value['stop_date'] = (start + timedelta(hours=duration)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        value['stop'] = (start + timedelta(hours=duration)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        value['stop_datetime'] = (start + timedelta(hours=duration)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        value['start_date'] = start.strftime(DEFAULT_SERVER_DATE_FORMAT)
        value['start'] = start.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return {'value': value}

    def onchange_dates(self, cr, uid, ids, fromtype, start=False, end=False, checkallday=False, allday=False, context=None):

        """Returns duration and end date based on values passed
        @param ids: List of calendar event's IDs.
        """
        value = {}

        if checkallday != allday:
            return value

        value['allday'] = checkallday  # Force to be rewrited

        if allday:
            if fromtype == 'start' and start:
                start = datetime.strptime(start, DEFAULT_SERVER_DATE_FORMAT)
                value['start_datetime'] = datetime.strftime(start, DEFAULT_SERVER_DATETIME_FORMAT)
                value['start'] = datetime.strftime(start, DEFAULT_SERVER_DATETIME_FORMAT)

            if fromtype == 'stop' and end:
                end = datetime.strptime(end, DEFAULT_SERVER_DATE_FORMAT)
                value['stop_datetime'] = datetime.strftime(end, DEFAULT_SERVER_DATETIME_FORMAT)
                value['stop'] = datetime.strftime(end, DEFAULT_SERVER_DATETIME_FORMAT)

        return {'value': value}

    def new_invitation_token(self, cr, uid, record, partner_id):
        return uuid.uuid4().hex

    def create_attendees(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        user_obj = self.pool['res.users']
        current_user = user_obj.browse(cr, uid, uid, context=context)
        res = {}
        for event in self.browse(cr, uid, ids, context):
            attendees = {}
            for att in event.attendee_ids:
                attendees[att.partner_id.id] = True
            new_attendees = []
            new_att_partner_ids = []
            for partner in event.partner_ids:
                if partner.id in attendees:
                    continue
                access_token = self.new_invitation_token(cr, uid, event, partner.id)
                values = {
                    'partner_id': partner.id,
                    'event_id': event.id,
                    'access_token': access_token,
                    'email': partner.email,
                }

                if partner.id == current_user.partner_id.id:
                    values['state'] = 'accepted'

                att_id = self.pool['calendar.attendee'].create(cr, uid, values, context=context)
                new_attendees.append(att_id)
                new_att_partner_ids.append(partner.id)

                if not current_user.email or current_user.email != partner.email:
                    mail_from = current_user.email or tools.config.get('email_from', False)
                    if not context.get('no_email'):
                        self.pool['calendar.attendee']._send_mail_to_attendees(cr, uid, att_id, email_from=mail_from, context=context)

            if new_attendees:
                self.write(cr, uid, [event.id], {'attendee_ids': [(4, att) for att in new_attendees]}, context=context)
            if new_att_partner_ids:
                self.message_subscribe(cr, uid, [event.id], new_att_partner_ids, context=context)

            # We remove old attendees who are not in partner_ids now.
            all_partner_ids = [part.id for part in event.partner_ids]
            all_part_attendee_ids = [att.partner_id.id for att in event.attendee_ids]
            all_attendee_ids = [att.id for att in event.attendee_ids]
            partner_ids_to_remove = map(lambda x: x, set(all_part_attendee_ids + new_att_partner_ids) - set(all_partner_ids))

            attendee_ids_to_remove = []

            if partner_ids_to_remove:
                attendee_ids_to_remove = self.pool["calendar.attendee"].search(cr, uid, [('partner_id.id', 'in', partner_ids_to_remove), ('event_id.id', '=', event.id)], context=context)
                if attendee_ids_to_remove:
                    self.pool['calendar.attendee'].unlink(cr, uid, attendee_ids_to_remove, context)

            res[event.id] = {
                'new_attendee_ids': new_attendees,
                'old_attendee_ids': all_attendee_ids,
                'removed_attendee_ids': attendee_ids_to_remove
            }
        return res

    def get_search_fields(self, browse_event, order_fields, r_date=None):
        sort_fields = {}
        for ord in order_fields:
            if ord == 'id' and r_date:
                sort_fields[ord] = '%s-%s' % (browse_event[ord], r_date.strftime("%Y%m%d%H%M%S"))
            else:
                sort_fields[ord] = browse_event[ord]
                if type(browse_event[ord]) is openerp.osv.orm.browse_record:
                    name_get = browse_event[ord].name_get()
                    if len(name_get) and len(name_get[0]) >= 2:
                        sort_fields[ord] = name_get[0][1]
        if r_date:
            sort_fields['sort_start'] = r_date.strftime("%Y%m%d%H%M%S")
        else:
            display_start = browse_event['display_start']
            sort_fields['sort_start'] = display_start and display_start.replace(' ', '').replace('-', '') or False
        return sort_fields

    def get_recurrent_ids(self, cr, uid, event_id, domain, order=None, context=None):

        """Gives virtual event ids for recurring events
        This method gives ids of dates that comes between start date and end date of calendar views

        @param order: The fields (comma separated, format "FIELD {DESC|ASC}") on which the events should be sorted
        """
        if not context:
            context = {}

        if isinstance(event_id, (basestring, int, long)):
            ids_to_browse = [event_id]  # keep select for return
        else:
            ids_to_browse = event_id

        if order:
            order_fields = [field.split()[0] for field in order.split(',')]
        else:
            # fallback on self._order defined on the model
            order_fields = [field.split()[0] for field in self._order.split(',')]

        if 'id' not in order_fields:
            order_fields.append('id')

        result_data = []
        result = []
        for ev in self.browse(cr, uid, ids_to_browse, context=context):
            if not ev.recurrency or not ev.rrule:
                result.append(ev.id)
                result_data.append(self.get_search_fields(ev, order_fields))
                continue
            rdates = self.get_recurrent_date_by_event(cr, uid, ev, context=context)

            for r_date in rdates:
                # fix domain evaluation
                # step 1: check date and replace expression by True or False, replace other expressions by True
                # step 2: evaluation of & and |
                # check if there are one False
                pile = []
                ok = True
                for arg in domain:
                    if str(arg[0]) in ('start', 'stop', 'final_date'):
                        if (arg[1] == '='):
                            ok = r_date.strftime('%Y-%m-%d') == arg[2]
                        if (arg[1] == '>'):
                            ok = r_date.strftime('%Y-%m-%d') > arg[2]
                        if (arg[1] == '<'):
                            ok = r_date.strftime('%Y-%m-%d') < arg[2]
                        if (arg[1] == '>='):
                            ok = r_date.strftime('%Y-%m-%d') >= arg[2]
                        if (arg[1] == '<='):
                            ok = r_date.strftime('%Y-%m-%d') <= arg[2]
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
                result_data.append(self.get_search_fields(ev, order_fields, r_date=r_date))

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
            ids = [r['id'] for r in sorted(result_data, cmp=comparer)]

        if isinstance(event_id, (basestring, int, long)):
            return ids and ids[0] or False
        else:
            return ids

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

        freq = data.get('rrule_type', False)  # day/week/month/year
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
        r = rrule.rrulestr(rule, dtstart=datetime.strptime(date_start, DEFAULT_SERVER_DATETIME_FORMAT))

        if r._freq > 0 and r._freq < 4:
            data['rrule_type'] = rrule_type[r._freq]
        data['count'] = r._count
        data['interval'] = r._interval
        data['final_date'] = r._until and r._until.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
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

    def onchange_partner_ids(self, cr, uid, ids, value, context=None):
        """ The basic purpose of this method is to check that destination partners
            effectively have email addresses. Otherwise a warning is thrown.
            :param value: value format: [[6, 0, [3, 4]]]
        """
        res = {'value': {}}

        if not value or not value[0] or not value[0][0] == 6:
            return

        res.update(self.check_partners_email(cr, uid, value[0][2], context=context))
        return res

    def check_partners_email(self, cr, uid, partner_ids, context=None):
        """ Verify that selected partner_ids have an email_address defined.
            Otherwise throw a warning. """
        partner_wo_email_lst = []
        for partner in self.pool['res.partner'].browse(cr, uid, partner_ids, context=context):
            if not partner.email:
                partner_wo_email_lst.append(partner)
        if not partner_wo_email_lst:
            return {}
        warning_msg = _('The following contacts have no email address :')
        for partner in partner_wo_email_lst:
            warning_msg += '\n- %s' % (partner.name)
        return {'warning': {
                'title': _('Email addresses not found'),
                'message': warning_msg,
                }}

    # shows events of the day for this user
    def _needaction_domain_get(self, cr, uid, context=None):
        return [
            ('stop', '<=', time.strftime(DEFAULT_SERVER_DATE_FORMAT + ' 23:59:59')),
            ('start', '>=', time.strftime(DEFAULT_SERVER_DATE_FORMAT + ' 00:00:00')),
            ('user_id', '=', uid),
        ]

    @api.cr_uid_ids_context
    def message_post(self, cr, uid, thread_id, context=None, **kwargs):
        if isinstance(thread_id, basestring):
            thread_id = get_real_ids(thread_id)
        if context.get('default_date'):
            del context['default_date']
        return super(calendar_event, self).message_post(cr, uid, thread_id, context=context, **kwargs)

    def message_subscribe(self, cr, uid, ids, partner_ids=None, channel_ids=None, subtype_ids=None, force=True, context=None):
        return super(calendar_event, self).message_subscribe(
            cr, uid, get_real_ids(ids),
            partner_ids=partner_ids,
            channel_ids=channel_ids,
            subtype_ids=subtype_ids,
            force=force,
            context=context)

    def message_unsubscribe(self, cr, uid, ids, partner_ids=None, channel_ids=None, context=None):
        return super(calendar_event, self).message_unsubscribe(cr, uid, get_real_ids(ids), partner_ids=partner_ids, channel_ids=channel_ids, context=context)

    def do_sendmail(self, cr, uid, ids, context=None):
        for event in self.browse(cr, uid, ids, context):
            current_user = self.pool['res.users'].browse(cr, uid, uid, context=context)

            if current_user.email:
                self.pool['calendar.attendee']._send_mail_to_attendees(cr, uid, [att.id for att in event.attendee_ids], email_from=current_user.email, context=context)
        return

    def get_attendee(self, cr, uid, meeting_id, context=None):
        # Used for view in controller
        invitation = {'meeting': {}, 'attendee': []}

        meeting = self.browse(cr, uid, int(meeting_id), context=context)
        invitation['meeting'] = {
            'event': meeting.name,
            'where': meeting.location,
            'when': meeting.display_time
        }

        for attendee in meeting.attendee_ids:
            invitation['attendee'].append({'name': attendee.cn, 'status': attendee.state})
        return invitation

    def get_interval(self, cr, uid, ids, date, interval, tz=None, context=None):
        ''' Format and localize some dates to be used in email templates

            :param string date: date/time to be formatted
            :param string interval: Among 'day', 'month', 'dayname' and 'time' indicating the desired formatting
            :param string tz: Timezone indicator (optional)

            :return unicode: Formatted date or time (as unicode string, to prevent jinja2 crash)

            (Function used only in calendar_event_data.xml) '''

        date = openerp.fields.Datetime.from_string(date)

        if tz:
            timezone = pytz.timezone(tz or 'UTC')
            date = date.replace(tzinfo=pytz.timezone('UTC')).astimezone(timezone)

        if interval == 'day':
            # Day number (1-31)
            res = unicode(date.day)

        elif interval == 'month':
            # Localized month name and year
            res = babel.dates.format_date(date=date, format='MMMM y', locale=context.get('lang', 'en_US'))

        elif interval == 'dayname':
            # Localized day name
            res = babel.dates.format_date(date=date, format='EEEE', locale=context.get('lang', 'en_US'))

        elif interval == 'time':
            # Localized time

            dummy, format_time = self.get_date_formats(cr, uid, context=context)
            res = tools.ustr(date.strftime(format_time + " %Z"))

        return res

    def search(self, cr, uid, args, offset=0, limit=0, order=None, context=None, count=False):
        if context is None:
            context = {}

        if context.get('mymeetings', False):
            partner_id = self.pool['res.users'].browse(cr, uid, uid, context).partner_id.id
            args += [('partner_ids', 'in', [partner_id])]

        new_args = []
        for arg in args:
            new_arg = arg

            if arg[0] in ('stop_date', 'stop_datetime', 'stop',) and arg[1] == ">=":
                if context.get('virtual_id', True):
                    new_args += ['|', '&', ('recurrency', '=', 1), ('final_date', arg[1], arg[2])]
            elif arg[0] == "id":
                new_id = get_real_ids(arg[2])
                new_arg = (arg[0], arg[1], new_id)
            new_args.append(new_arg)

        if not context.get('virtual_id', True):
            return super(calendar_event, self).search(cr, uid, new_args, offset=offset, limit=limit, order=order, count=count, context=context)

        # offset, limit, order and count must be treated separately as we may need to deal with virtual ids
        res = super(calendar_event, self).search(cr, uid, new_args, offset=0, limit=0, order=None, context=context, count=False)
        res = self.get_recurrent_ids(cr, uid, res, args, order=order, context=context)
        if count:
            return len(res)
        elif limit:
            return res[offset: offset + limit]
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        self._set_date(cr, uid, default, id=default.get('id'), context=context)
        return super(calendar_event, self).copy(cr, uid, calendar_id2real_id(id), default, context)

    def _detach_one_event(self, cr, uid, id, values=dict(), context=None):
        real_event_id = calendar_id2real_id(id)
        data = self.read(cr, uid, id, ['allday', 'start', 'stop', 'rrule', 'duration'])
        data['start_date' if data['allday'] else 'start_datetime'] = data['start']
        data['stop_date' if data['allday'] else 'stop_datetime'] = data['stop']
        if data.get('rrule'):
            data.update(
                values,
                recurrent_id=real_event_id,
                recurrent_id_date=data.get('start'),
                rrule_type=False,
                rrule='',
                recurrency=False,
                final_date=datetime.strptime(data.get('start'), DEFAULT_SERVER_DATETIME_FORMAT if data['allday'] else DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=values.get('duration', False) or data.get('duration'))
            )

            #do not copy the id
            if data.get('id'):
                del(data['id'])
            new_id = self.copy(cr, uid, real_event_id, default=data, context=context)
            return new_id

    def open_after_detach_event(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        new_id = self._detach_one_event(cr, uid, ids[0], context=context)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.event',
            'view_mode': 'form',
            'res_id': new_id,
            'target': 'current',
            'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}}
        }

    def _name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100, name_get_uid=None):
        for arg in args:
            if arg[0] == 'id':
                for n, calendar_id in enumerate(arg[2]):
                    if isinstance(calendar_id, basestring):
                        arg[2][n] = calendar_id.split('-')[0]
        return super(calendar_event, self)._name_search(cr, user, name=name, args=args, operator=operator, context=context, limit=limit, name_get_uid=name_get_uid)

    def write(self, cr, uid, ids, values, context=None):
        context = context or {}
        if not isinstance(ids, (tuple, list)):
            ids = [ids]

        values0 = values

        # process events one by one
        for event_id in ids:
            # make a copy, since _set_date() modifies values depending on event
            values = dict(values0)
            self._set_date(cr, uid, values, event_id, context=context)

            # special write of complex IDS
            real_ids = []
            new_ids = []
            if '-' not in str(event_id):
                real_ids = [int(event_id)]
            else:
                real_event_id = calendar_id2real_id(event_id)

                # if we are setting the recurrency flag to False or if we are only changing fields that
                # should be only updated on the real ID and not on the virtual (like message_follower_ids):
                # then set real ids to be updated.
                blacklisted = any(key in values for key in ('start', 'stop', 'active'))
                if not values.get('recurrency', True) or not blacklisted:
                    real_ids = [real_event_id]
                else:
                    data = self.read(cr, uid, event_id, ['start', 'stop', 'rrule', 'duration'])
                    if data.get('rrule'):
                        new_ids = [self._detach_one_event(cr, uid, event_id, values, context=None)]

            super(calendar_event, self).write(cr, uid, real_ids, values, context=context)

            # set end_date for calendar searching
            if values.get('recurrency') and values.get('end_type', 'count') in ('count', unicode('count')) and \
                    (values.get('rrule_type') or values.get('count') or values.get('start') or values.get('stop')):
                for id in real_ids:
                    final_date = self._get_recurrency_end_date(cr, uid, id, context=context)
                    super(calendar_event, self).write(cr, uid, [id], {'final_date': final_date}, context=context)

            attendees_create = False
            if values.get('partner_ids', False):
                attendees_create = self.create_attendees(cr, uid, real_ids + new_ids, context)

            if (values.get('start_date') or values.get('start_datetime')) and values.get('active', True):
                for the_id in real_ids + new_ids:
                    if attendees_create:
                        attendees_create = attendees_create[the_id]
                        mail_to_ids = list(set(attendees_create['old_attendee_ids']) - set(attendees_create['removed_attendee_ids']))
                    else:
                        mail_to_ids = [att.id for att in self.browse(cr, uid, the_id, context=context).attendee_ids]

                    if mail_to_ids:
                        current_user = self.pool['res.users'].browse(cr, uid, uid, context=context)
                        self.pool['calendar.attendee']._send_mail_to_attendees(cr, uid, mail_to_ids, template_xmlid='calendar_template_meeting_changedate', email_from=current_user.email, context=context)

        return True

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}

        self._set_date(cr, uid, vals, id=False, context=context)
        if not 'user_id' in vals:  # Else bug with quick_create when we are filter on an other user
            vals['user_id'] = uid

        res = super(calendar_event, self).create(cr, uid, vals, context=context)

        final_date = self._get_recurrency_end_date(cr, uid, res, context=context)
        self.write(cr, uid, [res], {'final_date': final_date}, context=context)

        self.create_attendees(cr, uid, [res], context=context)
        return res

    def export_data(self, cr, uid, ids, *args, **kwargs):
        """ Override to convert virtual ids to ids """
        real_ids = []
        for real_id in get_real_ids(ids):
            if real_id not in real_ids:
                real_ids.append(real_id)
        return super(calendar_event, self).export_data(cr, uid, real_ids, *args, **kwargs)

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        context = dict(context or {})

        if 'date' in groupby:
            raise UserError(_('Group by date is not supported, use the calendar view instead.'))
        virtual_id = context.get('virtual_id', True)
        context.update({'virtual_id': False})
        res = super(calendar_event, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby, lazy=lazy)
        return res

    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        if context is None:
            context = {}
        fields2 = fields and fields[:] or None
        EXTRAFIELDS = ('class', 'user_id', 'duration', 'allday', 'start', 'start_date', 'start_datetime', 'rrule')
        for f in EXTRAFIELDS:
            if fields and (f not in fields):
                fields2.append(f)
        if isinstance(ids, (basestring, int, long)):
            select = [ids]
        else:
            select = ids
        select = map(lambda x: (x, calendar_id2real_id(x)), select)
        result = []
        real_data = super(calendar_event, self).read(cr, uid, [real_id for calendar_id, real_id in select], fields=fields2, context=context, load=load)
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
                    res['display_time'] = self._get_display_time(cr, uid, ls[1], ls[2], res['duration'], res['allday'], context=context)

            res['id'] = calendar_id
            result.append(res)

        for r in result:
            if r['user_id']:
                user_id = type(r['user_id']) in (tuple, list) and r['user_id'][0] or r['user_id']
                if user_id == uid:
                    continue
            if r['class'] == 'private':
                for f in r.keys():
                    if f not in ('id', 'allday', 'start', 'stop', 'duration', 'user_id', 'state', 'interval', 'count', 'recurrent_id_date', 'rrule'):
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
        if isinstance(ids, (basestring, int, long)):
            return result and result[0] or False
        return result

    def unlink(self, cr, uid, ids, can_be_deleted=True, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        res = False

        ids_to_exclure = []
        ids_to_unlink = []

        for event_id in ids:
            if can_be_deleted and len(str(event_id).split('-')) == 1:  # if  ID REAL
                if self.browse(cr, uid, int(event_id), context).recurrent_id:
                    ids_to_exclure.append(event_id)
                else:
                    ids_to_unlink.append(int(event_id))
            else:
                ids_to_exclure.append(event_id)

        if ids_to_unlink:
            res = super(calendar_event, self).unlink(cr, uid, ids_to_unlink, context=context)

        if ids_to_exclure:
            for id_to_exclure in ids_to_exclure:
                res = self.write(cr, uid, id_to_exclure, {'active': False}, context=context)

        return res
