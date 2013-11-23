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

import hashlib
import pytz
import re
import time
import openerp
import openerp.service.report

from datetime import datetime, timedelta, date
from dateutil import parser
from dateutil import rrule
from dateutil.relativedelta import relativedelta

from openerp import tools, SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _


    
def get_recurrent_dates(rrulestring, startdate, exdate=None, tz=None, context=None):
    """Get recurrent dates based on Rule string considering exdate and start date.
    
    All input dates and output dates are in UTC. Dates are infered
    thanks to rules in the ``tz`` timezone if given, else it'll be in
    the current local timezone as specified in the context.

    @param rrulestring: rulestring (ie: 'FREQ=DAILY;INTERVAL=1;COUNT=3')
    @param exdate: string of dates separated by commas (ie: '20130506220000Z,20130507220000Z')
    @param startdate: string start date for computing recurrent dates
    @param tz: pytz timezone for computing recurrent dates    
    @return: list of Recurrent dates

    """

    exdate = exdate.split(',') if exdate else []
    startdate = pytz.UTC.localize(datetime.strptime(startdate, "%Y-%m-%d %H:%M:%S"))

    def todate(date):
        val = parser.parse(''.join((re.compile('\d')).findall(date)))
        ## Dates are localized to saved timezone if any, else current timezone.
        if not val.tzinfo:
            val = pytz.UTC.localize(val)
        return val.astimezone(timezone)

    timezone = pytz.timezone(tz or context.get('tz') or 'UTC')

    if not startdate:
        startdate = datetime.now()

    ## Convert the start date to saved timezone (or context tz) as it'll
    ## define the correct hour/day asked by the user to repeat for recurrence.
    startdate = startdate.astimezone(timezone)
    rset1 = rrule.rrulestr(str(rrulestring), dtstart=startdate, forceset=True)
    for date in exdate:
        datetime_obj = todate(date)
        rset1._exdate.append(datetime_obj)
            
    return [d.astimezone(pytz.UTC) for d in rset1]

def base_calendar_id2real_id(base_calendar_id=None, with_date=False):
    """
    Convert a "virtual/recurring event id" (type string) into a real event id (type int).
    E.g. virtual/recurring event id is 4-20091201100000, so it will return 4.
    @param base_calendar_id: id of calendar
    @param with_date: if a value is passed to this param it will return dates based on value of withdate + base_calendar_id
    @return: real event id
    """
    if base_calendar_id and isinstance(base_calendar_id, (str, unicode)):
        res = base_calendar_id.split('-')
        if len(res) >= 2:
            real_id = res[0]
            if with_date:
                real_date = time.strftime("%Y-%m-%d %H:%M:%S", time.strptime(res[1], "%Y%m%d%H%M%S"))
                start = datetime.strptime(real_date, "%Y-%m-%d %H:%M:%S")
                end = start + timedelta(hours=with_date) 
                return (int(real_id), real_date, end.strftime("%Y-%m-%d %H:%M:%S"))
            return int(real_id)

    return base_calendar_id and int(base_calendar_id) or base_calendar_id

def get_real_ids(ids):
    if isinstance(ids, (str, int, long)):
        return base_calendar_id2real_id(ids)

    if isinstance(ids, (list, tuple)):
        res = []
        for id in ids:
            res.append(base_calendar_id2real_id(id))
        return res

class calendar_attendee(osv.osv):
    """
    Calendar Attendee Information
    """
    _name = 'calendar.attendee'
    _description = 'Attendee information'

    def _get_address(self, name=None, email=None):
        """
        Gives email information in ical CAL-ADDRESS type format.
        @param name: name for CAL-ADDRESS value
        @param email: email address for CAL-ADDRESS value
        """
        if name and email:
            name += ':'
        return (name or '') + (email and ('MAILTO:' + email) or '')

    def _compute_data(self, cr, uid, ids, name, arg, context=None):
        """
        Compute data on function fields for attendee values.
        @param ids: list of calendar attendee's IDs
        @param name: name of field
        @return: dictionary of form {id: {'field Name': value'}}
        """
        name = name[0]
        result = {}
        for attdata in self.browse(cr, uid, ids, context=context):
            id = attdata.id
            result[id] = {}
            
            if name == 'cn':
                if attdata.partner_id:
                    result[id][name] = attdata.partner_id.name or False
                else:
                    result[id][name] = attdata.email or ''
            
            if name == 'event_date':
                if attdata.ref:
                    result[id][name] = attdata.ref.date
                else:
                    result[id][name] = False
 
            if name == 'event_end_date':
                if attdata.ref:
                    result[id][name] = attdata.ref.date_deadline
                else:
                    result[id][name] = False

        return result

    _columns = {
        'state': fields.selection([('needs-action', 'Needs Action'),('tentative', 'Uncertain'),('declined', 'Declined'),('accepted', 'Accepted')], 'Status', readonly=True, help="Status of the attendee's participation"),
        'cn': fields.function(_compute_data, string='Common name', type="char", size=124, multi='cn', store=True),
        'dir': fields.char('URI Reference', size=124, help="Reference to the URI that points to the directory information corresponding to the attendee."),
        'partner_id': fields.many2one('res.partner', 'Contact',readonly="True"),
        'email': fields.char('Email', size=124, help="Email of Invited Person"),
        'event_date': fields.function(_compute_data, string='Event Date', type="datetime", multi='event_date'),
        'event_end_date': fields.function(_compute_data, string='Event End Date', type="datetime", multi='event_end_date'),
        'availability': fields.selection([('free', 'Free'), ('busy', 'Busy')], 'Free/Busy', readonly="True"),
        'access_token':fields.char('Invitation Token', size=256),        
        'ref': fields.many2one('crm.meeting','Meeting linked'),        
    }
    _defaults = {
        'state': 'needs-action',        
    }

    def copy(self, cr, uid, id, default=None, context=None):
        raise osv.except_osv(_('Warning!'), _('You cannot duplicate a calendar attendee.'))
    
    def onchange_partner_id(self, cr, uid, ids, partner_id,context=None):
        """
        Make entry on email and availability on change of partner_id field.
        @param partner_id: changed value of partner id
        """        
        if not partner_id:
            return {'value': {'email': ''}}
        partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
        return {'value': {'email': partner.email}}
    
    def get_ics_file(self, cr, uid, event_obj, context=None):
        """
        Returns iCalendar file for the event invitation.
        @param event_obj: event object (browse record)
        @return: .ics file content
        """
        res = None
        def ics_datetime(idate, short=False):
            if idate:
                #returns the datetime as UTC, because it is stored as it in the database
                return datetime.strptime(idate, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.timezone('UTC'))
            return False
        
        try:
            # FIXME: why isn't this in CalDAV?
            import vobject
        except ImportError:
            return res
        
        cal = vobject.iCalendar()
        event = cal.add('vevent')
        if not event_obj.date_deadline or not event_obj.date:
            raise osv.except_osv(_('Warning!'),_("First you have to specify the date of the invitation."))
        event.add('created').value = ics_datetime(time.strftime('%Y-%m-%d %H:%M:%S'))
        event.add('dtstart').value = ics_datetime(event_obj.date)
        event.add('dtend').value = ics_datetime(event_obj.date_deadline)
        event.add('summary').value = event_obj.name
        if  event_obj.description:
            event.add('description').value = event_obj.description
        if event_obj.location:
            event.add('location').value = event_obj.location
        if event_obj.rrule:
            event.add('rrule').value = event_obj.rrule

        if event_obj.alarm_ids:
              for alarm in event_obj.alarm_ids:
                # computes alarm data
                valarm = event.add('valarm')
                # Compute trigger data
                interval = alarm.interval
                occurs = 'before'
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
                # Compute other details
                valarm.add('DESCRIPTION').value = alarm.name or 'OpenERP'
        for attendee in event_obj.attendee_ids:
            attendee_add = event.add('attendee')
            attendee_add.value = 'MAILTO:' + (attendee.email or '')
        res = cal.serialize()
        return res

    def _send_mail(self, cr, uid, ids, mail_to, email_from=tools.config.get('email_from', False), context=None):
        """
        Send mail for event invitation to event attendees.
        @param email_from: email address for user sending the mail
        """
        res = False
        
        mail_id = []
        data_pool = self.pool.get('ir.model.data')
        mail_pool = self.pool.get('mail.mail')
        template_pool = self.pool.get('email.template')
        local_context = context.copy()
        color = {
                 'needs-action' : 'grey',
                 'accepted' :'green',
                 'tentative' :'#FFFF00',
                 'declined':'red'                 
        }
        
        for attendee in self.browse(cr, uid, ids, context=context):            
            res_obj = attendee.ref
            if res_obj:
                dummy,template_id = data_pool.get_object_reference(cr, uid, 'base_calendar', "crm_email_template_meeting_invitation")
                dummy,act_id = data_pool.get_object_reference(cr, uid, 'base_calendar', "view_crm_meeting_calendar")                
                body = template_pool.browse(cr, uid, template_id, context=context).body_html
                if attendee.email and email_from:
                    ics_file = self.get_ics_file(cr, uid, res_obj, context=context)
                    local_context['att_obj'] = attendee
                    local_context['color'] = color
                    local_context['action_id'] = self.pool.get('ir.actions.act_window').search(cr, uid, [('view_id','=',act_id)], context=context)[0]
                    local_context['dbname'] = cr.dbname
                    local_context['base_url'] = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url', default='http://localhost:8069', context=context)
                    vals = template_pool.generate_email(cr, uid, template_id, res_obj.id, context=local_context)
                    if ics_file:
                        vals['attachment_ids'] = [(0,0,{'name': 'invitation.ics',
                                                    'datas_fname': 'invitation.ics',
                                                    'datas': str(ics_file).encode('base64')})]
                    vals['model'] = None #We don't want to have the mail in the tchatter while in queue!
                    vals['auto_delete'] = True #We don't need mail after it has been sended !
                    
                    if not attendee.partner_id.opt_out:
                        mail_id.append(mail_pool.create(cr, uid, vals, context=context))
                    
        
        if mail_id:
            try:
                res =  mail_pool.send(cr, uid, mail_id, context=context)
            except Exception as e:
                print e
                
        return res
    
    
    def do_attendee_decline(self, cr, uid, ids, context=None):
         return self.do_decline(cr, uid, ids, context=context)
     
    def do_attendee_accept(self, cr, uid, ids, context=None):
        return self.do_accept(cr, uid, ids, context=context)
    
    def do_attendee_maybe(self, cr, uid, ids, context=None):
        return self.do_tentative(cr, uid, ids, context=context)

    def onchange_user_id(self, cr, uid, ids, user_id, *args, **argv):
        """
        Make entry on email and availbility on change of user_id field.
        @param ids: list of attendee's IDs
        @param user_id: changed value of User id
        @return: dictionary of values which put value in email and availability fields
        """
        if not user_id:
            return {'value': {'email': ''}}
        
        usr_obj = self.pool.get('res.users').browse(cr, uid, user_id, *args)
        return {'value': {'email': user.email, 'availability':user.availability}}

    def do_tentative(self, cr, uid, ids, context=None, *args):
        """
        Makes event invitation as Tentative.
        @param ids: list of attendee's IDs
        """
        return self.write(cr, uid, ids, {'state': 'tentative'}, context)

    def do_accept(self, cr, uid, ids, context=None, *args):
        """
        Marks event invitation as Accepted.
        @param ids: list of attendee's IDs
        """
        if context is None:
            context = {}
        meeting_obj =  self.pool.get('crm.meeting')
        res = self.write(cr, uid, ids, {'state': 'accepted'}, context)
        for attendee in self.browse(cr, uid, ids, context=context):
            meeting_ids = meeting_obj.search(cr, uid, [('attendee_ids', '=', attendee.id)], context=context)
            if meeting_ids:
                meeting_obj.message_post(cr, uid, get_real_ids(meeting_ids), body=_(("%s has accepted invitation") % (attendee.cn)), context=context)
        return res
    
    def do_decline(self, cr, uid, ids, context=None, *args):
        """
        Marks event invitation as Declined.
        @param ids: list of calendar attendee's IDs
        """
        if context is None:
            context = {}
        meeting_obj = self.pool.get('crm.meeting')
        res = self.write(cr, uid, ids, {'state': 'declined'}, context)
        for attandee in self.browse(cr, uid, ids, context=context):
            meeting_ids = meeting_obj.search(cr, uid, [('attendee_ids', '=', attandee.id)], context=context)
            if meeting_ids:
                meeting_obj.message_post(cr, uid, get_real_ids(meeting_ids), body=_(("%s has declined invitation") % (attandee.cn)), context=context)
        return res

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if not vals.get("email") and vals.get("cn"):
            cnval = vals.get("cn").split(':')
            email = filter(lambda x:x.__contains__('@'), cnval)
            vals['email'] = email and email[0] or ''
            vals['cn'] = vals.get("cn")
        res = super(calendar_attendee, self).create(cr, uid, vals, context=context)
        return res


