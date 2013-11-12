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

from datetime import datetime, timedelta, date
from dateutil import parser
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from openerp.osv import fields, osv
from openerp.tools.translate import _
import pytz
import re
import time
from openerp import tools
import openerp.service.report

def get_recurrent_dates(rrulestring, startdate, exdate=None, tz=None, exrule=None, context=None):
    """Get recurrent dates based on Rule string considering exdate and start date.

    All input dates and output dates are in UTC. Dates are infered
    thanks to rules in the ``tz`` timezone if given, else it'll be in
    the current local timezone as specified in the context.

    @param rrulestring: rulestring (ie: 'FREQ=DAILY;INTERVAL=1;COUNT=3')
    @param exdate: string of dates separated by commas (ie: '20130506220000Z,20130507220000Z')
    @param startdate: string start date for computing recurrent dates
    @param tz: pytz timezone for computing recurrent dates
    @param exrule: string exrule
    @return: list of Recurrent dates

    """

    exdate = exdate.split(',') if exdate else []
    startdate = pytz.UTC.localize(
        datetime.strptime(startdate, "%Y-%m-%d %H:%M:%S"))

    def todate(date):
        val = parser.parse(''.join((re.compile('\d')).findall(date)))
        ## Dates are localized to saved timezone if any, else defaulted to
        ## current timezone. WARNING: these last event dates are considered as
        ## "floating" dates.
        if not val.tzinfo:
            val = pytz.UTC.localize(val)
        return val.astimezone(timezone)

    ## Note that we haven't any context tz info when called by the server, so
    ## we'll default to UTC which could induce one-day errors in date
    ## calculation.
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

    if exrule:
        rset1.exrule(rrule.rrulestr(str(exrule), dtstart=startdate))

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

def real_id2base_calendar_id(real_id, recurrent_date):
#     """
#     Convert a real event id (type int) into a "virtual/recurring event id" (type string).
#     E.g. real event id is 1 and recurrent_date is set to 01-12-2009 10:00:00, so
#     it will return 1-20091201100000.
#     @param real_id: real event id
#     @param recurrent_date: real event recurrent date
#     @return: string containing the real id and the recurrent date
#     """
#     if real_id and recurrent_date:
#         recurrent_date = time.strftime("%Y%m%d%H%M%S", time.strptime(recurrent_date, "%Y-%m-%d %H:%M:%S"))
#         return '%d-%s' % (real_id, recurrent_date)
#     return real_id
    raise  osv.except_osv(_('Warning!'), _('Methode removed ! :/ '))


