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
from openerp.service import web_services
from openerp.tools.translate import _

import pytz
import re
import time
from operator import itemgetter
from openerp import tools, SUPERUSER_ID

months = {
    1: "January", 2: "February", 3: "March", 4: "April", \
    5: "May", 6: "June", 7: "July", 8: "August", 9: "September", \
    10: "October", 11: "November", 12: "December"
}

def get_recurrent_dates(rrulestring, exdate, startdate=None, exrule=None):
    """
    Get recurrent dates based on Rule string considering exdate and start date.
    @param rrulestring: rulestring
    @param exdate: list of exception dates for rrule
    @param startdate: startdate for computing recurrent dates
    @return: list of Recurrent dates
    """
    def todate(date):
        val = parser.parse(''.join((re.compile('\d')).findall(date)))
        return val

    if not startdate:
        startdate = datetime.now()

    if not exdate:
        exdate = []

    rset1 = rrule.rrulestr(str(rrulestring), dtstart=startdate, forceset=True)
    for date in exdate:
        datetime_obj = todate(date)
        rset1._exdate.append(datetime_obj)

    if exrule:
        rset1.exrule(rrule.rrulestr(str(exrule), dtstart=startdate))

    return list(rset1)

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
                real_date = time.strftime("%Y-%m-%d %H:%M:%S", \
                                 time.strptime(res[1], "%Y%m%d%H%M%S"))
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
    """
    Convert a real event id (type int) into a "virtual/recurring event id" (type string).
    E.g. real event id is 1 and recurrent_date is set to 01-12-2009 10:00:00, so
    it will return 1-20091201100000.
    @param real_id: real event id
    @param recurrent_date: real event recurrent date
    @return: string containing the real id and the recurrent date
    """
    if real_id and recurrent_date:
        recurrent_date = time.strftime("%Y%m%d%H%M%S", \
                            time.strptime(recurrent_date, "%Y-%m-%d %H:%M:%S"))
        return '%d-%s' % (real_id, recurrent_date)
    return real_id

def _links_get(self, cr, uid, context=None):
    """
    Get request link.
    @param cr: the current row, from the database cursor
    @param uid: the current user's ID for security checks
    @param context: a standard dictionary for contextual values
    @return: list of dictionary which contain object and name and id
    """
    obj = self.pool.get('res.request.link')
    ids = obj.search(cr, uid, [])
    res = obj.read(cr, uid, ids, ['object', 'name'], context=context)
    return [(r['object'], r['name']) for r in res]