class res_partner(osv.osv): 
    _inherit = 'res.partner'
    
    _columns = {
        'cal_last_notif': fields.datetime('Last Notification from base Calendar'),        
     }
        
    def get_attendee_detail(self, cr, uid, ids, meeting_id, context=None):
        datas = []
        meeting = False
        if meeting_id:
            meeting = self.pool.get('crm.meeting').browse(cr, uid, get_real_ids(meeting_id),context)
        for partner in self.browse(cr, uid, ids, context=context):
            data = self.name_get(cr, uid, [partner.id], context)[0]
            if meeting:
                for attendee in meeting.attendee_ids:
                    if attendee.partner_id.id == partner.id:
                        data = (data[0], data[1], attendee.state)
            datas.append(data)
        return datas

    def update_cal_last_event(self,cr,uid,context=None):
        partner = self.pool.get('res.users').browse(cr,uid,uid,context=context).partner_id;
        self.write(cr,uid,partner.id,{'cal_last_notif' : datetime.now() } ,context=context)
        return "OK"
# 
#     def do_run_scheduler(self, cr, uid, automatic=False, use_new_cursor=False, \
#                        context=None):
#         """Scheduler for event reminder
#         @param ids: List of calendar alarm's IDs.
#         @param use_new_cursor: False or the dbname
#         """
#         if context is None:
#             context = {}
#         current_datetime = datetime.now()
#         alarm_ids = self.search(cr, uid, [('state', '!=', 'done')], context=context)
# 
#         mail_to = ""
# 
#         for alarm in self.browse(cr, uid, alarm_ids, context=context):
#             next_trigger_date = None
#             update_vals = {}
#             model_obj = self.pool[alarm.model_id.model]
#             res_obj = model_obj.browse(cr, uid, alarm.res_id, context=context)
#             re_dates = []
# 
#             if hasattr(res_obj, 'rrule') and res_obj.rrule:
#                 recurrent_dates = get_recurrent_dates(res_obj.rrule, res_obj.date, res_obj.exdate, res_obj.vtimezone, res_obj.exrule, context=context)
# 
#                 trigger_interval = alarm.interval
#                 if trigger_interval == 'days':
#                     delta = timedelta(days=alarm.duration)
#                 if trigger_interval == 'hours':
#                     delta = timedelta(hours=alarm.duration)
#                 if trigger_interval == 'minutes':
#                     delta = timedelta(minutes=alarm.duration)
#                 
#                 for rdate in recurrent_dates:
#                     if rdate + delta > current_datetime:
#                         break
#                     if rdate + delta <= current_datetime:
#                         re_dates.append(rdate.strftime("%Y-%m-%d %H:%M:%S"))
#                 rest_dates = recurrent_dates[len(re_dates):]
#                 next_trigger_date = rest_dates and rest_dates[0] or None
# 
#             else:
#                 re_dates = [alarm.date]
# 
#             if re_dates:
#                 if alarm.action == 'email':
#                     sub = '[OpenERP Reminder] %s' % (alarm.name)
#                     body = """<pre>Event: %s    
#                                     Event Date: %s
#                                     Description: %s
#                                     From: %s                                
#                                     ----
#                                     %s
#                               </pre>"""  % (alarm.name, alarm.trigger_date, alarm.description, alarm.user_id.name, alarm.user_id.signature)
#                     mail_to = alarm.user_id.email
#                     for att in alarm.attendee_ids:
#                         mail_to = mail_to + " " + att.user_id.email
#                     if mail_to:
#                         vals = {
#                             'state': 'outgoing',
#                             'subject': sub,
#                             'body_html': body,
#                             'email_to': mail_to,
#                             'email_from': tools.config.get('email_from', mail_to),
#                         }
#                         self.pool.get('mail.mail').create(cr, uid, vals, context=context)
#             if next_trigger_date:
#                 update_vals.update({'trigger_date': next_trigger_date})
#             else:
#                 update_vals.update({'state': 'done'})
#             self.write(cr, uid, [alarm.id], update_vals)
#         return True