class calendar_attendee(osv.osv):
    """
    Calendar Attendee Information
    """
    _name = 'calendar.attendee'
    _description = 'Attendee information'
    _rec_name = 'cutype'

    __attribute__ = {}

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
        'cutype': fields.selection([('individual', 'Individual'), ('group', 'Group'), ('resource', 'Resource'), ('room', 'Room'), ('unknown', 'Unknown') ], 'Invite Type', help="Specify the type of Invitation"),
        'state': fields.selection([('needs-action', 'Needs Action'),('tentative', 'Uncertain'),('declined', 'Declined'),('accepted', 'Accepted')], 'Status', readonly=True, help="Status of the attendee's participation"),
        'rsvp':  fields.boolean('Required Reply?', help="Indicats whether the favor of a reply is requested"),
        'cn': fields.function(_compute_data, string='Common name', type="char", size=124, multi='cn', store=True),
        'dir': fields.char('URI Reference', size=124, help="Reference to the URI that points to the directory information corresponding to the attendee."),
        'partner_id': fields.many2one('res.partner', 'Contact'),
        'email': fields.char('Email', size=124, help="Email of Invited Person"),
        'event_date': fields.function(_compute_data, string='Event Date', type="datetime", multi='event_date'),
        'event_end_date': fields.function(_compute_data, string='Event End Date', type="datetime", multi='event_end_date'),
        'availability': fields.selection([('free', 'Free'), ('busy', 'Busy')], 'Free/Busy', readonly="True"),
        'access_token':fields.char('Invitation Token', size=256),        
        'ref': fields.many2one('crm.meeting','Meeting linked'),
        
    }
    _defaults = {
        'state': 'needs-action',
        'rsvp':  True,
        'cutype': 'individual',
    }

    def copy(self, cr, uid, id, default=None, context=None):
        raise osv.except_osv(_('Warning!'), _('You cannot duplicate a calendar attendee.'))
    
    def onchange_partner_id(self, cr, uid, ids, partner_id,context=None):
        """
        Make entry on email and availability on change of partner_id field.
        @param partner_id: changed value of partner id
        @return: dictionary of values which put value in email and availability fields
        """
        
        if not partner_id:
            return {'value': {'email': ''}}
        partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
        return {'value': {'email': partner.email}}
    
    def get_ics_file(self, cr, uid, event_obj, context=None):
        """
        Returns iCalendar file for the event invitation.
        @param self: the object pointer
        @param cr: the current row, from the database cursor
        @param uid: the current user's id for security checks
        @param event_obj: event object (browse record)
        @param context: a standard dictionary for contextual values
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

        #"TO DO == replace by alarm ids"
        
#         if event_obj.alarm_id:
#             # computes alarm data
#             valarm = event.add('valarm')
#             alarm_object = self.pool.get('res.alarm')
#             alarm_data = alarm_object.read(cr, uid, event_obj.alarm_id.id, context=context)
#             # Compute trigger data
#             interval = alarm_data['trigger_interval']
#             occurs = alarm_data['trigger_occurs']
#             duration = (occurs == 'after' and alarm_data['trigger_duration']) \
#                                             or -(alarm_data['trigger_duration'])
#             related = alarm_data['trigger_related']
#             trigger = valarm.add('TRIGGER')
#             trigger.params['related'] = [related.upper()]
#             if interval == 'days':
#                 delta = timedelta(days=duration)
#             if interval == 'hours':
#                 delta = timedelta(hours=duration)
#             if interval == 'minutes':
#                 delta = timedelta(minutes=duration)
#             trigger.value = delta
#             # Compute other details
#             valarm.add('DESCRIPTION').value = alarm_data['name'] or 'OpenERP'

        for attendee in event_obj.attendee_ids:
            attendee_add = event.add('attendee')
            attendee_add.params['CUTYPE'] = [str(attendee.cutype)]
            #attendee_add.params['ROLE'] = [str(attendee.role)]
            attendee_add.params['RSVP'] = [str(attendee.rsvp)]
            attendee_add.value = 'MAILTO:' + (attendee.email or '')
        res = cal.serialize()
        return res

    def _send_mail(self, cr, uid, ids, mail_to, email_from=tools.config.get('email_from', False), context=None):
        """
        Send mail for event invitation to event attendees.
        @param email_from: email address for user sending the mail
        @return: True
        """
        mail_id = []
        data_pool = self.pool.get('ir.model.data')
        mail_pool = self.pool.get('mail.mail')
        template_pool = self.pool.get('email.template')
        local_context = context.copy()
        color = {
                 'needs-action' : 'grey',
                 'accepted' :'green',
                 'tentative' :'#FFFF00',
                 'declined':'red',
                 'delegated':'grey'
        }
        for attendee in self.browse(cr, uid, ids, context=context):
            res_obj = attendee.ref
            if res_obj:
                model,template_id = data_pool.get_object_reference(cr, uid, 'base_calendar', "crm_email_template_meeting_invitation")
                model,act_id = data_pool.get_object_reference(cr, uid, 'base_calendar', "view_crm_meeting_calendar")
                action_id = self.pool.get('ir.actions.act_window').search(cr, uid, [('view_id','=',act_id)], context=context)
                base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url', default='http://localhost:8069', context=context)
                body = template_pool.browse(cr, uid, template_id, context=context).body_html
                if attendee.email and email_from:
                    ics_file = self.get_ics_file(cr, uid, res_obj, context=context)
                    local_context['att_obj'] = attendee
                    local_context['color'] = color
                    local_context['action_id'] = action_id[0]
                    local_context['dbname'] = cr.dbname
                    local_context['base_url'] = base_url
                    vals = template_pool.generate_email(cr, uid, template_id, res_obj.id, context=local_context)
                    if ics_file:
                        vals['attachment_ids'] = [(0,0,{'name': 'invitation.ics',
                                                    'datas_fname': 'invitation.ics',
                                                    'datas': str(ics_file).encode('base64')})]
                    if not attendee.partner_id.opt_out:
                        mail_id.append(mail_pool.create(cr, uid, vals, context=context))
        if mail_id:
            return mail_pool.send(cr, uid, mail_id, context=context)
        return False

    def onchange_user_id(self, cr, uid, ids, user_id, *args, **argv):
        """
        Make entry on email and availbility on change of user_id field.
        @param ids: list of calendar attendee's IDs
        @param user_id: changed value of User id
        @return: dictionary of values which put value in email and availability fields
        """

        if not user_id:
            return {'value': {'email': ''}}
        usr_obj = self.pool.get('res.users')
        user = usr_obj.browse(cr, uid, user_id, *args)
        return {'value': {'email': user.email, 'availability':user.availability}}

    def do_tentative(self, cr, uid, ids, context=None, *args):
        """
        Makes event invitation as Tentative.
        @param ids: list of calendar attendee's IDs
        @param *args: get Tupple value
        @param context: a standard dictionary for contextual values
        """
        return self.write(cr, uid, ids, {'state': 'tentative'}, context)

    def do_accept(self, cr, uid, ids, context=None, *args):
        """
        Marks event invitation as Accepted.
        @param ids: list of calendar attendee's IDs
        @param context: a standard dictionary for contextual values
        @return: True
        """
        if context is None:
            context = {}
        meeting_obj =  self.pool.get('crm.meeting')
        res = self.write(cr, uid, ids, {'state': 'accepted'}, context)
        for attandee in self.browse(cr, uid, ids, context=context):
            meeting_ids = meeting_obj.search(cr, uid, [('attendee_ids', '=', attandee.id)], context=context)
            if meeting_ids:
                meeting_obj.message_post(cr, uid, get_real_ids(meeting_ids), body=_(("%s has accepted invitation") % (attandee.cn)), context=context)
        return res
        
    def do_decline(self, cr, uid, ids, context=None, *args):
        """
        Marks event invitation as Declined.
        @param ids: list of calendar attendee's IDs
        @param *args: get Tupple value
        @param context: a standard dictionary for contextual values
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

