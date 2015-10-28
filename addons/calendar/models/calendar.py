# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import collections
import logging
import re
import uuid
from datetime import timedelta

import babel.dates
import pytz
from dateutil import parser, rrule
from dateutil.relativedelta import relativedelta
from operator import itemgetter

import odoo
import odoo.service.report
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

from ..models.calendar_attendee import CalendarAttendee

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
                real_date = fields.Datetime.to_string(fields.datetime.strptime(res[1],  "%Y%m%d%H%M%S"))
                end = fields.Datetime.from_string(real_date) + timedelta(hours=with_date)
                return (int(real_id), real_date, fields.Datetime.to_string(end))
            return int(real_id)
    return calendar_id and int(calendar_id) or calendar_id


def get_real_ids(ids):
    if isinstance(ids, (basestring, int, long)):
        return calendar_id2real_id(ids)

    if isinstance(ids, (list, tuple)):
        return [calendar_id2real_id(id) for id in ids]


class CalendarEventType(models.Model):
    _name = 'calendar.event.type'
    _description = 'Meeting Type'

    name = fields.Char(required=True)

    _sql_constraints = [('name_uniq', 'unique (name)', "Tag name already exists !")]


class CalendarEvent(models.Model):
    """ Model for Calendar Event """
    _name = 'calendar.event'
    _description = "Event"
    _order = "id desc"
    _inherit = ["mail.thread", "ir.needaction_mixin"]

    def do_run_scheduler(self):
        self.env['calendar.alarm_manager'].get_next_mail()

    def get_recurrent_date_by_event(self):
        """Get recurrent dates based on Rule string and all event where recurrent_id is child
        """

        def todate(date):
            val = parser.parse(''.join((re.compile('\d')).findall(date)))
            ## Dates are localized to saved timezone if any, else current timezone.
            if not val.tzinfo:
                val = pytz.UTC.localize(val)
            return val.astimezone(pytz.timezone(self.env.context.get('tz') or 'UTC'))

        startdate = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(self.start))
        rset1 = rrule.rrulestr(str(self.rrule), dtstart=startdate, forceset=True)
        all_events = self.with_context(active_test=False).search([('recurrent_id', '=', self.id)])
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
            Return the first attendee where the user connected has been invited from all the meeting_ids in parameters
        """
        for event in self:
            for attendee in event.attendee_ids:
                if self.env.user.partner_id.id == attendee.partner_id.id:
                    return attendee
        return False

    def get_date_formats(self):
        lang = self.env.lang
        lang_params = {}
        if lang:
            res_lang = self.env['res.lang'].search([("code", "=", lang)])
            if res_lang:
                lang_params = {
                    'date_format': res_lang.date_format,
                    'time_format': res_lang.time_format}

        # formats will be used for str{f,p}time() which do not support unicode in Python 2, coerce to str
        format_date = lang_params.get("date_format", '%B-%d-%Y').encode('utf-8')
        format_time = lang_params.get("time_format", '%I-%M %p').encode('utf-8')
        return (format_date, format_time)

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
        tz = self.env.context.get('tz')
        if not tz:  # tz can have a value False, so dont do it in the default value of get !
            tz = self.env.context.get('tz') or self.env.user.tz
        tz = tools.ustr(tz).encode('utf-8')  # make safe for str{p,f}time()

        format_date, format_time = self.with_context(tz=tz).get_date_formats()
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
    def _get_rulestring(self):
        """
        Gets Recurrence rule string according to value type RECUR of iCalendar from the values given.
        @return: dictionary of rrule value.
        """

        #read these fields as SUPERUSER because if the record is private a normal search could raise an error
        recurrent_fields = self._get_recurrent_fields()
        events = self.sudo().read(recurrent_fields)
        for event in events:
            if event['recurrency']:
                rrule = self.compute_rule_string(event)
                self.browse(event['id']).rrule = rrule
            else:
                self.browse(event['id']).rrule = ''

    # retro compatibility function
    def _rrule_write(self):
        return self._set_rulestring(self)

    @api.multi
    def _set_rulestring(self):
        data = self._get_empty_rrule_data()
        if self.rrule:
            data['recurrency'] = True
            for event in self:
                update_data = self._parse_rrule(self.rrule, dict(data), event.start)
                data.update(update_data)
            self.write(data)
        return True

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
        ret = self.env.user.partner_id.ids
        active_id = self.env.context.get('active_id')
        if self.env.context.get('active_model') == 'res.partner' and active_id:
            if active_id not in ret:
                ret.append(active_id)
        return ret

    state = fields.Selection([('draft', 'Unconfirmed'), ('open', 'Confirmed')], string='Status', readonly=True, default='draft', track_visibility='onchange')
    name = fields.Char('Meeting Subject', required=True, states={'done': [('readonly', True)]})
    is_attendee = fields.Boolean(compute='_compute_is_attendee', string='Attendee')
    attendee_status = fields.Selection(compute='_compute_attendee_status', string='Attendee Status', selection=CalendarAttendee.STATE_SELECTION)
    display_time = fields.Char(compute='_compute_display_time', string='Event Time')
    display_start = fields.Char(compute='_compute_start', string='Date', store=True)
    allday = fields.Boolean('All Day', states={'done': [('readonly', True)]})
    start = fields.Datetime(compute='_compute_start', inverse=lambda *args: None, string='Start', store=True, required=True, help="Start date of an event, without time for full days events")
    stop = fields.Datetime(compute='_compute_stop', string='Stop', store=True, required=True, help="Stop date of an event, without time for full days events")
    start_date = fields.Date('Start Date', states={'done': [('readonly', True)]}, track_visibility='onchange')
    start_datetime = fields.Datetime('Start DateTime', states={'done': [('readonly', True)]}, track_visibility='onchange')
    stop_date = fields.Date('End Date', states={'done': [('readonly', True)]}, track_visibility='onchange')
    stop_datetime = fields.Datetime('End Datetime', states={'done': [('readonly', True)]}, track_visibility='onchange')  # old date_deadline
    duration = fields.Float('Duration', states={'done': [('readonly', True)]})
    description = fields.Text('Description', states={'done': [('readonly', True)]})
    privacy = fields.Selection([('public', 'Everyone'), ('private', 'Only me'), ('confidential', 'Only internal users')], default='public', oldname='class', states={'done': [('readonly', True)]})
    location = fields.Char(help="Location of Event", track_visibility='onchange', states={'done': [('readonly', True)]})
    show_as = fields.Selection([('free', 'Free'), ('busy', 'Busy')], 'Show Time as', default='busy', states={'done': [('readonly', True)]})

    # RECURRENCE FIELD
    rrule = fields.Char(compute='_get_rulestring', inverse='_set_rulestring', store=True, string='Recurrent Rule')
    rrule_type = fields.Selection([('daily', 'Day(s)'), ('weekly', 'Week(s)'), ('monthly', 'Month(s)'), ('yearly', 'Year(s)')], 'Recurrency', states={'done': [('readonly', True)]}, help="Let the event automatically repeat at that interval")
    recurrency = fields.Boolean('Recurrent', help="Recurrent Meeting")
    recurrent_id = fields.Integer('Recurrent ID')
    recurrent_id_date = fields.Datetime('Recurrent ID date')
    end_type = fields.Selection([('count', 'Number of repetitions'), ('end_date', 'End date')], 'Recurrence Termination', default='count')
    interval = fields.Integer('Repeat Every', default=1, help="Repeat every (Days/Week/Month/Year)")
    count = fields.Integer('Repeat', default=1, help="Repeat x times")
    mo = fields.Boolean('Mon')
    tu = fields.Boolean('Tue')
    we = fields.Boolean('Wed')
    th = fields.Boolean('Thu')
    fr = fields.Boolean('Fri')
    sa = fields.Boolean('Sat')
    su = fields.Boolean('Sun')
    month_by = fields.Selection([('date', 'Date of month'), ('day', 'Day of month')], string='Option', default='date', oldname='select1')
    day = fields.Integer('Date of month')
    week_list = fields.Selection([('MO', 'Monday'), ('TU', 'Tuesday'), ('WE', 'Wednesday'), ('TH', 'Thursday'), ('FR', 'Friday'), ('SA', 'Saturday'), ('SU', 'Sunday')], 'Weekday')
    byday = fields.Selection([('1', 'First'), ('2', 'Second'), ('3', 'Third'), ('4', 'Fourth'), ('5', 'Fifth'), ('-1', 'Last')], 'By day')
    final_date = fields.Date('Repeat Until')  # The last event of a recurrence

    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.uid, states={'done': [('readonly', True)]})
    color_partner_id = fields.Many2one(related='user_id.partner_id', string="Color index of creator")  # Color of creator
    active = fields.Boolean(default=True, help="If the active field is set to false, it will allow you to hide the event alarm information without removing it.")
    categ_ids = fields.Many2many('calendar.event.type', 'meeting_category_rel', 'event_id', 'type_id', 'Tags')
    attendee_ids = fields.One2many('calendar.attendee', 'event_id', 'Attendees', ondelete='cascade')
    partner_ids = fields.Many2many('res.partner', 'calendar_event_res_partner_rel', string='Attendees', default=_get_default_partners, states={'done': [('readonly', True)]})
    alarm_ids = fields.Many2many('calendar.alarm', 'calendar_alarm_calendar_event_rel', string='Reminders', ondelete="restrict", copy=False)

    def _compute_is_attendee(self):
        for meeting in self:
            meeting.is_attendee = bool(meeting._find_my_attendee())

    def _compute_attendee_status(self):
        for meeting in self:
            attendee = meeting._find_my_attendee()
            meeting.attendee_status = attendee.state if attendee else 'needsAction'

    def _compute_display_time(self):
        for meeting in self:
            meeting.display_time = self._get_display_time(meeting.start, meeting.stop, meeting.duration, meeting.allday)

    @api.depends('start_date', 'allday', 'start_datetime')
    def _compute_start(self):
        for meeting in self:
            meeting.start = meeting.start_date if meeting.allday else meeting.start_datetime
            meeting.display_start = meeting.start_date if meeting.allday else meeting.start_datetime

    @api.depends('stop_date', 'allday', 'stop_datetime')
    def _compute_stop(self):
        for meeting in self:
            meeting.stop = meeting.stop_date if meeting.allday else meeting.stop_datetime

    @api.constrains('start_datetime', 'stop_datetime', 'start_date', 'stop_date')
    def _check_closing_date(self):
        for event in self:
            if event.stop < event.start:
                raise ValidationError(_('Error ! End date cannot be set before start date.'))

    @api.onchange('allday')
    def onchange_allday(self):
        if not ((self.start_date and self.stop_date) or (self.start and self.stop)):  # At first intialize, we have not datetime
            return

        if self.allday:  # from datetime to date
            start_datetime = self.start_datetime or self.start

            if start_datetime:
                self.start_date = start_datetime
            stop_datetime = self.stop_datetime or self.stop
            if stop_datetime:
                self.stop_date = stop_datetime
        else:  # from date to datetime
            tz = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.utc

            if self.start_date:
                start = fields.Datetime.from_string(self.start_date)
                startdate = tz.localize(start).replace(hour=8).astimezone(pytz.utc)  # Add "+hh:mm" timezone, Set 8 AM in localtime, Convert to UTC
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
    def onchange_duration(self):
        if not (self.start_datetime and self.duration):
            return
        start = fields.Datetime.from_string(self.start_datetime) + timedelta(hours=self.duration)
        self.stop_date = self.stop = self.stop_datetime = fields.Datetime.to_string(start)
        self.start_date = self.start = self.start_datetime

    @api.onchange('start_date')
    def onchange_start_date(self):
        return self.onchange_dates('start', True)

    @api.onchange('stop_date')
    def onchange_stop_date(self):
        return self.onchange_dates('stop', True)

    def onchange_dates(self, fromtype, allday=False):

        """Returns duration and end date based on values passed
        """

        if self.allday != allday:
            return

        if allday:
            if fromtype == 'start' and self.start_date:
                self.start_datetime = self.start = self.start_date

            if fromtype == 'stop' and self.stop_date:
                self.stop_datetime = self.stop = self.stop_date

    def new_invitation_token(self):
        return uuid.uuid4().hex

    def create_attendees(self):
        res = {}
        CalendarAttendee = new_attendees = self.env['calendar.attendee']
        res_partner = self.env['res.partner']
        attendee_to_remove = self.env["calendar.attendee"]
        for event in self:
            attendees = event.attendee_ids.mapped("partner_id")
            for partner in event.partner_ids:
                if partner in attendees:
                    continue
                values = {
                    'partner_id': partner.id,
                    'event_id': event.id,
                    'access_token': self.new_invitation_token(),
                    'email': partner.email,
                }

                if partner == self.env.user.partner_id:
                    values['state'] = 'accepted'

                attendee = CalendarAttendee.create(values)
                new_attendees += attendee
                res_partner += partner

                if not self.env.user.email or self.env.user.email != partner.email:
                    mail_from = self.env.user.email or tools.config.get('email_from', False)
                    if not self.env.context.get('no_email'):
                        attendee._send_mail_to_attendees(email_from=mail_from)

            if new_attendees:
                event.write({'attendee_ids': [(4, att) for att in new_attendees.ids]})
            if res_partner:
                event.message_subscribe(res_partner.ids)

            # We remove old attendees who are not in partner_ids now.
            all_attendee_ids = event.attendee_ids
            partners_to_remove = (all_attendee_ids.mapped('partner_id') | res_partner) - event.partner_ids
            if partners_to_remove:
                attendee_to_remove = attendee_to_remove.search([('partner_id', 'in', partners_to_remove.ids), ('event_id', '=', event.id)])
                if attendee_to_remove:
                    attendee_to_remove.unlink()
            res[event.id] = {
                'new_attendees': new_attendees,
                'old_attendees': all_attendee_ids,
                'removed_attendees': attendee_to_remove
            }
        return res

    def get_search_fields(self, order_fields, r_date=None):
        sort_fields = {}
        for ord_field in order_fields:
            if ord_field == 'id' and r_date:
                sort_fields[ord_field] = '%s-%s' % (self[ord_field], r_date.strftime("%Y%m%d%H%M%S"))
            else:
                sort_fields[ord_field] = self[ord_field]
                if isinstance(self[ord_field], odoo.models.BaseModel):
                    name_get = self[ord_field].name_get()
                    if len(name_get) and len(name_get[0]) >= 2:
                        sort_fields[ord_field] = name_get[0][1]
        if r_date:
            sort_fields['sort_start'] = r_date.strftime("%Y%m%d%H%M%S")
        else:
            sort_fields['sort_start'] = self.display_start and self.display_start.replace(' ', '').replace('-', '')
        return sort_fields

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
            ids = [r['id'] for r in sorted(result_data, cmp=comparer)]
            return self.browse(ids)

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
    def onchange_partner_ids(self):
        """ The basic purpose of this method is to check that destination partners
            effectively have email addresses. Otherwise a warning is thrown.
        """
        field_values = self._fields['partner_ids'].convert_to_onchange(self.partner_ids)
        if not field_values or not field_values[0] or not field_values[0][0] == 6:
            return

        return self.check_partners_email()

    def check_partners_email(self):
        """ Verify that selected partner_ids have an email_address defined.
            Otherwise throw a warning. """
        partner_wo_email_lst = []
        for partner in self.partner_ids:
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
    @api.model
    def _needaction_domain_get(self):
        return [
            ('stop', '<=', fields.Date.today() + ' 23:59:59'),
            ('start', '>=', fields.Date.today()),
            ('user_id', '=', self.env.uid),
        ]

    @api.multi
    def message_post(self, **kwargs):
        ctx = self.env.context
        if self.env.context.get('default_date'):
            del ctx['default_date']
        mail_message = super(CalendarEvent, self.with_context(ctx).browse(get_real_ids(self.id))).message_post(**kwargs)
        return mail_message.id

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
        for event in self:
            current_user = self.env.user
            if current_user.email:
                self.env['calendar.attendee'].browse([att.id for att in event.attendee_ids])._send_mail_to_attendees(email_from=current_user.email)
        return

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
            res = babel.dates.format_date(date=date, format='MMMM y', locale=self.env.context.get('lang', 'en_US'))

        elif interval == 'dayname':
            # Localized day name
            res = babel.dates.format_date(date=date, format='EEEE', locale=self.env.context.get('lang', 'en_US'))

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
        res = res.get_recurrent_ids(args, order=order)
        if count:
            return len(res)
        elif limit:
            return res[offset: offset + limit]
        return res

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        self._set_date(default)
        return super(CalendarEvent, self.browse(calendar_id2real_id(self.id))).copy(default)

    def _detach_one_event(self, values=dict()):
        real_event_id = calendar_id2real_id(self.id)
        data = {'allday': self.allday,
                'start': self.start,
                'stop': self.stop,
                'rrule': self.rrule,
                'duration': self.duration}
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
                final_date=fields.Datetime.from_string(data.get('start')) + timedelta(hours=values.get('duration', False) or data.get('duration'))
            )

            #do not copy the id
            if data.get('id'):
                del(data['id'])
            return self.browse(real_event_id).copy(default=data)

    @api.multi
    def open_after_detach_event(self):
        self.ensure_one()
        new_event = self._detach_one_event()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.event',
            'view_mode': 'form',
            'res_id': new_event.id,
            'target': 'current',
            'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}}
        }

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100):
        for arg in args:
            if arg[0] == 'id':
                for n, calendar_id in enumerate(arg[2]):
                    if isinstance(calendar_id, basestring):
                        arg[2][n] = calendar_id.split('-')[0]
        return super(CalendarEvent, self)._name_search(name=name, args=args, operator=operator, limit=limit)

    @api.multi
    def write(self, values):
        values0 = values
        # process events one by one
        for event in self:
            # make a copy, since _set_date() modifies values depending on event
            values = dict(values0)
            self._set_date(values)
            # special write of complex IDS
            real_ids = []
            new_events = self.browse()
            if '-' not in str(event.id):
                real_ids = event.id
            else:
                real_event_id = calendar_id2real_id(event.id)

                # if we are setting the recurrency flag to False or if we are only changing fields that
                # should be only updated on the real ID and not on the virtual (like message_follower_ids):
                # then set real ids to be updated.
                blacklisted = any(key in values for key in ('start', 'stop', 'active'))
                if not values.get('recurrency', True) or not blacklisted:
                    real_ids = [real_event_id]
                else:
                    if event.rrule:
                        new_events = event._detach_one_event(values)
            real_cal_events = self.browse(real_ids)
            super(CalendarEvent, real_cal_events).write(values)

            # set end_date for calendar searching
            if values.get('recurrency') and values.get('end_type', 'count') in ('count', unicode('count')) and \
                    (values.get('rrule_type') or values.get('count') or values.get('start') or values.get('stop')):
                for real_cal_event in real_cal_events:
                    final_date = real_cal_event._get_recurrency_end_date()
                    super(CalendarEvent, real_cal_event).write({'final_date': final_date})

            attendees_create = False
            records = real_cal_events | new_events
            if values.get('partner_ids'):
                attendees_create = records.create_attendees()

            if (values.get('start_date') or values.get('start_datetime')) and values.get('active', True):
                for the_event in records:
                    if attendees_create:
                        attendees_create = attendees_create[the_event.id]
                        mail_to_attendees = attendees_create['old_attendee_ids'] - attendees_create['removed_attendee_ids']
                    else:
                        mail_to_attendees = the_event.attendee_ids

                    if mail_to_attendees:
                        mail_to_attendees._send_mail_to_attendees(template_xmlid='calendar_template_meeting_changedate', email_from=self.env.user.email)

        return True

    @api.model
    def create(self, vals):
        self._set_date(vals)
        res = super(CalendarEvent, self).create(vals)
        final_date = res._get_recurrency_end_date()
        res.write({'final_date': final_date})
        res.create_attendees()
        return res

    def export_data(self, *args, **kwargs):
        """ Override to convert virtual ids to ids """
        return super(CalendarEvent, self.browse(set(get_real_ids(self.ids)))).export_data(*args, **kwargs)

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
        if self.ids:
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
                user_id = type(r['user_id']) in (tuple, list) and r['user_id'][0] or r['user_id']
                if user_id == self.env.uid:
                    continue
            if r['privacy'] == 'private':
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
        if isinstance(self.ids, (basestring, int, long)):
            return result and result[0] or False

        return result

    @api.multi
    def unlink(self, can_be_deleted=True):
        res = False
        event_to_exclude = event_to_unlink = self.env['calendar.event']
        for event in self:
            if len(str(event.id).split('-')) == 1:  # if  ID REAL
                if event.recurrent_id:
                    event_to_exclude += event
                else:
                    event_to_unlink += event
            else:
                event_to_exclude += event

        if event_to_unlink:
            res = super(CalendarEvent, event_to_unlink).unlink()

        if event_to_exclude:
            res = event_to_exclude.write({'active': False})
        return res