class calendar_alarm_manager(osv.osv):
    _name = 'calendar.alarm_manager'
    
    def get_next_potential_limit_alarm(self,cr,uid,seconds, notif=True, mail=True, partner_id=None, context=None):
        res = {}
        print "Search for partner:  ", partner_id
        base_request = """
                    SELECT 
                        crm.id,
                        crm.date - interval '1' minute  * calcul_delta.max_delta AS first_alarm, 
                        CASE 
                            WHEN crm.recurrency THEN crm.end_date - interval '1' minute  * calcul_delta.min_delta
                            ELSE crm.date_deadline - interval '1' minute  * calcul_delta.min_delta
                        END as last_alarm, 
                        crm.date as first_event_date,     
                        CASE 
                            WHEN crm.recurrency THEN crm.end_date
                            ELSE crm.date_deadline
                        END as last_event_date,
                        calcul_delta.min_delta,
                        calcul_delta.max_delta,
                        crm.rrule
                    FROM 
                        crm_meeting AS crm
                        RIGHT JOIN
                            (
                                SELECT 
                                    rel.crm_meeting_id, max(alarm.duration_minutes) AS max_delta,min(alarm.duration_minutes) AS min_delta
                                FROM
                                    calendar_alarm_crm_meeting_rel AS rel 
                                        LEFT JOIN calendar_alarm AS alarm ON alarm.id = rel.calendar_alarm_id
                                WHERE alarm.type in %s            
                                GROUP BY rel.crm_meeting_id
                            ) AS calcul_delta ON calcul_delta.crm_meeting_id = crm.id
             """
             
        filter_user = """
                LEFT JOIN crm_meeting_res_partner_rel AS part_rel ON part_rel.crm_meeting_id = crm.id
                    AND part_rel.res_partner_id = %s
        """
        
        
        #Add filter on type
        type_to_read = () #('dummy',)
        if notif:
            type_to_read += ('notification',)
        if mail:
            type_to_read += ('email',)
            
        tuple_params = (type_to_read,)
                
        
        #ADD FILTER ON PARTNER_ID
        if partner_id:
            base_request += filter_user
            tuple_params += (partner_id, )

        #Add filter on hours
        tuple_params += (seconds,seconds,)
        
        print(tuple_params)
        cr.execute("""
            SELECT 
                * 
            FROM (
                    """ 
                + base_request
                + """
            ) AS ALL_EVENTS
            WHERE 
                ALL_EVENTS.first_alarm < (now() at time zone 'utc' + interval '%s' second )
                AND ALL_EVENTS.last_alarm > (now() at time zone 'utc' - interval '%s' second )
           """,tuple_params)
                 
        for event_id, first_alarm,last_alarm,first_meeting,last_meeting,min_duration,max_duration,rrule in cr.fetchall():
            res[event_id] = {}
            res[event_id]['event_id'] = event_id
            res[event_id]['first_alarm'] = first_alarm
            res[event_id]['last_alarm'] = last_alarm
            res[event_id]['first_meeting'] = first_meeting
            res[event_id]['last_meeting'] = last_meeting
            res[event_id]['min_duration'] = min_duration
            res[event_id]['max_duration'] = max_duration
            res[event_id]['rrule'] = rrule
        
        print "All event from SQL : ",res
        return res
    
    def do_check_alarm_for_one_date(self,cr,uid,one_date,event, event_maxdelta,in_the_next_X_seconds,after=False,notif=True, mail=True,context=None):
        res = []
        alarm_type = []
        
        if notif:
            alarm_type.append('notification')
        if mail:
            alarm_type.append('email')
        
        if one_date - timedelta(minutes=event_maxdelta) < datetime.now() + timedelta(seconds=in_the_next_X_seconds): #if an alarm is possible for this date
            print "ALARMIDS = ",  event.alarm_ids
            for alarm in event.alarm_ids:
                print "type = ",alarm.type
                print "after = ",after
                print "cond 0 =", alarm.type in alarm_type
                print "cond 1 = ", one_date - timedelta(minutes=alarm.duration_minutes), " < ", datetime.now()  + timedelta(seconds=in_the_next_X_seconds)
                #print "cond 2", one_date - timedelta(minutes=alarm.duration_minutes), " > ",datetime.strptime(after.split('.')[0], "%Y-%m-%d %H:%M:%S")
                
                print
                if alarm.type in alarm_type and \
                    one_date - timedelta(minutes=alarm.duration_minutes) < datetime.now()  + timedelta(seconds=in_the_next_X_seconds) and \
                    (not after or one_date - timedelta(minutes=alarm.duration_minutes) > datetime.strptime(after.split('.')[0], "%Y-%m-%d %H:%M:%S")):
                        alert =  {
                               'alarm_id' : alarm.id,
                               'event_id' : event.id,
                               'notify_at' : one_date - timedelta(minutes=alarm.duration_minutes),                               
                               }
                        print "ALERT ADDED : ", alert
                        res.append(alert) 
        else:
            print "Not in condition..."
            
        print "DATE SERVER:", datetime.now();
        return res

    def do_run_scheduler_mail(self,cr,uid,context=None):
        cron = self.pool.get('ir.cron').search(cr,uid,[('model','ilike',self._name)],context=context)
        if cron and len(cron) == 1:
            cron = self.pool.get('ir.cron').browse(cr,uid,cron[0],context=context)
        else:
            raise ("Cron for " + self._name + " not identified :( !")
        
        if cron.interval_type=="weeks":
            cron_interval = cron.interval_number * 7 * 24 * 60 * 60
        elif cron.interval_type=="days":
            cron_interval = cron.interval_number * 24 * 60 * 60 
        elif cron.interval_type=="hours":
            cron_interval = cron.interval_number * 60 * 60
        elif cron.interval_type=="minutes":
            cron_interval = cron.interval_number * 60
        elif cron.interval_type=="seconds":
            cron_interval = cron.interval_number 
        
        if not cron_interval:
            raise ("Cron delay for " + self._name + " not calculated :( !")
        
        print "Cron interval = ",cron_interval
        
        all_events = self.get_next_potential_limit_alarm(cr,uid,cron_interval,notif=False,context=context)
        for event in all_events: #.values()
            max_delta = all_events[event]['max_duration'];
            curEvent = self.pool.get('crm.meeting').browse(cr,uid,event,context=context) 
            if curEvent.recurrency:
                bFound = False
                LastFound = False                    
                for one_date in get_recurrent_dates(curEvent.rrule, curEvent.date, curEvent.exdate, curEvent.vtimezone, context=context) :
                    in_date_format = datetime.strptime(one_date, '%Y-%m-%d %H:%M:%S');
                    LastFound = self.do_check_alarm_for_one_date(cr,uid,in_date_format,curEvent,max_delta,cron_interval,notif=False,context=context)
                    if LastFound:
                        for alert in LastFound:
                            self.do_mail_reminder(cr,uid,alert,context=context)
                            
                        if not bFound: #if it's the first alarm for this recurrent event
                            bFound = True   
                    if bFound and not LastFound: #if the precendent event had alarm but not this one, we can stop the search fot this event
                        break                                              
            else:
                in_date_format = datetime.strptime(curEvent.date, '%Y-%m-%d %H:%M:%S');
                LastFound = self.do_check_alarm_for_one_date(cr,uid,in_date_format,curEvent,max_delta,cron_interval,notif=False,context=context)
                if LastFound:
                    for alert in LastFound:
                        self.do_mail_reminder(cr,uid,alert,context=context)                    
                
            #Purge all done
    
    def get_next_event(self,cr,uid,context=None):
        ajax_check_every_seconds = 300
        
        partner = self.pool.get('res.users').browse(cr,uid,uid,context=context).partner_id;
        print "Last alert for partner : ",partner.cal_last_notif
        
        all_notif = []
        
        all_events = self.get_next_potential_limit_alarm(cr,uid,ajax_check_every_seconds,partner_id=partner.id,mail=False,context=context)
        print all_events
        
        for event in all_events: #.values()
            max_delta = all_events[event]['max_duration'];
            curEvent = self.pool.get('crm.meeting').browse(cr,uid,event,context=context) 
            if curEvent.recurrency:
                bFound = False
                LastFound = False                    
                for one_date in get_recurrent_dates(curEvent.rrule, curEvent.date, curEvent.exdate, curEvent.vtimezone, context=context) :
                    in_date_format = datetime.strptime(one_date, '%Y-%m-%d %H:%M:%S');
                    LastFound = self.do_check_alarm_for_one_date(cr,uid,in_date_format,curEvent,max_delta,ajax_check_every_seconds,after=partner.cal_last_notif,mail=False,context=context)
                    if LastFound:
                        for alert in LastFound:
                            all_notif.append(self.do_notif_reminder(cr,uid,alert,context=context))                            
                        if not bFound: #if it's the first alarm for this recurrent event
                            bFound = True   
                    if bFound and not LastFound: #if the precendent event had alarm but not this one, we can stop the search fot this event
                        break                                              
            else:
                in_date_format = datetime.strptime(curEvent.date, '%Y-%m-%d %H:%M:%S');
                LastFound = self.do_check_alarm_for_one_date(cr,uid,in_date_format,curEvent,max_delta,ajax_check_every_seconds,partner.cal_last_notif,mail=False,context=context)
                print "Lastfound = ",LastFound
                if LastFound:
                    for alert in LastFound:
                        all_notif.append(self.do_notif_reminder(cr,uid,alert,context=context))
                    
        return  all_notif
            
    def do_mail_reminder(self,cr,uid,alert,context=None):
        if context is None:
            context = {}
        event = self.pool.get("crm.meeting").browse(cr,uid,alert['event_id'],context=context)
        alarm = self.pool.get("calendar.alarm").browse(cr,uid,alert['alarm_id'],context=context)
        
        if alarm.type == 'email':
            mail_id = []
            mail_pool = self.pool.get('mail.mail')
            data_pool = self.pool.get('ir.model.data')
            template_pool = self.pool.get('email.template')                       
            local_context = {}
            
            for attendee in event.attendee_ids:            
                dummy,template_id = data_pool.get_object_reference(cr, uid, 'base_calendar', "crm_email_template_meeting_reminder")
                dummy,act_id = data_pool.get_object_reference(cr, uid, 'base_calendar', "view_crm_meeting_calendar")                
                body = template_pool.browse(cr, uid, template_id, context=context).body_html
                if attendee.email: # and tools.config.get('email_from', False):
                    local_context['att_obj'] = attendee
                    local_context['action_id'] = self.pool.get('ir.actions.act_window').search(cr, uid, [('view_id','=',act_id)], context=context)[0]
                    local_context['dbname'] = cr.dbname
                    local_context['base_url'] = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url', default='http://localhost:8069', context=context)
                    vals = template_pool.generate_email(cr, uid, template_id, event.id, context=local_context)
                    vals['model'] = None #We don't want to have the mail in the tchatter while in queue!
                    vals['auto_delete'] = True #We don't need mail after it has been sended !
                     
                    if not attendee.partner_id.opt_out:
                        mail_id.append(mail_pool.create(cr, uid, vals, context=context))
             
            if mail_id:
                for mail in mail_pool.browse(cr,uid,mail_id,context=context):
                    print "REMINDER SENDED ... EMAIL : ",mail.id
                    
        else:
            print "SHOULD BE AN MAIL ALARM :(   FOR EVENT %s / ALARM %s" % (alert['event_id'],alert['alarm_id'])

    def do_notif_reminder(self,cr,uid,alert,context=None):
        alarm = self.pool.get("calendar.alarm").browse(cr,uid,alert['alarm_id'],context=context)
        event = self.pool.get("crm.meeting").browse(cr,uid,alert['event_id'],context=context)
        
        if alarm.type == 'notification':
            mail_id = []
            mail_pool = self.pool.get('mail.mail')
            data_pool = self.pool.get('ir.model.data')
            template_pool = self.pool.get('email.template')                       
            local_context = context.copy()
            message = event.display_time 
            
            delta = alert['notify_at'] - datetime.now()
            delta = delta.seconds + delta.days * 3600 * 24
            
            return {
                     'event_id' : event.id,
                     'title' : event.name,
                     'message' : message,
                     'timer' : delta, #Now - event_date - alaram.duration_minute
                     'notify_at' : alert['notify_at'].strftime("%Y-%m-%d %H:%M:%S"), #Now - event_date - alaram.duration_minute 
                     }
                                        
        else:
            print "SHOULD BE AN NOTIF ALARM :(   FOR EVENT %s / ALARM %s" % (alert['event_id'],alert['alarm_id'])