# 
# class res_alarm(osv.osv):
#     """Resource Alarm """
#     _name = 'res.alarm'
#     _description = 'Basic Alarm Information'
# 
#     _columns = {
#         'name':fields.char('Name', size=256, required=True),
#         'trigger_occurs': fields.selection([('before', 'Before'), ('after', 'After')], 'Triggers', required=True),
#         'trigger_interval': fields.selection([('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days')], 'Interval', required=True),
#         'trigger_duration': fields.integer('Duration', required=True),
#         'trigger_related': fields.selection([('start', 'The event starts'), ('end', 'The event ends')], 'Related to', required=True),
#         'duration': fields.integer('Duration', help="""Duration' and 'Repeat' are both optional, but if one occurs, so MUST the other"""),
#         'repeat': fields.integer('Repeat'),
#         'active': fields.boolean('Active', help="If the active field is set to true, it will allow you to hide the event alarm information without removing it.")
#     }
#     _defaults = {
#         'trigger_interval': 'minutes',
#         'trigger_duration': 5,
#         'trigger_occurs': 'before',
#         'trigger_related': 'start',
#         'active': 1,
#     }
# 
#     def do_alarm_create(self, cr, uid, ids, model, date, context=None):
#         """
#         Create Alarm for event.
#         @param model: Model name.
#         @param date: Event date
#         @param context: A standard dictionary for contextual values
#         @return: True
#         """
#         if context is None:
#             context = {}
#         alarm_obj = self.pool.get('calendar.alarm')
#         res_alarm_obj = self.pool.get('res.alarm')
#         ir_obj = self.pool.get('ir.model')
#         model_id = ir_obj.search(cr, uid, [('model', '=', model)])[0]
# 
#         model_obj = self.pool[model]
#         for data in model_obj.browse(cr, uid, ids, context=context):
# 
#             basic_alarm = data.alarm_id
#             cal_alarm = data.base_calendar_alarm_id
#             if (not basic_alarm and cal_alarm) or (basic_alarm and cal_alarm):
#                 new_res_alarm = None
#                 # Find for existing res.alarm
#                 duration = cal_alarm.trigger_duration
#                 interval = cal_alarm.trigger_interval
#                 occurs = cal_alarm.trigger_occurs
#                 related = cal_alarm.trigger_related
#                 domain = [('trigger_duration', '=', duration), ('trigger_interval', '=', interval), ('trigger_occurs', '=', occurs), ('trigger_related', '=', related)]
#                 alarm_ids = res_alarm_obj.search(cr, uid, domain, context=context)
#                 if not alarm_ids:
#                     val = {
#                             'trigger_duration': duration,
#                             'trigger_interval': interval,
#                             'trigger_occurs': occurs,
#                             'trigger_related': related,
#                             'name': str(duration) + ' ' + str(interval) + ' '  + str(occurs)
#                            }
#                     new_res_alarm = res_alarm_obj.create(cr, uid, val, context=context)
#                 else:
#                     new_res_alarm = alarm_ids[0]
#                 cr.execute('UPDATE %s ' % model_obj._table + \
#                             ' SET base_calendar_alarm_id=%s, alarm_id=%s ' \
#                             ' WHERE id=%s',
#                             (cal_alarm.id, new_res_alarm, data.id))
# 
#             self.do_alarm_unlink(cr, uid, [data.id], model)
#             if basic_alarm:
#                 vals = {
#                     'action': 'display',
#                     'description': data.description,
#                     'name': data.name,
#                     'attendee_ids': [(6, 0, map(lambda x:x.id, data.attendee_ids))],
#                     'trigger_related': basic_alarm.trigger_related,
#                     'trigger_duration': basic_alarm.trigger_duration,
#                     'trigger_occurs': basic_alarm.trigger_occurs,
#                     'trigger_interval': basic_alarm.trigger_interval,
#                     'duration': basic_alarm.duration,
#                     'repeat': basic_alarm.repeat,
#                     'state': 'run',
#                     'event_date': data[date],
#                     'res_id': data.id,
#                     'model_id': model_id,
#                     'user_id': uid
#                  }
#                 alarm_id = alarm_obj.create(cr, uid, vals)
#                 cr.execute('UPDATE %s ' % model_obj._table + \
#                             ' SET base_calendar_alarm_id=%s, alarm_id=%s '
#                             ' WHERE id=%s', \
#                             ( alarm_id, basic_alarm.id, data.id) )
#         return True
# 
#     def do_alarm_unlink(self, cr, uid, ids, model, context=None):
#         """
#         Delete alarm specified in ids
#         @param cr: the current row, from the database cursor,
#         @param uid: the current user's ID for security checks,
#         @param ids: List of res alarm's IDs.
#         @param model: Model name for which alarm is to be cleared.
#         @return: True
#         """
#         if context is None:
#             context = {}
#         alarm_obj = self.pool.get('calendar.alarm')
#         ir_obj = self.pool.get('ir.model')
#         model_id = ir_obj.search(cr, uid, [('model', '=', model)])[0]
#         model_obj = self.pool[model]
#         for data in model_obj.browse(cr, uid, ids, context=context):
#             alarm_ids = alarm_obj.search(cr, uid, [('model_id', '=', model_id), ('res_id', '=', data.id)])
#             if alarm_ids:
#                 alarm_obj.unlink(cr, uid, alarm_ids)
#                 cr.execute('Update %s set base_calendar_alarm_id=NULL, alarm_id=NULL\
#                             where id=%%s' % model_obj._table,(data.id,))
#         return True
# 
# class calendar_alarm(osv.osv):
#     _name = 'calendar.alarm'
#     _description = 'Event alarm information'
#     _inherit = 'res.alarm'
#     __attribute__ = {}
# 
#     _columns = {
#         'alarm_id': fields.many2one('res.alarm', 'Basic Alarm', ondelete='cascade'),
#         'name': fields.char('Summary', size=124, help="""Contains the text to be \
#                      used as the message subject for email \
#                      or contains the text to be used for display"""),
#         'action': fields.selection([('audio', 'Audio'), ('display', 'Display'), \
#                 ('procedure', 'Procedure'), ('email', 'Email') ], 'Action', \
#                 required=True, help="Defines the action to be invoked when an alarm is triggered"),
#         'description': fields.text('Description', help='Provides a more complete \
#                             description of the calendar component, than that \
#                             provided by the "SUMMARY" property'),
#         'attendee_ids': fields.many2many('calendar.attendee', 'alarm_attendee_rel', \
#                                       'alarm_id', 'attendee_id', 'Attendees', readonly=True),
#         'attach': fields.binary('Attachment', help="""* Points to a sound resource,\
#                      which is rendered when the alarm is triggered for audio,
#                     * File which is intended to be sent as message attachments for email,
#                     * Points to a procedure resource, which is invoked when\
#                       the alarm is triggered for procedure."""),
#         'res_id': fields.integer('Resource ID'),
#         'model_id': fields.many2one('ir.model', 'Model'),
#         'user_id': fields.many2one('res.users', 'Owner'),
#         'event_date': fields.datetime('Event Date'),
#         'event_end_date': fields.datetime('Event End Date'),
#         'trigger_date': fields.datetime('Trigger Date', readonly="True"),
#         'state':fields.selection([
#                     ('draft', 'Draft'),
#                     ('run', 'Run'),
#                     ('stop', 'Stop'),
#                     ('done', 'Done'),
#                 ], 'Status', select=True, readonly=True),
#      }
# 
#     _defaults = {
#         'action': 'email',
#         'state': 'run',
#      }
# 
#     def create(self, cr, uid, vals, context=None):
#         """
#         Overrides orm create method.
#         @param self: The object pointer
#         @param cr: the current row, from the database cursor,
#         @param vals: dictionary of fields value.{'name_of_the_field': value, ...}
#         @param context: A standard dictionary for contextual values
#         @return: new record id for calendar_alarm.
#         """
#         if context is None:
#             context = {}
#         event_date = vals.get('event_date', False)
#         if event_date:
#             dtstart = datetime.strptime(vals['event_date'], "%Y-%m-%d %H:%M:%S")
#             if vals['trigger_interval'] == 'days':
#                 delta = timedelta(days=vals['trigger_duration'])
#             if vals['trigger_interval'] == 'hours':
#                 delta = timedelta(hours=vals['trigger_duration'])
#             if vals['trigger_interval'] == 'minutes':
#                 delta = timedelta(minutes=vals['trigger_duration'])
#             trigger_date = dtstart + (vals['trigger_occurs'] == 'after' and delta or -delta)
#             vals['trigger_date'] = trigger_date
#         res = super(calendar_alarm, self).create(cr, uid, vals, context=context)
#         return res