html_invitation = """
<html>
<head>
<meta http-equiv="Content-type" content="text/html; charset=utf-8" />
<title>%(name)s</title>
</head>
<body>
<table border="0" cellspacing="10" cellpadding="0" width="100%%"
    style="font-family: Arial, Sans-serif; font-size: 14">
    <tr>
        <td width="100%%">Hello,</td>
    </tr>
    <tr>
        <td width="100%%">You are invited for <i>%(company)s</i> Event.</td>
    </tr>
    <tr>
        <td width="100%%">Below are the details of event. Hours and dates expressed in %(timezone)s time.</td>
    </tr>
</table>

<table cellspacing="0" cellpadding="5" border="0" summary=""
    style="width: 90%%; font-family: Arial, Sans-serif; border: 1px Solid #ccc; background-color: #f6f6f6">
    <tr valign="center" align="center">
        <td bgcolor="DFDFDF">
        <h3>%(name)s</h3>
        </td>
    </tr>
    <tr>
        <td>
        <table cellpadding="8" cellspacing="0" border="0"
            style="font-size: 14" summary="Eventdetails" bgcolor="f6f6f6"
            width="90%%">
            <tr>
                <td width="21%%">
                <div><b>Start Date</b></div>
                </td>
                <td><b>:</b></td>
                <td>%(start_date)s</td>
                <td width="15%%">
                <div><b>End Date</b></div>
                </td>
                <td><b>:</b></td>
                <td width="25%%">%(end_date)s</td>
            </tr>
            <tr valign="top">
                <td><b>Description</b></td>
                <td><b>:</b></td>
                <td colspan="3">%(description)s</td>
            </tr>
            <tr valign="top">
                <td>
                <div><b>Location</b></div>
                </td>
                <td><b>:</b></td>
                <td colspan="3">%(location)s</td>
            </tr>
            <tr valign="top">
                <td>
                <div><b>Event Attendees</b></div>
                </td>
                <td><b>:</b></td>
                <td colspan="3">
                <div>
                <div>%(attendees)s</div>
                </div>
                </td>
            </tr>
        </table>
        </td>
    </tr>
</table>
<table border="0" cellspacing="10" cellpadding="0" width="100%%"
    style="font-family: Arial, Sans-serif; font-size: 14">
    <tr>
        <td width="100%%">From:</td>
    </tr>
    <tr>
        <td width="100%%">%(user)s</td>
    </tr>
    <tr valign="top">
        <td width="100%%">-<font color="a7a7a7">-------------------------</font></td>
    </tr>
    <tr>
        <td width="100%%"> <font color="a7a7a7">%(sign)s</font></td>
    </tr>
</table>
</body>
</html>
"""

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
        @param cr: the current row, from the database cursor
        @param uid: the current user's ID for security checks
        @param ids: list of calendar attendee's IDs
        @param name: name of field
        @param context: a standard dictionary for contextual values
        @return: dictionary of form {id: {'field Name': value'}}
        """
        name = name[0]
        result = {}
        for attdata in self.browse(cr, uid, ids, context=context):
            id = attdata.id
            result[id] = {}
            if name == 'sent_by':
                if not attdata.sent_by_uid:
                    result[id][name] = ''
                    continue
                else:
                    result[id][name] = self._get_address(attdata.sent_by_uid.name, \
                                        attdata.sent_by_uid.email)

            if name == 'cn':
                if attdata.user_id:
                    result[id][name] = attdata.user_id.name
                elif attdata.partner_id:
                    result[id][name] = attdata.partner_id.name or False
                else:
                    result[id][name] = attdata.email or ''

            if name == 'delegated_to':
                todata = []
                for child in attdata.child_ids:
                    if child.email:
                        todata.append('MAILTO:' + child.email)
                result[id][name] = ', '.join(todata)

            if name == 'delegated_from':
                fromdata = []
                for parent in attdata.parent_ids:
                    if parent.email:
                        fromdata.append('MAILTO:' + parent.email)
                result[id][name] = ', '.join(fromdata)

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

            if name == 'sent_by_uid':
                if attdata.ref:
                    result[id][name] = (attdata.ref.user_id.id, attdata.ref.user_id.name)
                else:
                    result[id][name] = uid

            if name == 'language':
                user_obj = self.pool.get('res.users')
                lang = user_obj.read(cr, uid, uid, ['lang'], context=context)['lang']
                result[id][name] = lang.replace('_', '-') if lang else False

        return result

    def _links_get(self, cr, uid, context=None):
        """
        Get request link for ref field in calendar attendee.
        @param cr: the current row, from the database cursor
        @param uid: the current user's id for security checks
        @param context: A standard dictionary for contextual values
        @return: list of dictionary which contain object and name and id
        """
        obj = self.pool.get('res.request.link')
        ids = obj.search(cr, uid, [])
        res = obj.read(cr, uid, ids, ['object', 'name'], context=context)
        return [(r['object'], r['name']) for r in res]

    def _lang_get(self, cr, uid, context=None):
        """
        Get language for language selection field.
        @param cr: the current row, from the database cursor
        @param uid: the current user's id for security checks
        @param context: a standard dictionary for contextual values
        @return: list of dictionary which contain code and name and id
        """
        obj = self.pool.get('res.lang')
        ids = obj.search(cr, uid, [])
        res = obj.read(cr, uid, ids, ['code', 'name'], context=context)
        res = [((r['code']).replace('_', '-').lower(), r['name']) for r in res]
        return res

    _columns = {
        'cutype': fields.selection([('individual', 'Individual'), \
                    ('group', 'Group'), ('resource', 'Resource'), \
                    ('room', 'Room'), ('unknown', 'Unknown') ], \
                    'Invite Type', help="Specify the type of Invitation"),
        'member': fields.char('Member', size=124,
                    help="Indicate the groups that the attendee belongs to"),
        'role': fields.selection([('req-participant', 'Participation required'), \
                    ('chair', 'Chair Person'), \
                    ('opt-participant', 'Optional Participation'), \
                    ('non-participant', 'For information Purpose')], 'Role', \
                    help='Participation role for the calendar user'),
        'state': fields.selection([('needs-action', 'Needs Action'),
                        ('tentative', 'Uncertain'),
                        ('declined', 'Declined'),
                        ('accepted', 'Accepted'),
                        ('delegated', 'Delegated')], 'Status', readonly=True, \
                        help="Status of the attendee's participation"),
        'rsvp':  fields.boolean('Required Reply?',
                    help="Indicats whether the favor of a reply is requested"),
        'delegated_to': fields.function(_compute_data, \
                string='Delegated To', type="char", size=124, store=True, \
                multi='delegated_to', help="The users that the original \
request was delegated to"),
        'delegated_from': fields.function(_compute_data, string=\
            'Delegated From', type="char", store=True, size=124, multi='delegated_from'),
        'parent_ids': fields.many2many('calendar.attendee', 'calendar_attendee_parent_rel', \
                                    'attendee_id', 'parent_id', 'Delegrated From'),
        'child_ids': fields.many2many('calendar.attendee', 'calendar_attendee_child_rel', \
                                      'attendee_id', 'child_id', 'Delegrated To'),
        'sent_by': fields.function(_compute_data, string='Sent By', \
                        type="char", multi='sent_by', store=True, size=124, \
                        help="Specify the user that is acting on behalf of the calendar user"),
        'sent_by_uid': fields.function(_compute_data, string='Sent By User', \
                            type="many2one", relation="res.users", multi='sent_by_uid'),
        'cn': fields.function(_compute_data, string='Common name', \
                            type="char", size=124, multi='cn', store=True),
        'dir': fields.char('URI Reference', size=124, help="Reference to the URI\
that points to the directory information corresponding to the attendee."),
        'language': fields.function(_compute_data, string='Language', \
                    type="selection", selection=_lang_get, multi='language', \
                    store=True, help="To specify the language for text values in a\
property or property parameter."),
        'user_id': fields.many2one('res.users', 'User'),
        'partner_id': fields.many2one('res.partner', 'Contact'),
        'email': fields.char('Email', size=124, help="Email of Invited Person"),
        'event_date': fields.function(_compute_data, string='Event Date', \
                            type="datetime", multi='event_date'),
        'event_end_date': fields.function(_compute_data, \
                            string='Event End Date', type="datetime", \
                            multi='event_end_date'),
        'ref': fields.reference('Event Ref', selection=_links_get, size=128),
        'availability': fields.selection([('free', 'Free'), ('busy', 'Busy')], 'Free/Busy', readonly="True"),
    }
    _defaults = {
        'state': 'needs-action',
        'role': 'req-participant',
        'rsvp':  True,
        'cutype': 'individual',
    }


    def copy(self, cr, uid, id, default=None, context=None):
        raise osv.except_osv(_('Warning!'), _('You cannot duplicate a calendar attendee.'))
    
    def onchange_partner_id(self, cr, uid, ids, partner_id,context=None):
        """
        Make entry on email and availbility on change of partner_id field.
        @param cr: the current row, from the database cursor
        @param uid: the current user's ID for security checks
        @param ids: list of calendar attendee's IDs
        @param partner_id: changed value of partner id
        @param context: a standard dictionary for contextual values
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
        if event_obj.organizer:
            event_org = event.add('organizer')
            event_org.params['CN'] = [event_obj.organizer]
            event_org.value = 'MAILTO:' + (event_obj.organizer)
        elif event_obj.user_id or event_obj.organizer_id:
            event_org = event.add('organizer')
            organizer = event_obj.organizer_id
            if not organizer:
                organizer = event_obj.user_id
            event_org.params['CN'] = [organizer.name]
            event_org.value = 'MAILTO:' + (organizer.email or organizer.name)

        if event_obj.alarm_id:
            # computes alarm data
            valarm = event.add('valarm')
            alarm_object = self.pool.get('res.alarm')
            alarm_data = alarm_object.read(cr, uid, event_obj.alarm_id.id, context=context)
            # Compute trigger data
            interval = alarm_data['trigger_interval']
            occurs = alarm_data['trigger_occurs']
            duration = (occurs == 'after' and alarm_data['trigger_duration']) \
                                            or -(alarm_data['trigger_duration'])
            related = alarm_data['trigger_related']
            trigger = valarm.add('TRIGGER')
            trigger.params['related'] = [related.upper()]
            if interval == 'days':
                delta = timedelta(days=duration)
            if interval == 'hours':
                delta = timedelta(hours=duration)
            if interval == 'minutes':
                delta = timedelta(minutes=duration)
            trigger.value = delta
            # Compute other details
            valarm.add('DESCRIPTION').value = alarm_data['name'] or 'OpenERP'

        for attendee in event_obj.attendee_ids:
            attendee_add = event.add('attendee')
            attendee_add.params['CUTYPE'] = [str(attendee.cutype)]
            attendee_add.params['ROLE'] = [str(attendee.role)]
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
        company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.name
        for att in self.browse(cr, uid, ids, context=context):
            sign = att.sent_by_uid and att.sent_by_uid.signature or ''
            sign = '<br>'.join(sign and sign.split('\n') or [])
            res_obj = att.ref
            if res_obj:
                att_infos = []
                sub = res_obj.name
                other_invitation_ids = self.search(cr, uid, [('ref', '=', res_obj._name + ',' + str(res_obj.id))])

                for att2 in self.browse(cr, uid, other_invitation_ids):
                    att_infos.append(((att2.user_id and att2.user_id.name) or \
                                 (att2.partner_id and att2.partner_id.name) or \
                                    att2.email) + ' - Status: ' + att2.state.title())
                #dates and times are gonna be expressed in `tz` time (local timezone of the `uid`)
                tz = context.get('tz', pytz.timezone('UTC'))
                #res_obj.date and res_obj.date_deadline are in UTC in database so we use context_timestamp() to transform them in the `tz` timezone
                date_start = fields.datetime.context_timestamp(cr, uid, datetime.strptime(res_obj.date, tools.DEFAULT_SERVER_DATETIME_FORMAT), context=context)
                date_stop = False
                if res_obj.date_deadline:
                    date_stop = fields.datetime.context_timestamp(cr, uid, datetime.strptime(res_obj.date_deadline, tools.DEFAULT_SERVER_DATETIME_FORMAT), context=context)
                body_vals = {'name': res_obj.name,
                            'start_date': date_start,
                            'end_date': date_stop,
                            'timezone': tz,
                            'description': res_obj.description or '-',
                            'location': res_obj.location or '-',
                            'attendees': '<br>'.join(att_infos),
                            'user': res_obj.user_id and res_obj.user_id.name or 'OpenERP User',
                            'sign': sign,
                            'company': company
                }
                body = html_invitation % body_vals
                if mail_to and email_from:
                    ics_file = self.get_ics_file(cr, uid, res_obj, context=context)
                    vals = {'email_from': email_from,
                            'email_to': mail_to,
                            'state': 'outgoing',
                            'subject': sub,
                            'body_html': body,
                            'auto_delete': True}
                    if ics_file:
                        vals['attachment_ids'] = [(0,0,{'name': 'invitation.ics',
                                                        'datas_fname': 'invitation.ics',
                                                        'datas': str(ics_file).encode('base64')})]
                    self.pool.get('mail.mail').create(cr, uid, vals, context=context)
            return True

    def onchange_user_id(self, cr, uid, ids, user_id, *args, **argv):
        """
        Make entry on email and availbility on change of user_id field.
        @param cr: the current row, from the database cursor
        @param uid: the current user's ID for security checks
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
        @param self: the object pointer
        @param cr: the current row, from the database cursor
        @param uid: the current user's ID for security checks
        @param ids: list of calendar attendee's IDs
        @param *args: get Tupple value
        @param context: a standard dictionary for contextual values
        """
        return self.write(cr, uid, ids, {'state': 'tentative'}, context)

    def do_accept(self, cr, uid, ids, context=None, *args):
        """
        Marks event invitation as Accepted.
        @param cr: the current row, from the database cursor
        @param uid: the current user's ID for security checks
        @param ids: list of calendar attendee's IDs
        @param context: a standard dictionary for contextual values
        @return: True
        """
        if context is None:
            context = {}
        return self.write(cr, uid, ids, {'state': 'accepted'}, context)

    def do_decline(self, cr, uid, ids, context=None, *args):
        """
        Marks event invitation as Declined.
        @param self: the object pointer
        @param cr: the current row, from the database cursor
        @param uid: the current user's ID for security checks
        @param ids: list of calendar attendee's IDs
        @param *args: get Tupple value
        @param context: a standard dictionary for contextual values
        """
        if context is None:
            context = {}
        return self.write(cr, uid, ids, {'state': 'declined'}, context)

    def create(self, cr, uid, vals, context=None):
        """
        Overrides orm create method.
        @param self: The object pointer
        @param cr: the current row, from the database cursor
        @param uid: the current user's ID for security checks
        @param vals: get Values
        @param context: a standard dictionary for contextual values
        """
        if context is None:
            context = {}
        if not vals.get("email") and vals.get("cn"):
            cnval = vals.get("cn").split(':')
            email = filter(lambda x:x.__contains__('@'), cnval)
            vals['email'] = email and email[0] or ''
            vals['cn'] = vals.get("cn")
        res = super(calendar_attendee, self).create(cr, uid, vals, context=context)
        return res

calendar_attendee()

class res_alarm(osv.osv):
    """Resource Alarm """
    _name = 'res.alarm'
    _description = 'Basic Alarm Information'

    _columns = {
        'name':fields.char('Name', size=256, required=True),
        'trigger_occurs': fields.selection([('before', 'Before'), \
                                            ('after', 'After')], \
                                        'Triggers', required=True),
        'trigger_interval': fields.selection([('minutes', 'Minutes'), \
                                                ('hours', 'Hours'), \
                                                ('days', 'Days')], 'Interval', \
                                                required=True),
        'trigger_duration': fields.integer('Duration', required=True),
        'trigger_related': fields.selection([('start', 'The event starts'), \
                                            ('end', 'The event ends')], \
                                            'Related to', required=True),
        'duration': fields.integer('Duration', help="""Duration' and 'Repeat' \
are both optional, but if one occurs, so MUST the other"""),
        'repeat': fields.integer('Repeat'),
        'active': fields.boolean('Active', help="If the active field is set to \
false, it will allow you to hide the event alarm information without removing it.")
    }
    _defaults = {
        'trigger_interval': 'minutes',
        'trigger_duration': 5,
        'trigger_occurs': 'before',
        'trigger_related': 'start',
        'active': 1,
    }

    def do_alarm_create(self, cr, uid, ids, model, date, context=None):
        """
        Create Alarm for event.
        @param cr: the current row, from the database cursor,
        @param uid: the current user's ID for security checks,
        @param ids: List of res alarm's IDs.
        @param model: Model name.
        @param date: Event date
        @param context: A standard dictionary for contextual values
        @return: True
        """
        if context is None:
            context = {}
        alarm_obj = self.pool.get('calendar.alarm')
        res_alarm_obj = self.pool.get('res.alarm')
        ir_obj = self.pool.get('ir.model')
        model_id = ir_obj.search(cr, uid, [('model', '=', model)])[0]

        model_obj = self.pool.get(model)
        for data in model_obj.browse(cr, uid, ids, context=context):

            basic_alarm = data.alarm_id
            cal_alarm = data.base_calendar_alarm_id
            if (not basic_alarm and cal_alarm) or (basic_alarm and cal_alarm):
                new_res_alarm = None
                # Find for existing res.alarm
                duration = cal_alarm.trigger_duration
                interval = cal_alarm.trigger_interval
                occurs = cal_alarm.trigger_occurs
                related = cal_alarm.trigger_related
                domain = [('trigger_duration', '=', duration), ('trigger_interval', '=', interval), ('trigger_occurs', '=', occurs), ('trigger_related', '=', related)]
                alarm_ids = res_alarm_obj.search(cr, uid, domain, context=context)
                if not alarm_ids:
                    val = {
                            'trigger_duration': duration,
                            'trigger_interval': interval,
                            'trigger_occurs': occurs,
                            'trigger_related': related,
                            'name': str(duration) + ' ' + str(interval) + ' '  + str(occurs)
                           }
                    new_res_alarm = res_alarm_obj.create(cr, uid, val, context=context)
                else:
                    new_res_alarm = alarm_ids[0]
                cr.execute('UPDATE %s ' % model_obj._table + \
                            ' SET base_calendar_alarm_id=%s, alarm_id=%s ' \
                            ' WHERE id=%s',
                            (cal_alarm.id, new_res_alarm, data.id))

            self.do_alarm_unlink(cr, uid, [data.id], model)
            if basic_alarm:
                vals = {
                    'action': 'display',
                    'description': data.description,
                    'name': data.name,
                    'attendee_ids': [(6, 0, map(lambda x:x.id, data.attendee_ids))],
                    'trigger_related': basic_alarm.trigger_related,
                    'trigger_duration': basic_alarm.trigger_duration,
                    'trigger_occurs': basic_alarm.trigger_occurs,
                    'trigger_interval': basic_alarm.trigger_interval,
                    'duration': basic_alarm.duration,
                    'repeat': basic_alarm.repeat,
                    'state': 'run',
                    'event_date': data[date],
                    'res_id': data.id,
                    'model_id': model_id,
                    'user_id': uid
                 }
                alarm_id = alarm_obj.create(cr, uid, vals)
                cr.execute('UPDATE %s ' % model_obj._table + \
                            ' SET base_calendar_alarm_id=%s, alarm_id=%s '
                            ' WHERE id=%s', \
                            ( alarm_id, basic_alarm.id, data.id) )
        return True

    def do_alarm_unlink(self, cr, uid, ids, model, context=None):
        """
        Delete alarm specified in ids
        @param cr: the current row, from the database cursor,
        @param uid: the current user's ID for security checks,
        @param ids: List of res alarm's IDs.
        @param model: Model name for which alarm is to be cleared.
        @return: True
        """
        if context is None:
            context = {}
        alarm_obj = self.pool.get('calendar.alarm')
        ir_obj = self.pool.get('ir.model')
        model_id = ir_obj.search(cr, uid, [('model', '=', model)])[0]
        model_obj = self.pool.get(model)
        for data in model_obj.browse(cr, uid, ids, context=context):
            alarm_ids = alarm_obj.search(cr, uid, [('model_id', '=', model_id), ('res_id', '=', data.id)])
            if alarm_ids:
                alarm_obj.unlink(cr, uid, alarm_ids)
                cr.execute('Update %s set base_calendar_alarm_id=NULL, alarm_id=NULL\
                            where id=%%s' % model_obj._table,(data.id,))
        return True

res_alarm()

class calendar_alarm(osv.osv):
    _name = 'calendar.alarm'
    _description = 'Event alarm information'
    _inherit = 'res.alarm'
    __attribute__ = {}

    _columns = {
        'alarm_id': fields.many2one('res.alarm', 'Basic Alarm', ondelete='cascade'),
        'name': fields.char('Summary', size=124, help="""Contains the text to be \
                     used as the message subject for email \
                     or contains the text to be used for display"""),
        'action': fields.selection([('audio', 'Audio'), ('display', 'Display'), \
                ('procedure', 'Procedure'), ('email', 'Email') ], 'Action', \
                required=True, help="Defines the action to be invoked when an alarm is triggered"),
        'description': fields.text('Description', help='Provides a more complete \
                            description of the calendar component, than that \
                            provided by the "SUMMARY" property'),
        'attendee_ids': fields.many2many('calendar.attendee', 'alarm_attendee_rel', \
                                      'alarm_id', 'attendee_id', 'Attendees', readonly=True),
        'attach': fields.binary('Attachment', help="""* Points to a sound resource,\
                     which is rendered when the alarm is triggered for audio,
                    * File which is intended to be sent as message attachments for email,
                    * Points to a procedure resource, which is invoked when\
                      the alarm is triggered for procedure."""),
        'res_id': fields.integer('Resource ID'),
        'model_id': fields.many2one('ir.model', 'Model'),
        'user_id': fields.many2one('res.users', 'Owner'),
        'event_date': fields.datetime('Event Date'),
        'event_end_date': fields.datetime('Event End Date'),
        'trigger_date': fields.datetime('Trigger Date', readonly="True"),
        'state':fields.selection([
                    ('draft', 'Draft'),
                    ('run', 'Run'),
                    ('stop', 'Stop'),
                    ('done', 'Done'),
                ], 'Status', select=True, readonly=True),
     }

    _defaults = {
        'action': 'email',
        'state': 'run',
     }

    def create(self, cr, uid, vals, context=None):
        """
        Overrides orm create method.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param vals: dictionary of fields value.{'name_of_the_field': value, ...}
        @param context: A standard dictionary for contextual values
        @return: new record id for calendar_alarm.
        """
        if context is None:
            context = {}
        event_date = vals.get('event_date', False)
        if event_date:
            dtstart = datetime.strptime(vals['event_date'], "%Y-%m-%d %H:%M:%S")
            if vals['trigger_interval'] == 'days':
                delta = timedelta(days=vals['trigger_duration'])
            if vals['trigger_interval'] == 'hours':
                delta = timedelta(hours=vals['trigger_duration'])
            if vals['trigger_interval'] == 'minutes':
                delta = timedelta(minutes=vals['trigger_duration'])
            trigger_date = dtstart + (vals['trigger_occurs'] == 'after' and delta or -delta)
            vals['trigger_date'] = trigger_date
        res = super(calendar_alarm, self).create(cr, uid, vals, context=context)
        return res

    def do_run_scheduler(self, cr, uid, automatic=False, use_new_cursor=False, \
                       context=None):
        """Scheduler for event reminder
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user's ID for security checks,
        @param ids: List of calendar alarm's IDs.
        @param use_new_cursor: False or the dbname
        @param context: A standard dictionary for contextual values
        """
        if context is None:
            context = {}
        current_datetime = datetime.now()
        alarm_ids = self.search(cr, uid, [('state', '!=', 'done')], context=context)

        mail_to = set()
        for alarm in self.browse(cr, uid, alarm_ids, context=context):
            next_trigger_date = None
            update_vals = {}
            model_obj = self.pool.get(alarm.model_id.model)
            res_obj = model_obj.browse(cr, uid, alarm.res_id, context=context)
            re_dates = []

            if hasattr(res_obj, 'rrule') and res_obj.rrule:
                event_date = datetime.strptime(res_obj.date, '%Y-%m-%d %H:%M:%S')
                #exdate is a string and we need a list
                exdate = res_obj.exdate and res_obj.exdate.split(',') or []
                recurrent_dates = get_recurrent_dates(res_obj.rrule, exdate, event_date, res_obj.exrule)

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
                    body = """<pre>
Event: %s
Event Date: %s
Description: %s

From:
      %s

----
%s
</pre>
"""  % (alarm.name, alarm.trigger_date, alarm.description, \
                        alarm.user_id.name, alarm.user_id.signature)
                    mail_to.add(alarm.user_id.email)
                    for att in alarm.attendee_ids:
                        if att.user_id.email:
                            mail_to.add(att.user_id.email)
                    if mail_to:
                        mail_to = ','.join(mail_to)
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

calendar_alarm()


class calendar_event(osv.osv):
    _name = "calendar.event"
    _description = "Calendar Event"
    __attribute__ = {}

    def _tz_get(self, cr, uid, context=None):
        return [(x.lower(), x) for x in pytz.all_timezones]

    def onchange_dates(self, cr, uid, ids, start_date, duration=False, end_date=False, allday=False, context=None):
        """Returns duration and/or end date based on values passed
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user's ID for security checks,
        @param ids: List of calendar event's IDs.
        @param start_date: Starting date
        @param duration: Duration between start date and end date
        @param end_date: Ending Datee
        @param context: A standard dictionary for contextual values
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
            start = start.replace(hour=0, minute=0, second=0)   # change start's time to 00:00:00
            start = start.astimezone(pytz.utc)                  # convert start back to utc
            start_date = start.strftime("%Y-%m-%d %H:%M:%S")
            value['date'] = start_date

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
            cr.execute("select id from %s where recurrent_id=%%s" % (self._table), (event_id,))
            r_ids = map(lambda x: x[0], cr.fetchall())
            self.unlink(cr, uid, r_ids, context=context)
        return True

    def _get_rulestring(self, cr, uid, ids, name, arg, context=None):
        """
        Gets Recurrence rule string according to value type RECUR of iCalendar from the values given.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param id: List of calendar event's ids.
        @param context: A standard dictionary for contextual values
        @return: dictionary of rrule value.
        """

        result = {}
        if not isinstance(ids, list):
            ids = [ids]

        for id in ids:
            #read these fields as SUPERUSER because if the record is private a normal search could return False and raise an error
            data = self.read(cr, SUPERUSER_ID, id, ['interval', 'count'], context=context)
            if data.get('interval', 0) < 0:
                raise osv.except_osv(_('Warning!'), _('Interval cannot be negative.'))
            if data.get('count', 0) <= 0:
                raise osv.except_osv(_('Warning!'), _('Count cannot be negative or 0.'))
            data = self.read(cr, uid, id, ['id','byday','recurrency', 'month_list','end_date', 'rrule_type', 'select1', 'interval', 'count', 'end_type', 'mo', 'tu', 'we', 'th', 'fr', 'sa', 'su', 'exrule', 'day', 'week_list' ], context=context)
            event = data['id']
            if data['recurrency']:
                result[event] = self.compute_rule_string(data)
            else:
                result[event] = ""
        return result

    # hook method to fix the wrong signature
    def _set_rulestring(self, cr, uid, ids, field_name, field_value, args, context=None):
        return self._rrule_write(self, cr, uid, ids, field_name, field_value, args, context=context)

    def _rrule_write(self, obj, cr, uid, ids, field_name, field_value, args, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        data = self._get_empty_rrule_data()
        if field_value:
            data['recurrency'] = True
            for event in self.browse(cr, uid, ids, context=context):
                update_data = self._parse_rrule(field_value, dict(data), event.date)
                data.update(update_data)
                super(calendar_event, self).write(cr, uid, ids, data, context=context)
        return True

    _columns = {
        'id': fields.integer('ID', readonly=True),
        'sequence': fields.integer('Sequence'),
        'name': fields.char('Description', size=64, required=False, states={'done': [('readonly', True)]}),
        'date': fields.datetime('Date', states={'done': [('readonly', True)]}, required=True,),
        'date_deadline': fields.datetime('End Date', states={'done': [('readonly', True)]}, required=True,),
        'create_date': fields.datetime('Created', readonly=True),
        'duration': fields.float('Duration', states={'done': [('readonly', True)]}),
        'description': fields.text('Description', states={'done': [('readonly', True)]}),
        'class': fields.selection([('public', 'Public'), ('private', 'Private'), \
             ('confidential', 'Public for Employees')], 'Privacy', states={'done': [('readonly', True)]}),
        'location': fields.char('Location', size=264, help="Location of Event", states={'done': [('readonly', True)]}),
        'show_as': fields.selection([('free', 'Free'), ('busy', 'Busy')], \
                                                'Show Time as', states={'done': [('readonly', True)]}),
        'base_calendar_url': fields.char('Caldav URL', size=264),
        'state': fields.selection([
            ('tentative', 'Uncertain'),
            ('cancelled', 'Cancelled'),
            ('confirmed', 'Confirmed'),
            ], 'Status', readonly=True),
        'exdate': fields.text('Exception Date/Times', help="This property \
defines the list of date/time exceptions for a recurring calendar component."),
        'exrule': fields.char('Exception Rule', size=352, help="Defines a \
rule or repeating pattern of time to exclude from the recurring rule."),
        'rrule': fields.function(_get_rulestring, type='char', size=124, \
                    fnct_inv=_set_rulestring, store=True, string='Recurrent Rule'),
        'rrule_type': fields.selection([
            ('daily', 'Day(s)'),
            ('weekly', 'Week(s)'),
            ('monthly', 'Month(s)'),
            ('yearly', 'Year(s)')
            ], 'Recurrency', states={'done': [('readonly', True)]},
            help="Let the event automatically repeat at that interval"),
        'alarm_id': fields.many2one('res.alarm', 'Reminder', states={'done': [('readonly', True)]},
                        help="Set an alarm at this time, before the event occurs" ),
        'base_calendar_alarm_id': fields.many2one('calendar.alarm', 'Alarm'),
        'recurrent_id': fields.integer('Recurrent ID'),
        'recurrent_id_date': fields.datetime('Recurrent ID date'),
        'vtimezone': fields.selection(_tz_get, size=64, string='Timezone'),
        'user_id': fields.many2one('res.users', 'Responsible', states={'done': [('readonly', True)]}),
        'organizer': fields.char("Organizer", size=256, states={'done': [('readonly', True)]}), # Map with organizer attribute of VEvent.
        'organizer_id': fields.many2one('res.users', 'Organizer', states={'done': [('readonly', True)]}),
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
        'select1': fields.selection([('date', 'Date of month'),
                                    ('day', 'Day of month')], 'Option'),
        'day': fields.integer('Date of month'),
        'week_list': fields.selection([
            ('MO', 'Monday'),
            ('TU', 'Tuesday'),
            ('WE', 'Wednesday'),
            ('TH', 'Thursday'),
            ('FR', 'Friday'),
            ('SA', 'Saturday'),
            ('SU', 'Sunday')], 'Weekday'),
        'byday': fields.selection([
            ('1', 'First'),
            ('2', 'Second'),
            ('3', 'Third'),
            ('4', 'Fourth'),
            ('5', 'Fifth'),
            ('-1', 'Last')], 'By day'),
        'month_list': fields.selection(months.items(), 'Month'),
        'end_date': fields.date('Repeat Until'),
        'attendee_ids': fields.many2many('calendar.attendee', 'event_attendee_rel', \
                                 'event_id', 'attendee_id', 'Attendees'),
        'allday': fields.boolean('All Day', states={'done': [('readonly', True)]}),
        'active': fields.boolean('Active', help="If the active field is set to \
         false, it will allow you to hide the event alarm information without removing it."),
        'recurrency': fields.boolean('Recurrent', help="Recurrent Meeting"),
        'partner_ids': fields.many2many('res.partner', string='Attendees', states={'done': [('readonly', True)]}),
    }

    def create_attendees(self, cr, uid, ids, context):
        att_obj = self.pool.get('calendar.attendee')
        user_obj = self.pool.get('res.users')
        current_user = user_obj.browse(cr, uid, uid, context=context)
        for event in self.browse(cr, uid, ids, context):
            attendees = {}
            for att in event.attendee_ids:
                attendees[att.partner_id.id] = True
            new_attendees = []
            mail_to = set()
            for partner in event.partner_ids:
                if partner.id in attendees:
                    continue
                local_context = context.copy()
                local_context.pop('default_state', None)
                att_id = self.pool.get('calendar.attendee').create(cr, uid, {
                    'partner_id': partner.id,
                    'user_id': partner.user_ids and partner.user_ids[0].id or False,
                    'ref': self._name+','+str(event.id),
                    'email': partner.email
                }, context=local_context)
                if partner.email:
                    mail_to.add(partner.email)
                self.write(cr, uid, [event.id], {
                    'attendee_ids': [(4, att_id)]
                }, context=context)
                new_attendees.append(att_id)

            if mail_to and current_user.email:
                mail_to = ','.join(mail_to)
                att_obj._send_mail(cr, uid, new_attendees, mail_to,
                    email_from = current_user.email, context=context)
        return True

    def default_organizer(self, cr, uid, context=None):
        user_pool = self.pool.get('res.users')
        user = user_pool.browse(cr, uid, uid, context=context)
        res = user.name
        if user.email:
            res += " <%s>" %(user.email)
        return res

    _defaults = {
            'end_type': 'count',
            'count': 1,
            'rrule_type': False,
            'state': 'tentative',
            'class': 'public',
            'show_as': 'busy',
            'select1': 'date',
            'interval': 1,
            'active': 1,
            'user_id': lambda self, cr, uid, ctx: uid,
            'organizer': default_organizer,
    }

    def _check_closing_date(self, cr, uid, ids, context=None):
        for event in self.browse(cr, uid, ids, context=context):
            if event.date_deadline < event.date:
                return False
        return True

    _constraints = [
        (_check_closing_date, 'Error ! End date cannot be set before start date.', ['date_deadline']),
    ]

    # TODO for trunk: remove get_recurrent_ids
    def get_recurrent_ids(self, cr, uid, select, domain, limit=100, context=None):
        """Wrapper for _get_recurrent_ids to get the 'order' parameter from the context"""
        if not context:
            context = {}
        order = context.get('order', self._order)
        return self._get_recurrent_ids(cr, uid, select, domain, limit=limit, order=order, context=context)

    def _get_recurrent_ids(self, cr, uid, select, domain, limit=100, order=None, context=None):
        """Gives virtual event ids for recurring events based on value of Recurrence Rule
        This method gives ids of dates that comes between start date and end date of calendar views
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user's ID for security checks,
        @param limit: The Number of Results to Return
        @param order: The fields (comma separated, format "FIELD {DESC|ASC}") on which the events should be sorted"""
        if not context:
            context = {}

        result = []
        result_data = []
        fields = ['rrule', 'recurrency', 'exdate', 'exrule', 'date']
        if order:
            order_fields = [field.split()[0] for field in order.split(',')]
        else:
            # fallback on self._order defined on the model
            order_fields = [field.split()[0] for field in self._order.split(',')]
        fields = list(set(fields + order_fields))

        for data in super(calendar_event, self).read(cr, uid, select, fields, context=context):
            if not data['recurrency'] or not data['rrule']:
                result_data.append(data)
                result.append(data['id'])
                continue
            event_date = datetime.strptime(data['date'], "%Y-%m-%d %H:%M:%S")

            # TOCHECK: the start date should be replaced by event date; the event date will be changed by that of calendar code

            exdate = data['exdate'] and data['exdate'].split(',') or []
            rrule_str = data['rrule']
            new_rrule_str = []
            rrule_until_date = False
            is_until = False
            for rule in rrule_str.split(';'):
                name, value = rule.split('=')
                if name == "UNTIL":
                    is_until = True
                    value = parser.parse(value)
                    rrule_until_date = parser.parse(value.strftime("%Y-%m-%d %H:%M:%S"))
                    value = value.strftime("%Y%m%d%H%M%S")
                new_rule = '%s=%s' % (name, value)
                new_rrule_str.append(new_rule)
            new_rrule_str = ';'.join(new_rrule_str)
            rdates = get_recurrent_dates(str(new_rrule_str), exdate, event_date, data['exrule'])
            for r_date in rdates:
                # fix domain evaluation
                # step 1: check date and replace expression by True or False, replace other expressions by True
                # step 2: evaluation of & and |
                # check if there are one False
                pile = []
                for arg in domain:
                    if str(arg[0]) in (str('date'), str('date_deadline')):
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
                idval = real_id2base_calendar_id(data['id'], r_date.strftime("%Y-%m-%d %H:%M:%S"))
                r_data = dict(data, id=idval, date=r_date.strftime("%Y-%m-%d %H:%M:%S"))
                result.append(idval)
                result_data.append(r_data)
        ids = list(set(result))

        if order_fields:

            def comparer(left, right):
                for fn, mult in comparers:
                    if type(fn(left)) == tuple and type(fn(right)) == tuple:
                        # comparing many2one values, sorting on name_get result
                        leftv, rightv = fn(left)[1], fn(right)[1]
                    else:
                        leftv, rightv = fn(left), fn(right)
                    result = cmp(leftv, rightv)
                    if result:
                        return mult * result
                return 0

            sort_params = [key.split()[0] if key[-4:].lower() != 'desc' else '-%s' % key.split()[0] for key in (order or self._order).split(',')]
            comparers = [ ((itemgetter(col[1:]), -1) if col[0] == '-' else (itemgetter(col), 1)) for col in sort_params]    
            ids = [r['id'] for r in sorted(result_data, cmp=comparer)]
            
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
                if byday:
                    return ';BYDAY=' + ','.join(byday)
            return ''

        def get_month_string(freq, data):
            if freq == 'monthly':
                if data.get('select1')=='date' and (data.get('day') < 1 or data.get('day') > 31):
                    raise osv.except_osv(_('Error!'), ("Please select a proper day of the month."))

                if data.get('select1')=='day':
                    return ';BYDAY=' + data.get('byday') + data.get('week_list')
                elif data.get('select1')=='date':
                    return ';BYMONTHDAY=' + str(data.get('day'))
            return ''

        def get_end_date(data):
            if data.get('end_date'):
                data['end_date_new'] = ''.join((re.compile('\d')).findall(data.get('end_date'))) + 'T235959'

            return (data.get('end_type') == 'count' and (';COUNT=' + str(data.get('count'))) or '') +\
                             ((data.get('end_date_new') and data.get('end_type') == 'end_date' and (';UNTIL=' + data.get('end_date_new'))) or '')

        freq = data.get('rrule_type', False)
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
            'select1' : False,
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
            'exrule' : False,
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
            data['byday'] = str(r._bynweekday[0][1])
            data['select1'] = 'day'
            data['rrule_type'] = 'monthly'

        if r._bymonthday:
            data['day'] = r._bymonthday[0]
            data['select1'] = 'date'
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

    def search(self, cr, uid, args, offset=0, limit=0, order=None, context=None, count=False):
        if context is None:
            context = {}
        new_args = []

        for arg in args:
            new_arg = arg
            if arg[0] in ('date_deadline', unicode('date_deadline')):
                if context.get('virtual_id', True):
                    new_args += ['|','&',('recurrency','=',1),('end_date', arg[1], arg[2])]
            elif arg[0] == "id":
                new_id = get_real_ids(arg[2])
                new_arg = (arg[0], arg[1], new_id)
            new_args.append(new_arg)
        if not context.get('virtual_id', True):
            return super(calendar_event, self).search(cr, uid, new_args, offset=offset, limit=limit, order=order, context=context, count=count)

        # offset, limit, order and count must be treated separately as we may need to deal with virtual ids
        res = super(calendar_event, self).search(cr, uid, new_args, offset=0, limit=0, order=None, context=context, count=False)
        res = self._get_recurrent_ids(cr, uid, res, args, limit, order=order, context=context)            

        if count:
            return len(res)
        elif limit:
            return res[offset:offset+limit]
        return res

    def _get_data(self, cr, uid, id, context=None):
        return self.read(cr, uid, id,['date', 'date_deadline'])

    def need_to_update(self, event_id, vals):
        split_id = str(event_id).split("-")
        if len(split_id) < 2:
            return False
        else:
            date_start = vals.get('date', '')
            try:
                date_start = datetime.strptime(date_start, '%Y-%m-%d %H:%M:%S').strftime("%Y%m%d%H%M%S")
                return date_start == split_id[1]
            except Exception:
                return True

    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
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
            if not vals.get('recurrency', True) or _only_changes_to_apply_on_real_ids(vals.keys()):
                ids.append(real_event_id)
                continue

            #if edit one instance of a reccurrent id
            data = self.read(cr, uid, event_id, ['date', 'date_deadline', \
                                                'rrule', 'duration', 'exdate'])
            if data.get('rrule'):
                data.update(
                    vals,
                    recurrent_id=real_event_id,
                    recurrent_id_date=data.get('date'),
                    rrule_type=False,
                    rrule='',
                    recurrency=False,
                )
                #do not copy the id
                if data.get('id'):
                    del(data['id'])
                new_id = self.copy(cr, uid, real_event_id, default=data, context=context)

                date_new = event_id.split('-')[1]
                date_new = time.strftime("%Y%m%dT%H%M%S", \
                             time.strptime(date_new, "%Y%m%d%H%M%S"))
                exdate = (data['exdate'] and (data['exdate'] + ',')  or '') + date_new
                res = self.write(cr, uid, [real_event_id], {'exdate': exdate})

                context.update({'active_id': new_id, 'active_ids': [new_id]})
                continue

        if vals.get('vtimezone', '') and vals.get('vtimezone', '').startswith('/freeassociation.sourceforge.net/tzfile/'):
            vals['vtimezone'] = vals['vtimezone'][40:]

        res = super(calendar_event, self).write(cr, uid, ids, vals, context=context)

        # set end_date for calendar searching
        if vals.get('recurrency', True) and vals.get('end_type', 'count') in ('count', unicode('count')) and \
                (vals.get('rrule_type') or vals.get('count') or vals.get('date') or vals.get('date_deadline')):
            for data in self.read(cr, uid, ids, ['end_date', 'date_deadline', 'recurrency', 'rrule_type', 'count', 'end_type'], context=context):
                end_date = self._set_recurrency_end_date(data, context=context)
                super(calendar_event, self).write(cr, uid, [data['id']], {'end_date': end_date}, context=context)

        if vals.get('partner_ids', False):
            self.create_attendees(cr, uid, ids, context)

        if ('alarm_id' in vals or 'base_calendar_alarm_id' in vals)\
                or ('date' in vals or 'duration' in vals or 'date_deadline' in vals):
            alarm_obj = self.pool.get('res.alarm')
            alarm_obj.do_alarm_create(cr, uid, ids, self._name, 'date', context=context)
        return res or True and False

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
        if not context:
            context = {}

        if 'date' in groupby:
            raise osv.except_osv(_('Warning!'), _('Group by date is not supported, use the calendar view instead.'))
        virtual_id = context.get('virtual_id', True)
        context.update({'virtual_id': False})
        res = super(calendar_event, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby)
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

        EXTRAFIELDS = ('class','user_id','duration')
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

        real_data = super(calendar_event, self).read(cr, uid,
                    [real_id for base_calendar_id, real_id in select],
                    fields=fields2, context=context, load=load)
        real_data = dict(zip([x['id'] for x in real_data], real_data))

        for base_calendar_id, real_id in select:
            res = real_data[real_id].copy()
            ls = base_calendar_id2real_id(base_calendar_id, with_date=res and res.get('duration', 0) or 0)
            if not isinstance(ls, (str, int, long)) and len(ls) >= 2:
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

    def copy(self, cr, uid, id, default=None, context=None):
        if context is None:
            context = {}

        res = super(calendar_event, self).copy(cr, uid, base_calendar_id2real_id(id), default, context)
        alarm_obj = self.pool.get('res.alarm')
        alarm_obj.do_alarm_create(cr, uid, [res], self._name, 'date', context=context)
        return res

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
            self.write(cr, uid, [real_event_id], {'exdate': exdate})
            ids.remove(event_id)
        for event in self.browse(cr, uid, ids, context=context):
            if event.attendee_ids:
                attendee_obj.unlink(cr, uid, [x.id for x in event.attendee_ids], context=context)

        res = super(calendar_event, self).unlink(cr, uid, ids, context=context)
        self.pool.get('res.alarm').do_alarm_unlink(cr, uid, ids, self._name)
        self.unlink_events(cr, uid, ids, context=context)
        return res

    def _set_recurrency_end_date(self, data, context=None):
        if not data.get('recurrency'):
            return False

        end_type = data.get('end_type')
        end_date = data.get('end_date')

        if end_type == 'count' and all(data.get(key) for key in ['count', 'rrule_type', 'date_deadline']):
            count = data['count'] + 1
            delay, mult = {
                'daily': ('days', 1),
                'weekly': ('days', 7),
                'monthly': ('months', 1),
                'yearly': ('years', 1),
            }[data['rrule_type']]

            deadline = datetime.strptime(data['date_deadline'], tools.DEFAULT_SERVER_DATETIME_FORMAT)
            return deadline + relativedelta(**{delay: count * mult})
        return end_date

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}

        if vals.get('vtimezone', '') and vals.get('vtimezone', '').startswith('/freeassociation.sourceforge.net/tzfile/'):
            vals['vtimezone'] = vals['vtimezone'][40:]

        res = super(calendar_event, self).create(cr, uid, vals, context)

        data = self.read(cr, uid, [res], ['end_date', 'date_deadline', 'recurrency', 'rrule_type', 'count', 'end_type'], context=context)[0]
        end_date = self._set_recurrency_end_date(data, context=context)
        self.write(cr, uid, [res], {'end_date': end_date}, context=context)

        alarm_obj = self.pool.get('res.alarm')
        alarm_obj.do_alarm_create(cr, uid, [res], self._name, 'date', context=context)
        self.create_attendees(cr, uid, [res], context)
        return res

    def do_tentative(self, cr, uid, ids, context=None, *args):
        """ Makes event invitation as Tentative
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user's ID for security checks,
        @param ids: List of Event IDs
        @param *args: Get Tupple value
        @param context: A standard dictionary for contextual values
        """
        return self.write(cr, uid, ids, {'state': 'tentative'}, context)

    def do_cancel(self, cr, uid, ids, context=None, *args):
        """ Makes event invitation as Tentative
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user's ID for security checks,
        @param ids: List of Event IDs
        @param *args: Get Tupple value
        @param context: A standard dictionary for contextual values
        """
        return self.write(cr, uid, ids, {'state': 'cancelled'}, context)

    def do_confirm(self, cr, uid, ids, context=None, *args):
        """ Makes event invitation as Tentative
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user's ID for security checks,
        @param ids: List of Event IDs
        @param *args: Get Tupple value
        @param context: A standard dictionary for contextual values
        """
        return self.write(cr, uid, ids, {'state': 'confirmed'}, context)

calendar_event()

class calendar_todo(osv.osv):
    """ Calendar Task """

    _name = "calendar.todo"
    _inherit = "calendar.event"
    _description = "Calendar Task"

    def _get_date(self, cr, uid, ids, name, arg, context=None):
        """
        Get Date
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user's ID for security checks,
        @param ids: List of calendar todo's IDs.
        @param args: list of tuples of form [(‘name_of_the_field', ‘operator', value), ...].
        @param context: A standard dictionary for contextual values
        """

        res = {}
        for event in self.browse(cr, uid, ids, context=context):
            res[event.id] = event.date_start
        return res

    def _set_date(self, cr, uid, id, name, value, arg, context=None):
        """
        Set Date
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user's ID for security checks,
        @param id: calendar's ID.
        @param value: Get Value
        @param args: list of tuples of form [('name_of_the_field', 'operator', value), ...].
        @param context: A standard dictionary for contextual values
        """

        assert name == 'date'
        return self.write(cr, uid, id, { 'date_start': value }, context=context)

    _columns = {
        'date': fields.function(_get_date, fnct_inv=_set_date, \
                            string='Duration', store=True, type='datetime'),
        'duration': fields.integer('Duration'),
    }

    __attribute__ = {}


calendar_todo()


class ir_values(osv.osv):
    _inherit = 'ir.values'

    def set(self, cr, uid, key, key2, name, models, value, replace=True, \
            isobject=False, meta=False, preserve_user=False, company=False):
        """
        Set IR Values
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user's ID for security checks,
        @param model: Get The Model
        """

        new_model = []
        for data in models:
            if type(data) in (list, tuple):
                new_model.append((data[0], base_calendar_id2real_id(data[1])))
            else:
                new_model.append(data)
        return super(ir_values, self).set(cr, uid, key, key2, name, new_model, \
                    value, replace, isobject, meta, preserve_user, company)

    def get(self, cr, uid, key, key2, models, meta=False, context=None, \
             res_id_req=False, without_user=True, key2_req=True):
        """
        Get IR Values
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user's ID for security checks,
        @param model: Get The Model
        """
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

ir_values()

class ir_model(osv.osv):

    _inherit = 'ir.model'

    def read(self, cr, uid, ids, fields=None, context=None,
            load='_classic_read'):
        """
        Overrides orm read method.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user's ID for security checks,
        @param ids: List of IR Model's IDs.
        @param context: A standard dictionary for contextual values
        """
        new_ids = isinstance(ids, (str, int, long)) and [ids] or ids
        if context is None:
            context = {}
        data = super(ir_model, self).read(cr, uid, new_ids, fields=fields, \
                        context=context, load=load)
        if data:
            for val in data:
                val['id'] = base_calendar_id2real_id(val['id'])
        return isinstance(ids, (str, int, long)) and data[0] or data

ir_model()

class virtual_report_spool(web_services.report_spool):

    def exp_report(self, db, uid, object, ids, datas=None, context=None):
        """
        Export Report
        @param self: The object pointer
        @param db: get the current database,
        @param uid: the current user's ID for security checks,
        @param context: A standard dictionary for contextual values
        """

        if object == 'printscreen.list':
            return super(virtual_report_spool, self).exp_report(db, uid, \
                            object, ids, datas, context)
        new_ids = []
        for id in ids:
            new_ids.append(base_calendar_id2real_id(id))
        if datas.get('id', False):
            datas['id'] = base_calendar_id2real_id(datas['id'])
        return super(virtual_report_spool, self).exp_report(db, uid, object, new_ids, datas, context)

virtual_report_spool()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