# 
#     def do_run_stack_scheduler(self,cr,uid,context=None):
#         all_events = self.get_next_potential_limit_alarm(cr,uid,self.EVENT_ALARM_STACK_HOURS,context=context)
#         for event in all_events: #.values()
#             max_delta = all_events[event]['max_duration'];
#             curEvent = self.pool.get('crm.meeting').browse(cr,uid,event,context=context) 
#             if curEvent.recurrency:
#                 bFound = False
#                 bLastFournd = False                    
#                 for one_date in get_recurrent_dates(curEvent.rrule,curEvent.date) :
#                     in_date_format = datetime.strptime(one_date, '%Y-%m-%d %H:%M:%S');
#                     bLastFound = self.do_check_alarm_for_one_date(cr,uid,in_date_format,curEvent,max_delta,context=context)
#                     if bLastFound and not bFound: #if it's the first alarm for this recurrent event
#                         bFound = True   
#                     if bFound and not bLastFound: #if the precendent event had alarm but not this one, we can stop the search fot this event
#                         break                                              
#             else:
#                 in_date_format = datetime.strptime(curEvent.date, '%Y-%m-%d %H:%M:%S');
#                 self.do_check_alarm_for_one_date(cr,uid,in_date_format,curEvent,max_delta,context=context)
#                 
#             #Purge all done
                
        

class calendar_alarm(osv.osv):
    _name = 'calendar.alarm'
    _description = 'Event alarm'

    def _get_duration(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for alarm in self.browse(cr, uid, ids, context=context):
            if alarm.interval == "minutes":
                res[alarm.id] = alarm.duration
            elif alarm.interval == "hours":
                res[alarm.id] = alarm.duration * 60
            elif alarm.interval == "days":
                res[alarm.id] = alarm.duration * 60 * 24
            else:
                res[alarm.id] = 0
        return res

    _columns = {
        'name':fields.char('Name', size=256, required=True), # fields function
        'type': fields.selection([('notification', 'Notification'), ('email', 'Email')], 'Type', required=True),
        'duration': fields.integer('Amount', required=True),
        'interval': fields.selection([('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days')], 'Unit', required=True),
        
        'duration_minutes': fields.function(_get_duration, type='integer', string='duration_minutes',store=True),
     }
    
    _defaults = {
        'type': 'notification',
        'duration': 1,
        'interval': 'hours',
    }
    

class ir_values(osv.osv):
    _inherit = 'ir.values'

    def set(self, cr, uid, key, key2, name, models, value, replace=True, isobject=False, meta=False, preserve_user=False, company=False):
        
        new_model = []
        for data in models:
            if type(data) in (list, tuple):
                new_model.append((data[0], base_calendar_id2real_id(data[1])))
            else:
                new_model.append(data)
        return super(ir_values, self).set(cr, uid, key, key2, name, new_model, \
                    value, replace, isobject, meta, preserve_user, company)

    def get(self, cr, uid, key, key2, models, meta=False, context=None, res_id_req=False, without_user=True, key2_req=True):
        if context is None:
            context = {}
        new_model = []
        for data in models:
            if type(data) in (list, tuple):
                new_model.append((data[0], base_calendar_id2real_id(data[1])))
            else:
                new_model.append(data)
        return super(ir_values, self).get(cr, uid, key, key2, new_model, \
                         meta, context, res_id_req, without_user, key2_req)


class ir_model(osv.osv):

    _inherit = 'ir.model'

    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
                
        new_ids = isinstance(ids, (str, int, long)) and [ids] or ids
        if context is None:
            context = {}
        data = super(ir_model, self).read(cr, uid, new_ids, fields=fields, \
                        context=context, load=load)
        if data:
            for val in data:
                val['id'] = base_calendar_id2real_id(val['id'])
        return isinstance(ids, (str, int, long)) and data[0] or data


original_exp_report = openerp.service.report.exp_report

def exp_report(db, uid, object, ids, data=None, context=None):
    """
    Export Report
    """
    if object == 'printscreen.list':
        original_exp_report(db, uid, object, ids, data, context)
    new_ids = []
    for id in ids:
        new_ids.append(base_calendar_id2real_id(id))
    if data.get('id', False):
        data['id'] = base_calendar_id2real_id(data['id'])
    return original_exp_report(db, uid, object, new_ids, data, context)

openerp.service.report.exp_report = exp_report






class ________OLD_CRM_MEETING():
    _name = 'TEMP'
    






class crm_meeting_type(osv.Model):
    _name = 'crm.meeting.type'
    _description = 'Meeting Type'
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
    }