class res_partner(osv.osv): 
    _inherit = 'res.partner'
    
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

    def do_run_scheduler(self, cr, uid, automatic=False, use_new_cursor=False, \
                       context=None):
        """Scheduler for event reminder
        @param ids: List of calendar alarm's IDs.
        @param use_new_cursor: False or the dbname
        """
        if context is None:
            context = {}
        current_datetime = datetime.now()
        alarm_ids = self.search(cr, uid, [('state', '!=', 'done')], context=context)

        mail_to = ""

        for alarm in self.browse(cr, uid, alarm_ids, context=context):
            next_trigger_date = None
            update_vals = {}
            model_obj = self.pool[alarm.model_id.model]
            res_obj = model_obj.browse(cr, uid, alarm.res_id, context=context)
            re_dates = []

            if hasattr(res_obj, 'rrule') and res_obj.rrule:
                recurrent_dates = get_recurrent_dates(res_obj.rrule, res_obj.date, res_obj.exdate, res_obj.vtimezone, res_obj.exrule, context=context)

                trigger_interval = alarm.trigger_interval
                if trigger_interval == 'days':
                    delta = timedelta(days=alarm.trigger_duration)
                if trigger_interval == 'hours':
                    delta = timedelta(hours=alarm.trigger_duration)
                if trigger_interval == 'minutes':
                    delta = timedelta(minutes=alarm.trigger_duration)
                delta = alarm.trigger_occurs == 'after' and delta or -delta

                for rdate in recurrent_dates:
                    if rdate + delta > current_datetime:
                        break
                    if rdate + delta <= current_datetime:
                        re_dates.append(rdate.strftime("%Y-%m-%d %H:%M:%S"))
                rest_dates = recurrent_dates[len(re_dates):]
                next_trigger_date = rest_dates and rest_dates[0] or None

            else:
                re_dates = [alarm.trigger_date]

            if re_dates:
                if alarm.action == 'email':
                    sub = '[OpenERP Reminder] %s' % (alarm.name)
                    body = """<pre>Event: %s    
                                    Event Date: %s
                                    Description: %s
                                    From: %s                                
                                    ----
                                    %s
                              </pre>"""  % (alarm.name, alarm.trigger_date, alarm.description, alarm.user_id.name, alarm.user_id.signature)
                    mail_to = alarm.user_id.email
                    for att in alarm.attendee_ids:
                        mail_to = mail_to + " " + att.user_id.email
                    if mail_to:
                        vals = {
                            'state': 'outgoing',
                            'subject': sub,
                            'body_html': body,
                            'email_to': mail_to,
                            'email_from': tools.config.get('email_from', mail_to),
                        }
                        self.pool.get('mail.mail').create(cr, uid, vals, context=context)
            if next_trigger_date:
                update_vals.update({'trigger_date': next_trigger_date})
            else:
                update_vals.update({'state': 'done'})
            self.write(cr, uid, [alarm.id], update_vals)
        return True


class calendar_alarm(osv.osv):
    _name = 'calendar.alarm'
    _description = 'Event alarm'

    _columns = {
        'name':fields.char('Name', size=256, required=True), # fields function
        'type': fields.selection([('notification', 'Notification'), ('email', 'Email')], 'Type', required=True),
        'duration': fields.integer('Amount', required=True),
        'interval': fields.selection([('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days')], 'Unit', required=True),
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