class crm_meeting(osv.Model):
    """ Model for CRM meetings """
    _name = 'crm.meeting'
    _description = "Meeting"
    _order = "id desc"
    _inherit = ["mail.thread", "ir.needaction_mixin"]
       
    def do_run_scheduler(self,cr,uid,id,context=None):
        self.pool.get('calendar.alarm_manager').do_run_scheduler(cr,uid,context=context)
        
    def _get_recurrency_end_date(self, data, context=None):  
        if data.get('recurrency') and data.get('end_type') in ('count', unicode('count')):
            data_date_deadline = datetime.strptime(data.get('date_deadline'), '%Y-%m-%d %H:%M:%S')
            if data.get('rrule_type') in ('daily', unicode('count')):
                rel_date = relativedelta(days=data.get('count')+1)
            elif data.get('rrule_type') in ('weekly', unicode('weekly')):
                rel_date = relativedelta(days=(data.get('count')+1)*7) 
            elif data.get('rrule_type') in ('monthly', unicode('monthly')):
                rel_date = relativedelta(months=data.get('count')+1)
            elif data.get('rrule_type') in ('yearly', unicode('yearly')):
                rel_date = relativedelta(years=data.get('count')+1)            
            end_date = data_date_deadline + rel_date            
        else:
            end_date = data.get('end_date')            
        return end_date
    
    def _find_my_attendee(self, cr, uid, meeting_ids, context=None):
        """
            Return the first attendee where the user connected has been invited from all the meeting_ids in parameters
        """
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        for meeting_id in meeting_ids:
            for attendee in self.browse(cr,uid,meeting_id,context).attendee_ids:
                if user.partner_id.id == attendee.partner_id.id:
                    return attendee
        return False
    
    def _get_display_time(self, cr, uid, meeting_id, context=None):
        """
            Return date and time (from to from) based on duration with timezone in string :
            eg.
            1) if user add duration for 2 hours, return : August-23-2013 at ( 04-30 To 06-30) (Europe/Brussels)
            2) if event all day ,return : AllDay, July-31-2013
        """
        if context is None:
            context = {}
        
        tz = context.get('tz', False) 
        if not tz: #tz can have a value False, so dont do it in the default value of get !
            tz = pytz.timezone('UTC')
            
        meeting = self.browse(cr, uid, meeting_id, context=context)
        date = fields.datetime.context_timestamp(cr, uid, datetime.strptime(meeting.date, tools.DEFAULT_SERVER_DATETIME_FORMAT), context=context)
        date_deadline = fields.datetime.context_timestamp(cr, uid, datetime.strptime(meeting.date_deadline, tools.DEFAULT_SERVER_DATETIME_FORMAT), context=context)
        event_date = date.strftime('%B-%d-%Y')
        display_time = date.strftime('%H-%M')
        if meeting.allday:
            time =  _("AllDay , %s") % (event_date)
        elif meeting.duration < 24:
            duration =  date + timedelta(hours= meeting.duration)
            time = ("%s at ( %s To %s) (%s)") % (event_date, display_time, duration.strftime('%H-%M'), tz)
        else :
            time = ("%s at %s To\n %s at %s (%s)") % (event_date, display_time, date_deadline.strftime('%B-%d-%Y'), date_deadline.strftime('%H-%M'), tz)
        return time
    
    def _compute(self, cr, uid, ids, fields, arg, context=None):
        res = {}
        for meeting_id in ids:
            res[meeting_id] = {}
            attendee = self._find_my_attendee(cr, uid, [meeting_id], context)
            for field in fields:
                if field == 'is_attendee':
                    res[meeting_id][field] = True if attendee else False
                elif field == 'attendee_status':
                    res[meeting_id][field] = attendee.state if attendee else 'needs-action'
                elif field == 'display_time':
                    res[meeting_id][field] = self._get_display_time(cr, uid, meeting_id, context=context)
        return res
      
    def _get_rulestring(self, cr, uid, ids, name, arg, context=None):
        """
        Gets Recurrence rule string according to value type RECUR of iCalendar from the values given.
        @return: dictionary of rrule value.
        """

        result = {}
        if not isinstance(ids, list):
            ids = [ids]

        for id in ids:
            #read these fields as SUPERUSER because if the record is private a normal search could return False and raise an error
            data = self.browse(cr, SUPERUSER_ID, id, context=context)
            if data.interval < 0:
                raise osv.except_osv(_('Warning!'), _('Interval cannot be negative.'))
            if data.count <= 0:
                raise osv.except_osv(_('Warning!'), _('Count cannot be negative or 0.'))
           
            data = self.read(cr, uid, id, ['id','byday','recurrency', 'month_list','end_date', 'rrule_type', 'month_by', 'interval', 'count', 'end_type', 'mo', 'tu', 'we', 'th', 'fr', 'sa', 'su', 'day', 'week_list' ], context=context)
            event = data['id']
            if data['recurrency']:
                result[event] = self.compute_rule_string(data)
            else:
                result[event] = ""
        return result

    def _rrule_write(self, obj, cr, uid, ids, field_name, field_value, args, context=None):
        data = self._get_empty_rrule_data()
        if field_value:
            data['recurrency'] = True
            for event in self.browse(cr, uid, ids, context=context):
                rdate = rule_date or event.date #TO CHECK :/
                update_data = self._parse_rrule(field_value, dict(data), rdate)
                data.update(update_data)
                self.write(cr, uid, ids, data, context=context)
        return True

    def _tz_get(self, cr, uid, context=None):
        return [(x.lower(), x) for x in pytz.all_timezones]

    _columns = {
        'create_date': fields.datetime('Creation Date', readonly=True),
        'write_date': fields.datetime('Write Date', readonly=True),
        'state': fields.selection([('draft', 'Unconfirmed'), ('open', 'Confirmed')], string='Status', size=16, readonly=True, track_visibility='onchange'),
        
        # Meeting fields
        'name': fields.char('Meeting Subject', size=128, required=True, states={'done': [('readonly', True)]}),
        'is_attendee': fields.function(_compute, string='Attendee', type="boolean", multi='attendee'),
        'attendee_status': fields.function(_compute, string='Attendee Status', type="selection", multi='attendee'),
        'display_time': fields.function(_compute, string='Event Time', type="char", multi='attendee'),
        
        # ---------------------
        # OLD CALENDAR_EVENT 
        # ---------------------
        'id': fields.integer('ID', readonly=True),
        'sequence': fields.integer('Sequence'),
        
        'date': fields.datetime('Date', states={'done': [('readonly', True)]}, required=True,),
        'date_deadline': fields.datetime('End Date', states={'done': [('readonly', True)]}, required=True,),
        
        'duration': fields.float('Duration', states={'done': [('readonly', True)]}),
        'description': fields.text('Description', states={'done': [('readonly', True)]}),
        'class': fields.selection([('public', 'Public'), ('private', 'Private'), ('confidential', 'Public for Employees')], 'Privacy', states={'done': [('readonly', True)]}),
        'location': fields.char('Location', size=264, help="Location of Event", states={'done': [('readonly', True)]}),
        'show_as': fields.selection([('free', 'Free'), ('busy', 'Busy')], 'Show Time as', states={'done': [('readonly', True)]}),        
        
        #'state': fields.selection([('tentative', 'Uncertain'),('cancelled', 'Cancelled'),('confirmed', 'Confirmed'),],'Status', readonly=True, track_visibility='onchange'),
        
        #FIELD FOR RECURRENCY
        'exdate': fields.text('Exception Date/Times', help="This property defines the list of date/time exceptions for a recurring calendar component."),
        'rrule': fields.function(_get_rulestring, type='char', size=124, fnct_inv=_rrule_write, store=True, string='Recurrent Rule'),
        'rrule_type': fields.selection([('daily', 'Day(s)'),('weekly', 'Week(s)'),('monthly', 'Month(s)'),('yearly', 'Year(s)')], 'Recurrency', states={'done': [('readonly', True)]}, help="Let the event automatically repeat at that interval"),
        'recurrency': fields.boolean('Recurrent', help="Recurrent Meeting"),
        'recurrent_id': fields.integer('Recurrent ID'),
        #'recurrent_id_date': fields.datetime('Recurrent ID date'),
        #'recurrence_end_date': fields.function(_get_recurrence_end_date, type='datetime', store=True, string='Recurrence end date',priority=30),
        'vtimezone': fields.selection(_tz_get, size=64, string='Timezone'),
        'end_type' : fields.selection([('count', 'Number of repetitions'), ('end_date','End date')], 'Recurrence Termination'),
        'interval': fields.integer('Repeat Every', help="Repeat every (Days/Week/Month/Year)"),
        'count': fields.integer('Repeat', help="Repeat x times"),
        'mo': fields.boolean('Mon'),
        'tu': fields.boolean('Tue'),
        'we': fields.boolean('Wed'),
        'th': fields.boolean('Thu'),
        'fr': fields.boolean('Fri'),
        'sa': fields.boolean('Sat'),
        'su': fields.boolean('Sun'),
        'month_by': fields.selection([('date', 'Date of month'),('day', 'Day of month')], 'Option'),
        'day': fields.integer('Date of month'),
        'week_list': fields.selection([('MO', 'Monday'),('TU', 'Tuesday'),('WE', 'Wednesday'),('TH', 'Thursday'),('FR', 'Friday'),('SA', 'Saturday'),('SU', 'Sunday')], 'Weekday'),
        'byday': fields.selection([('1', 'First'),('2', 'Second'),('3', 'Third'),('4', 'Fourth'),('5', 'Fifth'),('-1', 'Last')], 'By day'),
        'end_date': fields.date('Repeat Until'),
        'allday': fields.boolean('All Day', states={'done': [('readonly', True)]}),
        
        'user_id': fields.many2one('res.users', 'Responsible', states={'done': [('readonly', True)]}),        
        'color_partner_id': fields.related('user_id','partner_id','id',type="int",string="colorize",store=False), #Color of creator
        'active': fields.boolean('Active', help="If the active field is set to true, it will allow you to hide the event alarm information without removing it."),

        'categ_ids': fields.many2many('crm.meeting.type', 'meeting_category_rel', 'event_id', 'type_id', 'Tags'),
        'attendee_ids': fields.many2many('calendar.attendee', 'crmmeeting_attendee_rel', 'crmmeeting_id', 'attendee_id', 'Attendees'),
        'partner_ids': fields.many2many('res.partner', string='Attendees', states={'done': [('readonly', True)]}),
        'alarm_ids': fields.many2many('calendar.alarm', string='Reminders'),
    }
    _defaults = {
        'end_type': 'count',
        'count': 1,
        'rrule_type': False,
        'state': 'draft',
        'class': 'public',
        'show_as': 'busy',
        'month_by': 'date',
        'interval': 1,
        'active': 1,
        'user_id': lambda self, cr, uid, ctx: uid,
        'partner_ids': lambda self, cr, uid, ctx: [self.pool.get('res.users').browse(cr, uid, [uid],context=ctx)[0].partner_id.id]
    }
        
    def _check_closing_date(self, cr, uid, ids, context=None):
        for event in self.browse(cr, uid, ids, context=context):
            if event.date_deadline < event.date:
                return False
        return True
    
    _constraints = [
        (_check_closing_date, 'Error ! End date cannot be set before start date.', ['date_deadline']),
    ]
    
    def onchange_dates(self, cr, uid, ids, start_date, duration=False, end_date=False, allday=False, context=None):
        """Returns duration and/or end date based on values passed
        @param ids: List of calendar event's IDs.
        @param start_date: Starting date
        @param duration: Duration between start date and end date
        @param end_date: Ending Datee
        """
        if context is None:
            context = {}

        value = {}
        if not start_date:
            return value
        if not end_date and not duration:
            duration = 1.00
            value['duration'] = duration

        start = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        if allday: # For all day event
            duration = 24.0
            value['duration'] = duration
            # change start_date's time to 00:00:00 in the user's timezone
            user = self.pool.get('res.users').browse(cr, uid, uid)
            tz = pytz.timezone(user.tz) if user.tz else pytz.utc
            start = pytz.utc.localize(start).astimezone(tz)     # convert start in user's timezone
            start = start.replace(hour=0, minute=0, second=0)   # remove time 
            start = start.astimezone(pytz.utc)                  # convert start back to utc
            value['date'] = start.strftime("%Y-%m-%d %H:%M:%S")

        if end_date and not duration:
            end = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
            diff = end - start
            duration = float(diff.days)* 24 + (float(diff.seconds) / 3600)
            value['duration'] = round(duration, 2)
        elif not end_date:
            end = start + timedelta(hours=duration)
            value['date_deadline'] = end.strftime("%Y-%m-%d %H:%M:%S")
        elif end_date and duration and not allday:
            # we have both, keep them synchronized:
            # set duration based on end_date (arbitrary decision: this avoid
            # getting dates like 06:31:48 instead of 06:32:00)
            end = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
            diff = end - start
            duration = float(diff.days)* 24 + (float(diff.seconds) / 3600)
            value['duration'] = round(duration, 2)

        return {'value': value}

    def unlink_events(self, cr, uid, ids, context=None):
        """
        This function deletes event which are linked with the event with recurrent_id
                (Removes the events which refers to the same UID value)
        """
        if context is None:
            context = {}
        for event_id in ids:
            r_ids = self.search(cr,uid,[('recurrent_id','=',event_id)],context=context)
            self.unlink(cr, uid, r_ids, context=context)
        return True

    def new_invitation_token(self, cr, uid, record, partner_id):
        db_uuid = self.pool.get('ir.config_parameter').get_param(cr, uid, 'database.uuid')
        invitation_token = hashlib.sha256('%s-%s-%s-%s-%s' % (time.time(), db_uuid, record._name, record.id, partner_id)).hexdigest()
        return invitation_token
        
    def create_attendees(self, cr, uid, ids, context):
        att_obj = self.pool.get('calendar.attendee')
        user_obj = self.pool.get('res.users')
        current_user = user_obj.browse(cr, uid, uid, context=context)
        for event in self.browse(cr, uid, ids, context):            
            attendees = {}
            for att in event.attendee_ids:
                attendees[att.partner_id.id] = True
            new_attendees = []
            new_att_partner_ids = [] #avoid to rebrowse attendees
            mail_to = ""
            for partner in event.partner_ids:
                if partner.id in attendees:                    
                    continue
                access_token = self.new_invitation_token(cr, uid, event, partner.id)
                att_id = self.pool.get('calendar.attendee').create(cr, uid, {
                    'partner_id': partner.id,
                    'user_id': partner.user_ids and partner.user_ids[0].id or False,
                    'ref': event.id,
                    'access_token': access_token,
                    'email': partner.email,
                }, context=context)
                if partner.email:
                    mail_to = mail_to + " " + partner.email
                new_attendees.append(att_id)
                new_att_partner_ids.append(partner.id)
            
            self.write(cr, uid, [event.id], {'attendee_ids': [(4, att) for att in new_attendees]},context=context)
                        
            # We remove old attendees who are not in partner_ids now.
            all_partner_ids = [part.id for part in event.partner_ids]
            all_attendee_ids = [att.partner_id.id for att in event.attendee_ids]
            partner_ids_to_remove = map(lambda x: x, set(all_attendee_ids + new_att_partner_ids) - set(all_partner_ids))
            
            if partner_ids_to_remove:
                attendee_ids_to_remove =self.pool.get("calendar.attendee").search(cr,uid,[('partner_id.id','in',partner_ids_to_remove),('ref.id','=',event.id)],context=context)
                if attendee_ids_to_remove: 
                    self.pool.get("calendar.attendee").unlink(cr, uid, attendee_ids_to_remove, context) 
            
        return True

    def get_recurrent_ids(self, cr, uid, select, domain, limit=100, context=None):
        """Gives virtual event ids for recurring events based on value of Recurrence Rule
        This method gives ids of dates that comes between start date and end date of calendar views
      
        @param limit: The Number of Results to Return """
        if not context:
            context = {}

        result = []
        for data in self.read(cr, uid, select, ['rrule', 'recurrency', 'exdate', 'date', 'vtimezone'], context=context):
            if not data['recurrency'] or not data['rrule']:
                result.append(data['id'])
                continue
#             event_date = datetime.strptime(data['date'], "%Y-%m-%d %H:%M:%S")
#             event_date = pytz.UTC.localize(event_date)
            rdates = get_recurrent_dates(data['rrule'], data['date'], data['exdate'], data['vtimezone'], context=context)
            for r_date in rdates:
                # fix domain evaluation
                # step 1: check date and replace expression by True or False, replace other expressions by True
                # step 2: evaluation of & and |
                # check if there are one False
                pile = []
                ok = True
                for arg in domain:
                    if str(arg[0]) in (str('date'), str('date_deadline'), str('end_date')):
                        if (arg[1] == '='):
                            ok = r_date.strftime('%Y-%m-%d')==arg[2]
                        if (arg[1] == '>'):
                            ok = r_date.strftime('%Y-%m-%d')>arg[2]
                        if (arg[1] == '<'):
                            ok = r_date.strftime('%Y-%m-%d')<arg[2]
                        if (arg[1] == '>='):
                            ok = r_date.strftime('%Y-%m-%d')>=arg[2]
                        if (arg[1] == '<='):
                            ok = r_date.strftime('%Y-%m-%d')<=arg[2]
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
                # idval = real_id2base_calendar_id(data['id'], r_date.strftime("%Y-%m-%d %H:%M:%S"))
                idval = '%d-%s' % (data['id'], r_date.strftime("%Y%m%d%H%M%S"))    
                result.append(idval)

        if isinstance(select, (str, int, long)):
            return ids and ids[0] or False
        else:
            ids = list(set(result))
        return ids

    def compute_rule_string(self, data):
        """
        Compute rule string according to value type RECUR of iCalendar from the values given.
        @param self: the object pointer
        @param data: dictionary of freq and interval value
        @return: string containing recurring rule (empty if no rule)
        """
        def get_week_string(freq, data):
            weekdays = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
            if freq == 'weekly':
                byday = map(lambda x: x.upper(), filter(lambda x: data.get(x) and x in weekdays, data))
                #byday = map(lambda x: x.upper(),[data[day] for day in weekdays if data[day]]) 
                
                if byday:
                    return ';BYDAY=' + ','.join(byday)
            return ''

        def get_month_string(freq, data):
            if freq == 'monthly':
                if data.get('month_by')=='date' and (data.get('day') < 1 or data.get('day') > 31):
                    raise osv.except_osv(_('Error!'), ("Please select a proper day of the month."))

                if data.get('month_by')=='day': #Eg : Second Monday of the month
                    return ';BYDAY=' + data.get('byday') + data.get('week_list')
                elif data.get('month_by')=='date': #Eg : 16th of the month
                    return ';BYMONTHDAY=' + str(data.get('day'))
            return ''

        def get_end_date(data):
            if data.get('end_date'):
                data['end_date_new'] = ''.join((re.compile('\d')).findall(data.get('end_date'))) + 'T235959Z'

            return (data.get('end_type') == 'count' and (';COUNT=' + str(data.get('count'))) or '') +\
                             ((data.get('end_date_new') and data.get('end_type') == 'end_date' and (';UNTIL=' + data.get('end_date_new'))) or '')

        freq = data.get('rrule_type', False) #day/week/month/year
        res = ''
        if freq:
            interval_srting = data.get('interval') and (';INTERVAL=' + str(data.get('interval'))) or ''
            res = 'FREQ=' + freq.upper() + get_week_string(freq, data) + interval_srting + get_end_date(data) + get_month_string(freq, data)

        return res

    def _get_empty_rrule_data(self):
        return  {
            'byday' : False,
            'recurrency' : False,
            'end_date' : False,
            'rrule_type' : False,
            'month_by' : False,
            'interval' : 0,
            'count' : False,
            'end_type' : False,
            'mo' : False,
            'tu' : False,
            'we' : False,
            'th' : False,
            'fr' : False,
            'sa' : False,
            'su' : False,
            'day' : False,
            'week_list' : False
        }

    def _parse_rrule(self, rule, data, date_start):
        day_list = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
        rrule_type = ['yearly', 'monthly', 'weekly', 'daily']
        r = rrule.rrulestr(rule, dtstart=datetime.strptime(date_start, "%Y-%m-%d %H:%M:%S"))

        if r._freq > 0 and r._freq < 4: 
            data['rrule_type'] = rrule_type[r._freq]

        data['count'] = r._count
        data['interval'] = r._interval
        data['end_date'] = r._until and r._until.strftime("%Y-%m-%d %H:%M:%S")
        #repeat weekly
        if r._byweekday:
            for i in xrange(0,7):
                if i in r._byweekday:
                    data[day_list[i]] = True
            data['rrule_type'] = 'weekly'
        #repeat monthly by nweekday ((weekday, weeknumber), )
        if r._bynweekday:
            data['week_list'] = day_list[r._bynweekday[0][0]].upper()
            data['byday'] = r._bynweekday[0][1]
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
        if not (data.get('count') or data.get('end_date')):
            data['count'] = 100
        if data.get('count'):
            data['end_type'] = 'count'
        else:
            data['end_type'] = 'end_date'
        return data

    #def _get_data(self, cr, uid, id, context=None):
    #    return self.read(cr, uid, id,['date', 'date_deadline'])

#     def need_to_update(self, event_id, vals):
#         split_id = str(event_id).split("-")
#         if len(split_id) < 2:
#             return False
#         else:
#             date_start = vals.get('date', '')
#             try:
#                 date_start = datetime.strptime(date_start, '%Y-%m-%d %H:%M:%S').strftime("%Y%m%d%H%M%S")
#                 return date_start == split_id[1]
#             except Exception:
#                 return True
        
    def message_get_subscription_data(self, cr, uid, ids, user_pid=None, context=None):
        res = {}
        for virtual_id in ids:
            real_id = base_calendar_id2real_id(virtual_id)
            result = super(crm_meeting, self).message_get_subscription_data(cr, uid, [real_id], user_pid=None, context=context)
            res[virtual_id] = result[real_id]
        return res
        
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
        ##TODO : REFACTOR !
        """ Verify that selected partner_ids have an email_address defined.
            Otherwise throw a warning. """
        partner_wo_email_lst = []
        for partner in self.pool.get('res.partner').browse(cr, uid, partner_ids, context=context):
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
                    }
                }
    # ----------------------------------------
    # OpenChatter
    # ----------------------------------------

    # shows events of the day for this user
   
    def _needaction_domain_get(self, cr, uid, context=None):
        return [('end_date', '>=', time.strftime(DEFAULT_SERVER_DATE_FORMAT + ' 23:59:59')), ('date', '>=', time.strftime(DEFAULT_SERVER_DATE_FORMAT + ' 23:59:59')), ('user_id', '=', uid)]

    def message_post(self, cr, uid, thread_id, body='', subject=None, type='notification', subtype=None, parent_id=False, attachments=None, context=None, **kwargs):
        if isinstance(thread_id, str):
            thread_id = get_real_ids(thread_id)
        if context.get('default_date'):
            del context['default_date']
        return super(crm_meeting, self).message_post(cr, uid, thread_id, body=body, subject=subject, type=type, subtype=subtype, parent_id=parent_id, attachments=attachments, context=context, **kwargs)

    def do_sendmail(self, cr, uid, ids, context=None):
        for event in self.browse(cr, uid, ids, context):            
                     
            current_user = self.pool.get('res.users').browse(cr, uid, uid, context=context)                       

            if current_user.email:
                if self.pool.get('calendar.attendee')._send_mail(cr, uid, [att.id for att in event.attendee_ids], '', email_from = current_user.email, context=context):
                    self.message_post(cr, uid, event.id, body=_("An invitation email has been sent to attendee(s)"), context=context)
        return;

    def get_attendee(self, cr, uid, meeting_id, context=None):
        #Used for view in controller 
        invitation = {'meeting':{}, 'attendee': [], 'logo': ''}
        attendee_pool = self.pool.get('calendar.attendee')
        company_logo = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.logo
        meeting = self.browse(cr, uid, int(meeting_id), context)
        invitation['meeting'] = {
                'event':meeting.name,
                'where': meeting.location,
                'when':meeting.display_time
        }
        invitation['logo'] = company_logo.replace('\n','\\n') if company_logo else ''
        for attendee in meeting.attendee_ids:
            invitation['attendee'].append({'name':attendee.cn,'status': attendee.state})
        return invitation

    def get_interval(self, cr, uid, ids, date, interval, context=None):
        #Function used only in crm_meeting_data.xml for email template
        date = datetime.strptime(date, DEFAULT_SERVER_DATETIME_FORMAT)
        if interval == 'day':
            res = str(date.day)
        elif interval == 'month':
            res = date.strftime('%B') + " " + str(date.year)
        elif interval == 'dayname':
            res = date.strftime('%A')
        elif interval == 'time':
            res = date.strftime('%I:%M %p')
        return res
    
    def search(self, cr, uid, args, offset=0, limit=0, order=None, context=None, count=False):
        
        if context is None:
            context={}        
    
        if context.get('mymeetings',False):
            partner_id = self.pool.get('res.users').browse(cr, uid, uid, context).partner_id.id
            args += ['|', ('partner_ids', 'in', [partner_id]), ('user_id', '=', uid)]
        
        new_args = []    
        for arg in args:
            new_arg = arg
            
            if arg[0] in ('date', unicode('date')) and arg[1]==">=":
                if context.get('virtual_id', True):
                    new_args += ['|','&',('recurrency','=',1),('end_date', arg[1], arg[2])]
 #                   new_args += ['|','&',('recurrency','=',1),('date_deadline', arg[1], arg[2])]
            elif arg[0] in ('date', unicode('date')):
                if context.get('virtual_id', True):
                    new_args += ['|','&',('recurrency','=',1),('end_date', arg[1], arg[2])]
 #                   new_args += ['|','&',('recurrency','=',1),('date_deadline', arg[1], arg[2])]
            elif arg[0] == "id":
                new_id = get_real_ids(arg[2])
                new_arg = (arg[0], arg[1], new_id)
            new_args.append(new_arg)
        #offset, limit and count must be treated separately as we may need to deal with virtual ids
        #print 'AFTER SEARCH',new_args
        
        res = super(crm_meeting,self).search(cr, uid, new_args, offset=0, limit=0, order=order, context=context, count=False)
        
        if context.get('virtual_id', True):
            res = self.get_recurrent_ids(cr, uid, res, args, limit, context=context)
        if count:
            return len(res)
        elif limit:
            return res[offset:offset+limit]
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        if context is None:
            context = {}
            
        default = default or {}
        default['attendee_ids'] = False
        
        res = super(crm_meeting, self).copy(cr, uid, base_calendar_id2real_id(id), default, context)
        return res        

    def write(self, cr, uid, ids, values, context=None):
        def _only_changes_to_apply_on_real_ids(field_names):
            ''' return True if changes are only to be made on the real ids'''
            for field in field_names:
                if field not in ['message_follower_ids']:
                    return False
            return True
        
        context = context or {}
        if isinstance(ids, (str, int, long)):
            ids = [ids]
        res = False
                
          
         # Special write of complex IDS
        for event_id in ids[:]:
            if len(str(event_id).split('-')) == 1:
                continue
            ids.remove(event_id)
            real_event_id = base_calendar_id2real_id(event_id)

            # if we are setting the recurrency flag to False or if we are only changing fields that
            # should be only updated on the real ID and not on the virtual (like message_follower_ids):
            # then set real ids to be updated.
            if not values.get('recurrency', True) or _only_changes_to_apply_on_real_ids(values.keys()):
                ids.append(real_event_id)
                continue

            #if edit one instance of a reccurrent id
            data = self.read(cr, uid, event_id, ['date', 'date_deadline', \
                                                'rrule', 'duration', 'exdate'])
            if data.get('rrule'):
                data.update(
                    values,
                    recurrent_id=real_event_id,
                    #recurrent_id_date=data.get('date'),
                    rrule_type=False,
                    rrule='',
                    recurrency=False,
                )
                #do not copy the id
                if data.get('id'):
                    del(data['id'])
                new_id = self.copy(cr, uid, real_event_id, default=data, context=context)

                date_new = event_id.split('-')[1]
                date_new = time.strftime("%Y%m%dT%H%M%SZ", \
                             time.strptime(date_new, "%Y%m%d%H%M%S"))
                exdate = (data['exdate'] and (data['exdate'] + ',')  or '') + date_new
                res = super(crm_meeting, self).write(cr, uid, [real_event_id], {'exdate': exdate})

                context.update({'active_id': new_id, 'active_ids': [new_id]})
                continue

        res = super(crm_meeting, self).write(cr, uid, ids, values, context=context)
        
        # set end_date for calendar searching
        if values.get('recurrency', True) and values.get('end_type', 'count') in ('count', unicode('count')) and \
                (values.get('rrule_type') or values.get('count') or values.get('date') or values.get('date_deadline')):
            for data in self.read(cr, uid, ids, ['date', 'date_deadline', 'recurrency', 'rrule_type', 'count', 'end_type'], context=context):
                end_date = self._get_recurrency_end_date(data, context=context)
                super(crm_meeting, self).write(cr, uid, [data['id']], {'end_date': end_date}, context=context)
        
        if values.get('partner_ids', False):
            self.create_attendees(cr, uid, ids, context)
        
        return res or True and False

    def create(self, cr, uid, vals, context=None):
        
        if context is None:
            context = {}

        if vals.get('duration', '') and vals.get('duration', '')==24 and not 'allday' in vals: #If from quick create
            vals['allday'] = True
        
        if not 'user_id' in vals: #Else bug with quick_create when we are filter on an other user
            vals['user_id'] = uid
            
                
        res = super(crm_meeting, self).create(cr, uid, vals, context=context)
        #res = self.write(cr, uid, id_res,vals, context)
        
        self.create_attendees(cr, uid, [res], context=context)
        return res

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
        
        if not context:
            context = {}

        if 'date' in groupby:
            raise osv.except_osv(_('Warning!'), _('Group by date is not supported, use the calendar view instead.'))
        virtual_id = context.get('virtual_id', True)
        context.update({'virtual_id': False})
        res = super(crm_meeting, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby)
        for re in res:
            #remove the count, since the value is not consistent with the result of the search when expand the group
            for groupname in groupby:
                if re.get(groupname + "_count"):
                    del re[groupname + "_count"]
            re.get('__context', {}).update({'virtual_id' : virtual_id})
        return res

    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
                
        if context is None:
            context = {}
        fields2 = fields and fields[:] or None

        EXTRAFIELDS = ('class','user_id','duration', 'date','rrule', 'vtimezone', 'exdate')
        for f in EXTRAFIELDS:
            if fields and (f not in fields):
                fields2.append(f)

        # FIXME This whole id mangling has to go!
        if isinstance(ids, (str, int, long)):
            select = [ids]
        else:
            select = ids

        select = map(lambda x: (x, base_calendar_id2real_id(x)), select)
        result = []

        real_data = super(crm_meeting, self).read(cr, uid, [real_id for base_calendar_id, real_id in select], fields=fields2, context=context, load=load)
        real_data = dict(zip([x['id'] for x in real_data], real_data))
        
        
        for base_calendar_id, real_id in select:
            res = real_data[real_id].copy()
                
            res = real_data[real_id].copy()
            ls = base_calendar_id2real_id(base_calendar_id, with_date=res and res.get('duration', 0) or 0)
            if not isinstance(ls, (str, int, long)) and len(ls) >= 2:
                recurrent_dates = [d.strftime("%Y-%m-%d %H:%M:%S") for d in get_recurrent_dates(res['rrule'], res['date'], res['exdate'],res['vtimezone'], context=context)]
                
                #if not (ls[1] in recurrent_dates or ls[1] in res['exdate']): #when update a recurrent event
                    
                res['date'] = ls[1]
                res['date_deadline'] = ls[2]
            res['id'] = base_calendar_id
            result.append(res)

        for r in result:
            if r['user_id']:
                user_id = type(r['user_id']) in (tuple,list) and r['user_id'][0] or r['user_id']
                if user_id==uid:
                    continue
            if r['class']=='private':
                for f in r.keys():
                    if f not in ('id','date','date_deadline','duration','user_id','state','interval','count'):
                        if isinstance(r[f], list):
                            r[f] = []
                        else:
                            r[f] = False
                    if f=='name':
                        r[f] = _('Busy')

        for r in result:
            for k in EXTRAFIELDS:
                if (k in r) and (fields and (k not in fields)):
                    del r[k]
        if isinstance(ids, (str, int, long)):
            return result and result[0] or False
        return result
    
    def unlink(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        res = False
        attendee_obj=self.pool.get('calendar.attendee')
        for event_id in ids[:]:
            if len(str(event_id).split('-')) == 1:
                continue

            real_event_id = base_calendar_id2real_id(event_id)
            data = self.read(cr, uid, real_event_id, ['exdate'], context=context)
            date_new = event_id.split('-')[1]
            date_new = time.strftime("%Y%m%dT%H%M%S", \
                         time.strptime(date_new, "%Y%m%d%H%M%S"))
            exdate = (data['exdate'] and (data['exdate'] + ',')  or '') + date_new
            self.write(cr, uid, [real_event_id], {'exdate': exdate}, context=context)
            ids.remove(event_id)
        for event in self.browse(cr, uid, ids, context=context):
            if event.attendee_ids:
                attendee_obj.unlink(cr, uid, [x.id for x in event.attendee_ids], context=context)

        res = super(crm_meeting, self).unlink(cr, uid, ids, context=context)
        self.unlink_events(cr, uid, ids, context=context)
        return res

              
# class mail_mail(osv.osv):
#     _inherit = "mail.mail"
#       
#     _columns = {
#         'date_trigger': fields.datetime('date_trigger'),
#     }
#           
#     def process_email_queue(self, cr, uid, ids=None, context=None):
#         if context is None:
#             context = {}
#         import ipdb; ipdb.set_trace();
#         context['filters'] = (['|',('date_trigger', '=', False),('date_trigger', '>=', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))]) #datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# #         ids_to_send = ids;
# #         for mail in self.browse(cr,uid,ids,context=context):
# #             if mail.date_trigger and datetime.strptime(mail.date_trigger, '%Y-%m-%d %H:%M:%S') >  datetime.now():
# #                 ids_to_send.remove(mail.id)
# #         
# #        return super(mail_mail, self).send(cr, uid, ids_to_send, auto_commit=auto_commit, raise_exception=raise_exception, context=context)                
#         return super(mail_mail, self).process_email_queue(cr, uid, ids=ids, context=context)
  
          
            
class mail_message(osv.osv):
    _inherit = "mail.message"

    def search(self, cr, uid, args, offset=0, limit=0, order=None, context=None, count=False):
        '''
        convert the search on real ids in the case it was asked on virtual ids, then call super()
        '''
        for index in range(len(args)):
            if args[index][0] == "res_id" and isinstance(args[index][2], str):
                args[index][2] = get_real_ids(args[index][2])
        return super(mail_message, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)

    def _find_allowed_model_wise(self, cr, uid, doc_model, doc_dict, context=None):
        if doc_model == 'crm.meeting':
            for virtual_id in self.pool[doc_model].get_recurrent_ids(cr, uid, doc_dict.keys(), [], context=context):
                doc_dict.setdefault(virtual_id, doc_dict[get_real_ids(virtual_id)])
        return super(mail_message, self)._find_allowed_model_wise(cr, uid, doc_model, doc_dict, context=context)

class ir_attachment(osv.osv):
    _inherit = "ir.attachment"

    def search(self, cr, uid, args, offset=0, limit=0, order=None, context=None, count=False):
        '''
        convert the search on real ids in the case it was asked on virtual ids, then call super()
        '''
        for index in range(len(args)):
            if args[index][0] == "res_id" and isinstance(args[index][2], str):
                args[index][2] = get_real_ids(args[index][2])
        return super(ir_attachment, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)

    def write(self, cr, uid, ids, vals, context=None):
        '''
        when posting an attachment (new or not), convert the virtual ids in real ids.
        '''
        if isinstance(vals.get('res_id'), str):
            vals['res_id'] = get_real_ids(vals.get('res_id'))
        return super(ir_attachment, self).write(cr, uid, ids, vals, context=context)

class invite_wizard(osv.osv_memory):
    _inherit = 'mail.wizard.invite'

    def default_get(self, cr, uid, fields, context=None):
        '''
        in case someone clicked on 'invite others' wizard in the followers widget, transform virtual ids in real ids
        '''
        result = super(invite_wizard, self).default_get(cr, uid, fields, context=context)
        if 'res_id' in result:
            result['res_id'] = get_real_ids(result['res_id'])
        return result

