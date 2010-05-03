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
from osv import fields, osv
from service import web_services
from tools.translate import _
import pytz
import re
import time
import tools

months = {
    1: "January", 2: "February", 3: "March", 4: "April", \
    5: "May", 6: "June", 7: "July", 8: "August", 9: "September", \
    10: "October", 11: "November", 12: "December"
}

def get_recurrent_dates(rrulestring, exdate, startdate=None, exrule=None):
    """
    Get recurrent dates based on Rule string considering exdate and start date
    @param rrulestring: Rulestring
    @param exdate: List of exception dates for rrule
    @param startdate: Startdate for computing recurrent dates
    @return: List of Recurrent dates
    """
    def todate(date):
        val = parser.parse(''.join((re.compile('\d')).findall(date)))
        return val

    if not startdate:
        startdate = datetime.now()
    rset1 = rrule.rrulestr(rrulestring, dtstart=startdate, forceset=True)

    for date in exdate:
        datetime_obj = todate(date)
        rset1._exdate.append(datetime_obj)
    if exrule:
        rset1.exrule(rrule.rrulestr(str(exrule), dtstart=startdate))
    re_dates = map(lambda x:x.strftime('%Y-%m-%d %H:%M:%S'), rset1._iter())
    return re_dates

def base_calendar_id2real_id(base_calendar_id=None, with_date=False):
    """
    This function converts virtual event id into real id of actual event
    @param base_calendar_id: Id of calendar
    @param with_date: If value passed to this param it will return dates based on value of withdate + base_calendar_id
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

def real_id2base_calendar_id(real_id, recurrent_date):
    """
    Convert  real id of record into virtual id using recurrent_date
    e.g. real id is 1 and recurrent_date is 01-12-2009 10:00:00 then it will return
        1-20091201100000
    @return: real id with recurrent date.
    """

    if real_id and recurrent_date:
        recurrent_date = time.strftime("%Y%m%d%H%M%S", \
                            time.strptime(recurrent_date, "%Y-%m-%d %H:%M:%S"))
        return '%d-%s' % (real_id, recurrent_date)
    return real_id

def _links_get(self, cr, uid, context={}):
    """
    Get request link.
    @param cr: the current row, from the database cursor,
    @param uid: the current user’s ID for security checks,
    @param context: A standard dictionary for contextual values
    @return: list of dictionary which contain object and name and id.
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
        <td width="100%%">Below are the details of event:</td>
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
            <tr valign="top">
                <td><b>Are you coming?</b></td>
                <td><b>:</b></td>
                <td colspan="3">
                <UL>
                    <LI>YES</LI>
                    <LI>NO</LI>
                    <LI>MAYBE</LI>
                </UL>
                </td>
            </tr>
        </table>
        </td>
    </tr>
</table>
<table border="0" cellspacing="10" cellpadding="0" width="100%%"
    style="font-family: Arial, Sans-serif; font-size: 14">
    <tr>
        <td width="100%%"><b>Note:</b> If you are interested please reply this
        mail and keep only your response from options <i>YES, NO</i>
        and <i>MAYBE</i>.</td>
    </tr>
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
        Get Email Address
        """
        if name and email:
            name += ':'
        return (name or '') + (email and ('MAILTO:' + email) or '')

    def _compute_data(self, cr, uid, ids, name, arg, context):
        """
        Compute data on field.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of calendar attendee’s IDs.
        @param name: name of field.
        @param context: A standard dictionary for contextual values
        @return: Dictionary of form {id: {'field Name': value'}}.
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
                                        attdata.sent_by_uid.address_id.email)
            if name == 'cn':
                if attdata.user_id:
                    result[id][name] = self._get_address(attdata.user_id.name, attdata.email)
                elif attdata.partner_address_id:
                    result[id][name] = self._get_address(attdata.partner_id.name, attdata.email)
                else:
                    result[id][name] = self._get_address(None, attdata.email)
            if name == 'delegated_to':
                todata = []
                for parent in attdata.parent_ids:
                    if parent.email:
                        todata.append('MAILTO:' + parent.email)
                result[id][name] = ', '.join(todata)
            if name == 'delegated_from':
                fromdata = []
                for child in attdata.child_ids:
                    if child.email:
                        fromdata.append('MAILTO:' + child.email)
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
                lang = user_obj.read(cr, uid, uid, ['context_lang'], context=context)['context_lang']
                result[id][name] = lang.replace('_', '-')
        return result

    def _links_get(self, cr, uid, context={}):
        """
        Get request link for ref field in calendar attendee.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        @return: list of dictionary which contain object and name and id.
        """

        obj = self.pool.get('res.request.link')
        ids = obj.search(cr, uid, [])
        res = obj.read(cr, uid, ids, ['object', 'name'], context=context)
        return [(r['object'], r['name']) for r in res]

    def _lang_get(self, cr, uid, context={}):
        """
        Get language for language function field.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        @return: list of dictionary which contain code and name and id.
        """
        obj = self.pool.get('res.lang')
        ids = obj.search(cr, uid, [])
        res = obj.read(cr, uid, ids, ['code', 'name'], context=context)
        res = [((r['code']).replace('_', '-'), r['name']) for r in res]
        return res

    _columns = {
        'cutype': fields.selection([('individual', 'Individual'), \
                    ('group', 'Group'), ('resource', 'Resource'), \
                    ('room', 'Room'), ('unknown', '') ], \
                    'Invite Type', help="Specify the type of Invitation"),
        'member': fields.char('Member', size=124,
                    help="Indicate the groups that the attendee belongs to"),
        'role': fields.selection([('req-participant', 'Participation required'), \
                    ('chair', 'Chair Person'), \
                    ('opt-participant', 'Optional Participation'), \
                    ('non-participant', 'For information Purpose')], 'Role', \
                    help='Participation role for the calendar user'),
        'state': fields.selection([('tentative', 'Tentative'),
                        ('needs-action', 'Needs Action'),
                        ('accepted', 'Accepted'),
                        ('declined', 'Declined'),
                        ('delegated', 'Delegated')], 'State', readonly=True, \
                        help="Status of the attendee's participation"),
        'rsvp':  fields.boolean('Required Reply?',
                    help="Indicats whether the favor of a reply is requested"),
        'delegated_to': fields.function(_compute_data, method=True, \
                string='Delegated To', type="char", size=124, store=True, \
                multi='delegated_to', help="The users that the original \
request was delegated to"),
        'delegated_from': fields.function(_compute_data, method=True, string=\
            'Delegated From', type="char", store=True, size=124, multi='delegated_from'),
        'parent_ids': fields.many2many('calendar.attendee', 'calendar_attendee_parent_rel', \
                                    'attendee_id', 'parent_id', 'Delegrated From'),
        'child_ids': fields.many2many('calendar.attendee', 'calendar_attendee_child_rel', \
                                      'attendee_id', 'child_id', 'Delegrated To'),
        'sent_by': fields.function(_compute_data, method=True, string='Sent By', \
                        type="char", multi='sent_by', store=True, size=124, \
                        help="Specify the user that is acting on behalf of the calendar user"),
        'sent_by_uid': fields.function(_compute_data, method=True, string='Sent By User', \
                            type="many2one", relation="res.users", multi='sent_by_uid'),
        'cn': fields.function(_compute_data, method=True, string='Common name', \
                            type="char", size=124, multi='cn', store=True),
        'dir': fields.char('URI Reference', size=124, help="Reference to the URI\
that points to the directory information corresponding to the attendee."),
        'language': fields.function(_compute_data, method=True, string='Language', \
                    type="selection", selection=_lang_get, multi='language', \
                    store=True, help="To specify the language for text values in a\
property or property parameter."),
        'user_id': fields.many2one('res.users', 'User'),
        'partner_address_id': fields.many2one('res.partner.address', 'Contact'),
        'partner_id': fields.related('partner_address_id', 'partner_id', type='many2one', \
                        relation='res.partner', string='Partner', help="Partner related to contact"),
        'email': fields.char('Email', size=124, help="Email of Invited Person"),
        'event_date': fields.function(_compute_data, method=True, string='Event Date', \
                            type="datetime", multi='event_date'),
        'event_end_date': fields.function(_compute_data, method=True, \
                            string='Event End Date', type="datetime", \
                            multi='event_end_date'),
        'ref': fields.reference('Event Ref', selection=_links_get, size=128),
        'availability': fields.selection([('free', 'Free'), ('busy', 'Busy')], 'Free/Busy', readonly="True"),
     }
    _defaults = {
        'state': lambda *x: 'needs-action',
    }

    response_re = re.compile("Are you coming\?.*\n*.*(YES|NO|MAYBE).*", re.UNICODE)

    def msg_new(self, cr, uid, msg):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        """
        return False

    def msg_act_get(self, msg):
        """
        Get Message.
        @param self: The object pointer
        @return: dictionary of actions which contain state field value.
        """

        mailgate_obj = self.pool.get('mail.gateway')
        body = mailgate_obj.msg_body_get(msg)
        actions = {}
        res = self.response_re.findall(body['body'])
        if res:
            actions['state'] = res[0]
        return actions

    def msg_update(self, cr, uid, ids, msg, data={}, default_act='None'):
        """
        Update msg state which may be accepted.declined.tentative.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of calendar attendee’s IDs.
        @param context: A standard dictionary for contextual values
        @return: True
        """
        msg_actions = self.msg_act_get(msg)
        if msg_actions.get('state'):
            if msg_actions['state'] in ['YES', 'NO', 'MAYBE']:
                mapping = {'YES': 'accepted', 'NO': 'declined', 'MAYBE': 'tentative'}
                status = mapping[msg_actions['state']]
                print 'Got response for invitation id: %s as %s' % (ids, status)
                self.write(cr, uid, ids, {'state': status})
        return True

    def get_ics_file(self, cr, uid, event_obj, context=None):
        """
        Returns iCalendar file for the event invitation
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param event_obj: Event object (browse record)
        @param context: A standard dictionary for contextual values
        @return: .ics file content
        """
        res = None
        def ics_datetime(idate, short=False):
            if short:
                return date.fromtimestamp(time.mktime(time.strptime(idate, '%Y-%m-%d')))
            else:
                return datetime.strptime(idate, '%Y-%m-%d %H:%M:%S')
        try:
            import vobject
        except ImportError:
            return res
        cal = vobject.iCalendar()
        event = cal.add('vevent')
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
            attendee_add.value = 'MAILTO:' + attendee.email
        res = cal.serialize()
        return res
    
    def _send_mail(self, cr, uid, ids, mail_to, email_from=tools.config.get('email_from', False), context={}):
        """
        Send mail for calendar attendee.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of calendar attendee’s IDs.
        @param context: A standard dictionary for contextual values
        @return: True
        """

        company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.name
        for att in self.browse(cr, uid, ids, context=context):
            sign = att.sent_by_uid and att.sent_by_uid.signature or ''
            sign = '<br>'.join(sign and sign.split('\n') or [])
            res_obj = att.ref
            sub = '[%s Invitation][%d] %s' % (company, att.id, res_obj.name)
            att_infos = []
            other_invitaion_ids = self.search(cr, uid, [('ref', '=', res_obj._name + ',' + str(res_obj.id))])
            for att2 in self.browse(cr, uid, other_invitaion_ids):
                att_infos.append(((att2.user_id and att2.user_id.name) or \
                             (att2.partner_id and att2.partner_id.name) or \
                                att2.email) + ' - Status: ' + att2.state.title())
            body_vals = {'name': res_obj.name,
                        'start_date': res_obj.date,
                        'end_date': res_obj.date_deadline or False,
                        'description': res_obj.description or '-',
                        'location': res_obj.location or '-',
                        'attendees': '<br>'.join(att_infos),
                        'user': res_obj.user_id and res_obj.user_id.name or 'OpenERP User',
                        'sign': sign,
                        'company': company
            }
            body = html_invitation % body_vals
            attach = self.get_ics_file(cr, uid, res_obj, context=context)
            if mail_to and email_from:
                tools.email_send(
                    email_from,
                    mail_to,
                    sub,
                    body,
                    attach=attach and [('invitation.ics', attach)] or None,
                    subtype='html',
                    reply_to=email_from
                )
            return True

    def onchange_user_id(self, cr, uid, ids, user_id, *args, **argv):
        """
        Make entry on email and availbility on change of user_id field.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of calendar attendee’s IDs.
        @param user_id: User id
        @return: dictionary of value. which put value in email and availability fields.
        """

        if not user_id:
            return {'value': {'email': ''}}
        usr_obj = self.pool.get('res.users')
        user = usr_obj.browse(cr, uid, user_id, *args)
        return {'value': {'email': user.address_id.email, 'availability':user.availability}}

    def do_tentative(self, cr, uid, ids, context=None, *args):
        """ @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of calendar attendee’s IDs
            @param *args: Get Tupple value
            @param context: A standard dictionary for contextual values """

        self.write(cr, uid, ids, {'state': 'tentative'}, context)

    def do_accept(self, cr, uid, ids, context=None, *args):
        """
        Update state which value is accepted.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of calendar attendee’s IDs.
        @return: True
        """

        if not context:
            context = {}

        for vals in self.browse(cr, uid, ids, context=context):
            user = vals.user_id
            if user:
                mod_obj = self.pool.get(vals.ref._name)
                if vals.ref:
                    if vals.ref.user_id.id != user.id:
                        defaults = {'user_id': user.id}
                        new_event = mod_obj.copy(cr, uid, vals.ref.id, default=defaults, context=context)
            self.write(cr, uid, vals.id, {'state': 'accepted'}, context)

        return True

    def do_decline(self, cr, uid, ids, context=None, *args):
        """ @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of calendar attendee’s IDs
            @param *args: Get Tupple value
            @param context: A standard dictionary for contextual values """

        self.write(cr, uid, ids, {'state': 'declined'}, context)

    def create(self, cr, uid, vals, context=None):
        """ @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param vals: Get Values
            @param context: A standard dictionary for contextual values """

        if not context:
            context = {}
        if not vals.get("email") and vals.get("cn"):
            cnval = vals.get("cn").split(':')
            email = filter(lambda x:x.__contains__('@'), cnval)
            vals['email'] = email[0]
            vals['cn'] = vals.get("cn")
        res = super(calendar_attendee, self).create(cr, uid, vals, context)
        return res

calendar_attendee()

class res_alarm(osv.osv):
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
                    true, it will allow you to hide the event alarm information without removing it.")
    }
    _defaults = {
        'trigger_interval': lambda *x: 'minutes',
        'trigger_duration': lambda *x: 5,
        'trigger_occurs': lambda *x: 'before',
        'trigger_related': lambda *x: 'start',
        'active': lambda *x: 1,
    }

    def do_alarm_create(self, cr, uid, ids, model, date, context={}):
        """
        Create Alarm for meeting.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of res alarm’s IDs.
        @param model: Model name.
        @param context: A standard dictionary for contextual values
        @return: True
        """

        alarm_obj = self.pool.get('calendar.alarm')
        ir_obj = self.pool.get('ir.model')
        model_id = ir_obj.search(cr, uid, [('model', '=', model)])[0]

        model_obj = self.pool.get(model)
        for data in model_obj.browse(cr, uid, ids, context):

            basic_alarm = data.alarm_id
            if not context.get('alarm_id', False):
                self.do_alarm_unlink(cr, uid, [data.id], model)
                return True
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
                cr.execute('Update %s set base_calendar_alarm_id=%s, alarm_id=%s \
                                        where id=%s' % (model_obj._table, \
                                        alarm_id, basic_alarm.id, data.id))
        cr.commit()
        return True

    def do_alarm_unlink(self, cr, uid, ids, model, context={}):
        """
        Delete alarm specified in ids
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of res alarm’s IDs.
        @param model: Model name.
        @return: True
        """

        alarm_obj = self.pool.get('calendar.alarm')
        ir_obj = self.pool.get('ir.model')
        model_id = ir_obj.search(cr, uid, [('model', '=', model)])[0]
        model_obj = self.pool.get(model)
        for datas in model_obj.browse(cr, uid, ids, context):
            alarm_ids = alarm_obj.search(cr, uid, [('model_id', '=', model_id), ('res_id', '=', datas.id)])
            if alarm_ids:
                alarm_obj.unlink(cr, uid, alarm_ids)
                cr.execute('Update %s set base_calendar_alarm_id=NULL, alarm_id=NULL\
                            where id=%s' % (model_obj._table, datas.id))
        cr.commit()
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
                ], 'State', select=True, readonly=True),
     }

    _defaults = {
        'action': lambda *x: 'email',
        'state': lambda *x: 'run',
     }
    def create(self, cr, uid, vals, context={}):
        """
        create new record.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param vals: dictionary of fields value.{‘name_of_the_field’: value, ...}
        @param context: A standard dictionary for contextual values
        @return: new record id for calendar_alarm.
        """

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
        res = super(calendar_alarm, self).create(cr, uid, vals, context)
        return res

    def do_run_scheduler(self, cr, uid, automatic=False, use_new_cursor=False, \
                       context=None):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of calendar alarm’s IDs.
        @param use_new_cursor: False or the dbname
        @param context: A standard dictionary for contextual values
        """

        if not context:
            context = {}
        current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cr.execute("select alarm.id as id \
                    from calendar_alarm alarm \
                    where alarm.state = %s and alarm.trigger_date <= %s", ('run', current_datetime))
        res = cr.dictfetchall()
        alarm_ids = map(lambda x: x['id'], res)
        #attendee_obj = self.pool.get('calendar.attendee')
        request_obj = self.pool.get('res.request')
        mail_to = []
        for alarm in self.browse(cr, uid, alarm_ids):
            if alarm.action == 'display':
                value = {
                   'name': alarm.name,
                   'act_from': alarm.user_id.id,
                   'act_to': alarm.user_id.id,
                   'body': alarm.description,
                   'trigger_date': alarm.trigger_date,
                   'ref_doc1': '%s,%s' % (alarm.model_id.model, alarm.res_id)
                }
                request_id = request_obj.create(cr, uid, value)
                request_ids = [request_id]
                for attendee in alarm.attendee_ids:
                    if attendee.user_id:
                        value['act_to'] = attendee.user_id.id
                        request_id = request_obj.create(cr, uid, value)
                        request_ids.append(request_id)
                request_obj.request_send(cr, uid, request_ids)

            if alarm.action == 'email':
                sub = '[Openobject Remainder] %s' % (alarm.name)
                body = """
                Name: %s
                Date: %s
                Description: %s

                From:
                      %s
                      %s

                """  % (alarm.name, alarm.trigger_date, alarm.description, \
                    alarm.user_id.name, alarm.user_id.signature)
                mail_to = [alarm.user_id.address_id.email]
                for att in alarm.attendee_ids:
                    mail_to.append(att.user_id.address_id.email)
                if mail_to:
                    tools.email_send(
                        tools.config.get('email_from', False),
                        mail_to,
                        sub,
                        body
                    )
            self.write(cr, uid, [alarm.id], {'state':'done'})
        return True

calendar_alarm()


class calendar_event(osv.osv):
    _name = "calendar.event"
    _description = "Calendar Event"
    __attribute__ = {}

    def _tz_get(self, cr, uid, context={}):
        return [(x.lower(), x) for x in pytz.all_timezones]

    def onchange_allday(self, cr, uid, ids, allday, context={}):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of calendar event’s IDs.
        @param allday: Value of allday boolean
        @param context: A standard dictionary for contextual values
        """
        if not allday or not ids:
            return {}
        event = self.browse(cr, uid, ids, context=context)[0]
        value = {
                 'date': event.date and event.date[:11] + '00:00:00',
                 'date_deadline': event.date_deadline and event.date_deadline[:11] + '00:00:00',
                 'duration': 24
                 }
        return {'value': value}

    def onchange_dates(self, cr, uid, ids, start_date, duration=False, end_date=False, allday=False, context={}):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of calendar event’s IDs.
        @param start_date: Get starting date
        @param duration: Get Duration between start date and end date or False
        @param end_date: Get Ending Date or False
        @param context: A standard dictionary for contextual values
        """
        value = {}
        if not start_date:
            return value
        if not end_date and not duration:
            duration = 8.00
            value['duration'] = duration

        if allday: # For all day event
            start = start_date[:11] + '00:00:00'
            value = {
                 'date': start,
                 'date_deadline': start,
                 'duration': 24
                 }
            return {'value': value}

        start = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        if end_date and not duration:
            end = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
            diff = end - start
            duration = float(diff.days)* 24 + (float(diff.seconds) / 3600)
            value['duration'] = round(duration, 2)
        elif not end_date:
            end = start + timedelta(hours=duration)
            value['date_deadline'] = end.strftime("%Y-%m-%d %H:%M:%S")

        return {'value': value}

    def _set_rrulestring(self, cr, uid, id, name, value, arg, context):
        """
        Set rule string.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param id: List of calendar event's ids.
        @param context: A standard dictionary for contextual values
        @return: dictionary of rrule value.
        """
        cr.execute("UPDATE %s set freq='None',interval=0,count=0,end_date=Null,\
                    mo=False,tu=False,we=False,th=False,fr=False,sa=False,su=False,\
                    day=0,select1='date',month_list=Null ,byday=Null where id=%s" % (self._table, id))

        if not value:
            cr.execute("UPDATE %s set rrule_type='none' where id=%s" % (self._table, id))
            return True
        val = {}
        for part in value.split(';'):
            if part.lower().__contains__('freq') and len(value.split(';')) <=2:
                rrule_type = part.lower()[5:]
                break
            else:
                rrule_type = 'custom'
                break
        ans = value.split(';')
        for i in ans:
            val[i.split('=')[0].lower()] = i.split('=')[1].lower()
        if not val.get('interval'):
            rrule_type = 'custom'
        elif int(val.get('interval')) > 1: #If interval is other than 1 rule is custom
            rrule_type = 'custom'

        qry = "UPDATE %(table)s set rrule_type=\'%(rule_type)s\' "

        if rrule_type == 'custom':
            new_val = val.copy()
            for k, v in val.items():
                if  val['freq'] == 'weekly' and val.get('byday'):
                    for day in val['byday'].split(','):
                        new_val[day] = True
                    val.pop('byday')

                if val.get('until'):
                    until = parser.parse(''.join((re.compile('\d')).findall(val.get('until'))))
                    new_val['end_date'] = until.strftime('%Y-%m-%d')
                    val.pop('until')
                    new_val.pop('until')

                if val.get('bymonthday'):
                    new_val['day'] = val.get('bymonthday')
                    val.pop('bymonthday')
                    new_val['select1'] = 'date'
                    new_val.pop('bymonthday')

                if val.get('byday'):
                    d = val.get('byday')
                    if '-' in d:
                        new_val['byday'] = d[:2]
                        new_val['week_list'] = d[2:4].upper()
                    else:
                        new_val['byday'] = d[:1]
                        new_val['week_list'] = d[1:3].upper()
                    new_val['select1'] = 'day'

                if val.get('bymonth'):
                    new_val['month_list'] = val.get('bymonth')
                    val.pop('bymonth')
                    new_val.pop('bymonth')

            for k, v in new_val.items():
                temp = ", %s='%s'" % (k, v)
                qry += temp

        whr = " where id=%(id)s"
        qry = qry + whr
        val.update({
            'table': self._table,
            'rule_type': rrule_type,
            'id': id,
        })
        cr.execute(qry % val)
        return True

    def _get_rulestring(self, cr, uid, ids, name, arg, context=None):
        """
        Get rule string.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param id: List of calendar event's ids.
        @param context: A standard dictionary for contextual values
        @return: dictionary of rrule value.
        """
        result = {}
        for datas in self.read(cr, uid, ids, context=context):
            event = datas['id']
            if datas.get('rrule_type'):
                if datas.get('rrule_type') == 'none':
                    result[event] = False
                elif datas.get('rrule_type') == 'custom':
                    if datas.get('interval', 0) < 0:
                        raise osv.except_osv('Warning!', 'Interval can not be Negative')
                    if datas.get('count', 0) < 0:
                        raise osv.except_osv('Warning!', 'Count can not be Negative')
                    rrule_custom = self.compute_rule_string(cr, uid, datas, \
                                                         context=context)
                    result[event] = rrule_custom
                else:
                    result[event] = self.compute_rule_string(cr, uid, {'freq': datas.get('rrule_type').upper(), 'interval': 1}, context=context)

        return result

    _columns = {
        'id': fields.integer('ID'),
        'sequence': fields.integer('Sequence'),
        'name': fields.char('Description', size=64, required=True),
        'date': fields.datetime('Date'),
        'date_deadline': fields.datetime('Deadline'),
        'create_date': fields.datetime('Created', readonly=True),
        'duration': fields.float('Duration'),
        'description': fields.text('Your action'),
        'class': fields.selection([('public', 'Public'), ('private', 'Private'), \
             ('confidential', 'Confidential')], 'Mark as'),
        'location': fields.char('Location', size=264, help="Location of Event"),
        'show_as': fields.selection([('free', 'Free'), ('busy', 'Busy')], \
                                                'Show as'),
        'base_calendar_url': fields.char('Caldav URL', size=264),
        'exdate': fields.text('Exception Date/Times', help="This property \
                    defines the list of date/time exceptions for arecurring calendar component."),
        'exrule': fields.char('Exception Rule', size=352, help="defines a \
                    rule or repeating pattern for anexception to a recurrence set"),
        'rrule': fields.function(_get_rulestring, type='char', size=124, method=True, \
                                    string='Recurrent Rule', store=True, \
                                    fnct_inv=_set_rrulestring, help='Defines a\
 rule or repeating pattern for recurring events\n\
e.g.: Every other month on the last Sunday of the month for 10 occurrences:\
        FREQ=MONTHLY;INTERVAL=2;COUNT=10;BYDAY=-1SU'),
        'rrule_type': fields.selection([('none', ''), ('daily', 'Daily'), \
                            ('weekly', 'Weekly'), ('monthly', 'Monthly'), \
                            ('yearly', 'Yearly'), ('custom', 'Custom')], 'Recurrency'),
        'alarm_id': fields.many2one('res.alarm', 'Alarm'),
        'base_calendar_alarm_id': fields.many2one('calendar.alarm', 'Alarm'),
        'recurrent_uid': fields.integer('Recurrent ID'),
        'recurrent_id': fields.datetime('Recurrent ID date'),
        'vtimezone': fields.related('user_id', 'context_tz', type='char', size=24, \
                         string='Timezone', store=True),
        'user_id': fields.many2one('res.users', 'Responsible'),
        'freq': fields.selection([('None', 'No Repeat'), \
                                ('secondly', 'Secondly'), \
                                ('minutely', 'Minutely'), \
                                ('hourly', 'Hourly'), \
                                ('daily', 'Daily'), \
                                ('weekly', 'Weekly'), \
                                ('monthly', 'Monthly'), \
                                ('yearly', 'Yearly')], 'Frequency'),
        'interval': fields.integer('Interval'),
        'count': fields.integer('Count'),
        'mo': fields.boolean('Mon'),
        'tu': fields.boolean('Tue'),
        'we': fields.boolean('Wed'),
        'th': fields.boolean('Thu'),
        'fr': fields.boolean('Fri'),
        'sa': fields.boolean('Sat'),
        'su': fields.boolean('Sun'),
        'select1': fields.selection([('date', 'Date of month'), \
                                    ('day', 'Day of month')], 'Option'),
        'day': fields.integer('Date of month'),
        'week_list': fields.selection([('MO', 'Monday'), ('TU', 'Tuesday'), \
                                   ('WE', 'Wednesday'), ('TH', 'Thursday'), \
                                   ('FR', 'Friday'), ('SA', 'Saturday'), \
                                   ('SU', 'Sunday')], 'Weekday'),
        'byday': fields.selection([('1', 'First'), ('2', 'Second'), \
                                   ('3', 'Third'), ('4', 'Fourth'), \
                                   ('5', 'Fifth'), ('-1', 'Last')], 'By day'),
        'month_list': fields.selection(months.items(), 'Month'),
        'end_date': fields.date('Repeat Until'),
        'attendee_ids': fields.many2many('calendar.attendee', 'event_attendee_rel', \
                                 'event_id', 'attendee_id', 'Attendees'),
        'allday': fields.boolean('All Day')
    }

    _defaults = {
         'class': lambda *a: 'public',
         'show_as': lambda *a: 'busy',
         'freq': lambda *x: 'None',
         'select1': lambda *x: 'date',
         'interval': lambda *x: 1,
    }

    def open_event(self, cr, uid, ids, context=None):
        """
        Open Event From for Editing
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of event’s IDs
        @param context: A standard dictionary for contextual values
        @return: Dictionary value which open Crm Meeting form.
        """
        if not context:
            context = {}

        data_obj = self.pool.get('ir.model.data')

        value = {}

        id2 = data_obj._get_id(cr, uid, 'base_calendar', 'event_form_view')
        id3 = data_obj._get_id(cr, uid, 'base_calendar', 'event_tree_view')
        id4 = data_obj._get_id(cr, uid, 'base_calendar', 'event_calendar_view')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        if id3:
            id3 = data_obj.browse(cr, uid, id3, context=context).res_id
        if id4:
            id4 = data_obj.browse(cr, uid, id4, context=context).res_id
        for id in ids:
            value = {
                    'name': _('Event'),
                    'view_type': 'form',
                    'view_mode': 'form,tree',
                    'res_model': 'calendar.event',
                    'view_id': False,
                    'views': [(id2, 'form'), (id3, 'tree'), (id4, 'calendar')],
                    'type': 'ir.actions.act_window',
                    'res_id': base_calendar_id2real_id(id),
                    'nodestroy': True
                    }

        return value

    def modify_this(self, cr, uid, event_id, defaults, real_date, context=None, *args):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param event_id: Get Event_id
        @param real_date: Get Real Date
        @param context: A standard dictionary for contextual values
        @param *args: Get Tuppel Value

        """

        event_id = base_calendar_id2real_id(event_id)
        datas = self.read(cr, uid, event_id, context=context)
        defaults.update({
                        'recurrent_uid': base_calendar_id2real_id(datas['id']),
                        'recurrent_id': defaults.get('date') or real_date,
                        'rrule_type': 'none',
                        'rrule': ''
                        })
        exdate = datas['exdate'] and datas['exdate'].split(',') or []
        if real_date and defaults.get('date'):
            exdate.append(real_date)
        self.write(cr, uid, event_id, {'exdate': ','.join(exdate)}, context=context)
        new_id = self.copy(cr, uid, event_id, default=defaults, context=context)
        return new_id

    def modify_all(self, cr, uid, event_ids, defaults, context=None, *args):
        """
        Modify name, date, date_deadline fields.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param event_ids: List of crm meeting’s IDs.
        @return: True
        """

        for event_id in event_ids:
            event_id = base_calendar_id2real_id(event_id)

            defaults.pop('id')
            defaults.update({'table': self._table})

            qry = "UPDATE %(table)s set name = '%(name)s', \
                            date = '%(date)s', date_deadline = '%(date_deadline)s'"
            if defaults.get('alarm_id'):
                qry += ", alarm_id = %(alarm_id)s"
            if defaults.get('location'):
                qry += ", location = '%(location)s'"
            qry += "WHERE id = %s" % (event_id)
            cr.execute(qry %(defaults))

        return True

    def get_recurrent_ids(self, cr, uid, select, base_start_date, base_until_date, limit=100):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param base_start_date: Get Start Date
        @param base_until_date: Get End Date
        @param limit: The Number of Results to Return """

        if not limit:
            limit = 100
        if isinstance(select, (str, int, long)):
            ids = [select]
        else:
            ids = select
        result = []
        if ids and (base_start_date or base_until_date):
            cr.execute("select m.id, m.rrule, m.date, m.date_deadline, \
                            m.exdate, m.exrule from " + self._table + \
                            " m where m.id in ("\
                            + ','.join(map(lambda x: str(x), ids))+")")

            count = 0
            for data in cr.dictfetchall():
                start_date = base_start_date and datetime.strptime(base_start_date[:10], "%Y-%m-%d") or False
                until_date = base_until_date and datetime.strptime(base_until_date[:10], "%Y-%m-%d") or False
                if count > limit:
                    break
                event_date = datetime.strptime(data['date'], "%Y-%m-%d %H:%M:%S")
#                To check: If the start date is replace by event date .. the event date will be changed by that of calendar code
#                if start_date and start_date <= event_date:
#                        start_date = event_date
                start_date = event_date
                if not data['rrule']:
                    if start_date and (event_date < start_date):
                        continue
                    if until_date and (event_date > until_date):
                        continue
                    idval = real_id2base_calendar_id(data['id'], data['date'])
                    result.append(idval)
                    count += 1
                else:
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
                            rrule_until_date = parser.parse(value.strftime("%Y-%m-%d"))
                            if until_date and until_date >= rrule_until_date:
                                until_date = rrule_until_date
                            if until_date:
                                value = until_date.strftime("%Y%m%d%H%M%S")
                        new_rule = '%s=%s' % (name, value)
                        new_rrule_str.append(new_rule)
                    if not is_until and until_date:
                        value = until_date.strftime("%Y%m%d%H%M%S")
                        name = "UNTIL"
                        new_rule = '%s=%s' % (name, value)
                        new_rrule_str.append(new_rule)
                    new_rrule_str = ';'.join(new_rrule_str)
                    rdates = get_recurrent_dates(str(new_rrule_str), exdate, start_date, data['exrule'])
                    for rdate in rdates:
                        r_date = datetime.strptime(rdate, "%Y-%m-%d %H:%M:%S")
                        if start_date and r_date < start_date:
                            continue
                        if until_date and r_date > until_date:
                            continue
                        idval = real_id2base_calendar_id(data['id'], rdate)
                        result.append(idval)
                        count += 1
        if result:
            ids = result
        if isinstance(select, (str, int, long)):
            return ids and ids[0] or False
        return ids

    def compute_rule_string(self, cr, uid, datas, context=None, *args):
        """
        Compute rule string.
        @param self: the object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param datas: dictionary of freq and interval value.
        @return: string value which compute FREQILY;INTERVAL
        """

        weekdays = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
        weekstring = ''
        monthstring = ''
        yearstring = ''

        freq = datas.get('freq')
        if freq == 'None':
            return ''

        interval_srting = datas.get('interval') and (';INTERVAL=' + str(datas.get('interval'))) or ''

        if freq == 'weekly':

            byday = map(lambda x: x.upper(), filter(lambda x: datas.get(x) and x in weekdays, datas))
            if byday:
                weekstring = ';BYDAY=' + ','.join(byday)

        elif freq == 'monthly':
            if datas.get('select1')=='date' and (datas.get('day') < 1 or datas.get('day') > 31):
                raise osv.except_osv(_('Error!'), ("Please select proper Day of month"))
            if datas.get('select1')=='day':
                monthstring = ';BYDAY=' + datas.get('byday') + datas.get('week_list')
            elif datas.get('select1')=='date':
                monthstring = ';BYMONTHDAY=' + str(datas.get('day'))

        elif freq == 'yearly':
            if datas.get('select1')=='date' and (datas.get('day') < 1 or datas.get('day') > 31):
                raise osv.except_osv(_('Error!'), ("Please select proper Day of month"))
            bymonth = ';BYMONTH=' + str(datas.get('month_list'))
            if datas.get('select1')=='day':
                bystring = ';BYDAY=' + datas.get('byday') + datas.get('week_list')
            elif datas.get('select1')=='date':
                bystring = ';BYMONTHDAY=' + str(datas.get('day'))
            yearstring = bymonth + bystring

        if datas.get('end_date'):
            datas['end_date'] = ''.join((re.compile('\d')).findall(datas.get('end_date'))) + '235959Z'
        enddate = (datas.get('count') and (';COUNT=' + str(datas.get('count'))) or '') +\
                             ((datas.get('end_date') and (';UNTIL=' + datas.get('end_date'))) or '')

        rrule_string = 'FREQ=' + freq.upper() + weekstring + interval_srting \
                            + enddate + monthstring + yearstring

        return rrule_string


    def search(self, cr, uid, args, offset=0, limit=100, order=None,
            context=None, count=False):
        """
        Overrides orm search method.
        @param cr: the current row, from the database cursor,
        @param user: the current user’s ID for security checks,
        @param args: list of tuples of form [(‘name_of_the_field’, ‘operator’, value), ...].
        @param offset: The Number of Results to Pass
        @param limit: The Number of Results to Return
        @return: List of id
        """
        args_without_date = []
        start_date = False
        until_date = False
        for arg in args:
            if arg[0] not in ('date', unicode('date')):
                args_without_date.append(arg)
            else:
                if arg[1] in ('>', '>='):
                    if start_date:
                        continue
                    start_date = arg[2]
                elif arg[1] in ('<', '<='):
                    if until_date:
                        continue
                    until_date = arg[2]
                else:
                        args_without_date.append(arg)
       # args.append(('rrule_type', '=', 'none'))
        res = super(calendar_event, self).search(cr, uid, args, offset, limit, order, context, count)
        if start_date and until_date:
             recur_args = [('rrule_type', '!=', 'none'), ('date', '<=', until_date), '|', ('end_date', '=', False), ('end_date', '>=', start_date)]
             recur_args.extend(args_without_date)
             recur_res = super(calendar_event, self).search(cr, uid, recur_args, offset, limit, order, context, count)

        if not isinstance(res, list):
            res = [res]
        if not isinstance(recur_res, list):
            recur_res = [recur_res]

        res.extend(recur_res)
        res = list(set(res))
        return self.get_recurrent_ids(cr, uid, res, start_date, until_date, limit)


    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        """
        Writes values in one or several fields.
        @param self: the object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of crm meeting's ids
        @param vals: Dictionary of field value.
        @return: True
        """
        if not context:
            context = {}
        if isinstance(ids, (str, int, long)):
            select = [ids]
        else:
            select = ids
        new_ids = []
        for event_id in select:
            if len(str(event_id).split('-')) > 1:
                data = self.read(cr, uid, event_id, ['date', 'date_deadline', \
                                                    'rrule', 'duration'])
                if data.get('rrule'):
                    real_date = data.get('date')
                    data.update(vals)
                    new_id = self.modify_this(cr, uid, event_id, data, \
                                                real_date, context)
                    context.update({'active_id': new_id, 'active_ids': [new_id]})
                    continue
            event_id = base_calendar_id2real_id(event_id)
            if not event_id in new_ids:
                new_ids.append(event_id)
        res = super(calendar_event, self).write(cr, uid, new_ids, vals, context=context)
        if vals.has_key('alarm_id') or vals.has_key('base_calendar_alarm_id'):
            alarm_obj = self.pool.get('res.alarm')
            context.update({'alarm_id': vals.get('alarm_id')})
            alarm_obj.do_alarm_create(cr, uid, new_ids, self._name, 'date', \
                                            context=context)
        return res

    def browse(self, cr, uid, ids, context=None, list_class=None, fields_process={}):
        """
        Overrides orm browse method.
        @param self: the object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of crm meeting's ids
        @return: the object list.
        """
        if isinstance(ids, (str, int, long)):
            select = [ids]
        else:
            select = ids
        select = map(lambda x: base_calendar_id2real_id(x), select)
        res = super(calendar_event, self).browse(cr, uid, select, context, \
                                                    list_class, fields_process)
        if isinstance(ids, (str, int, long)):
            return res and res[0] or False

        return res

    def read(self, cr, uid, ids, fields=None, context={}, load='_classic_read'):
        """
        Overrides orm Read method.Read List of fields for calendar event.
        @param cr: the current row, from the database cursor,
        @param user: the current user’s ID for security checks,
        @param ids: List of calendar event's id.
        @param fields: List of fields.
        @return: List of Dictionary of form [{‘name_of_the_field’: value, ...}, ...]
        """
        if isinstance(ids, (str, int, long)):
            select = [ids]
        else:
            select = ids
        select = map(lambda x: (x, base_calendar_id2real_id(x)), select)
        result = []
        if fields and 'date' not in fields:
            fields.append('date')
        for base_calendar_id, real_id in select:
            res = super(calendar_event, self).read(cr, uid, real_id, fields=fields, context=context, load=load)
            ls = base_calendar_id2real_id(base_calendar_id, with_date=res.get('duration', 0))
            if not isinstance(ls, (str, int, long)) and len(ls) >= 2:
                res['date'] = ls[1]
                res['date_deadline'] = ls[2]
            res['id'] = base_calendar_id

            result.append(res)
        if isinstance(ids, (str, int, long)):
            return result and result[0] or False
        return result

    def copy(self, cr, uid, id, default=None, context={}):
        """
        Duplicate record on specified id.
        @param self: the object pointer.
        @param cr: the current row, from the database cursor,
        @param id: id of record from which we duplicated.
        @return: Duplicate record id.
        """
        res = super(calendar_event, self).copy(cr, uid, base_calendar_id2real_id(id), default, context)
        alarm_obj = self.pool.get('res.alarm')
        alarm_obj.do_alarm_create(cr, uid, [res], self._name, 'date')

        return res

    def unlink(self, cr, uid, ids, context=None):
        """
        Deletes records specified in ids.
        @param self: the object pointer.
        @param cr: the current row, from the database cursor,
        @param id: List of calendar event's id.
        @return: True
        """
        res = False
        for id in ids:
            ls = base_calendar_id2real_id(id)
            if not isinstance(ls, (str, int, long)) and len(ls) >= 2:
                date_new = ls[1]
                for record in self.read(cr, uid, [base_calendar_id2real_id(id)], \
                                            ['date', 'rrule', 'exdate']):
                    if record['rrule']:
                        exdate = (record['exdate'] and (record['exdate'] + ',') or '') + ''.join((re.compile('\d')).findall(date_new)) + 'Z'
                        if record['date'] == date_new:
                            res = self.write(cr, uid, [base_calendar_id2real_id(id)], {'exdate': exdate})
                    else:
                        ids = map(lambda x: base_calendar_id2real_id(x), ids)
                        res = super(calendar_event, self).unlink(cr, uid, \
                                                base_calendar_id2real_id(ids))
                        alarm_obj = self.pool.get('res.alarm')
                        alarm_obj.do_alarm_unlink(cr, uid, ids, self._name)
            else:
                ids = map(lambda x: base_calendar_id2real_id(x), ids)
                res = super(calendar_event, self).unlink(cr, uid, ids)
                alarm_obj = self.pool.get('res.alarm')
                alarm_obj.do_alarm_unlink(cr, uid, ids, self._name)
        return res

    def create(self, cr, uid, vals, context={}):
        """
        Create new record.
        @param self: the object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param vals: dictionary of every field value.
        @return: new created record id.
        """
        res = super(calendar_event, self).create(cr, uid, vals, context)
        alarm_obj = self.pool.get('res.alarm')
        alarm_obj.do_alarm_create(cr, uid, [res], self._name, 'date')
        return res

calendar_event()

class calendar_todo(osv.osv):
    """ Calendar Task """

    _name = "calendar.todo"
    _inherit = "calendar.event"
    _description = "Calendar Task"

    def _get_date(self, cr, uid, ids, name, arg, context):
        """
        Get Date
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of calendar todo's IDs.
        @param args: list of tuples of form [(‘name_of_the_field’, ‘operator’, value), ...].
        @param context: A standard dictionary for contextual values
        """

        res = {}
        for event in self.browse(cr, uid, ids, context=context):
            res[event.id] = event.date_start
        return res

    def _set_date(self, cr, uid, id, name, value, arg, context):
        """
        Set Date
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param id: calendar's ID.
        @param value: Get Value
        @param args: list of tuples of form [(‘name_of_the_field’, ‘operator’, value), ...].
        @param context: A standard dictionary for contextual values
        """

        event = self.browse(cr, uid, id, context=context)
        cr.execute("UPDATE %s set date_start='%s' where id=%s" \
                            % (self._table, value, id))
        return True

    _columns = {
        'date': fields.function(_get_date, method=True, fnct_inv=_set_date, \
                            string='Duration', store=True, type='datetime'),
        'duration': fields.integer('Duration'),
    }

    __attribute__ = {}


calendar_todo()

class ir_attachment(osv.osv):
    _name = 'ir.attachment'
    _inherit = 'ir.attachment'

    def search_count(self, cr, user, args, context=None):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param user: the current user’s ID for security checks,
        @param args: list of tuples of form [(‘name_of_the_field’, ‘operator’, value), ...].
        @param context: A standard dictionary for contextual values
        """

        args1 = []
        for arg in args:
            args1.append(map(lambda x:str(x).split('-')[0], arg))
        return super(ir_attachment, self).search_count(cr, user, args1, context)

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
            context=None, count=False):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param args: list of tuples of form [(‘name_of_the_field’, ‘operator’, value), ...].
        @param offset: The Number of Results to pass,
        @param limit: The Number of Results to Return,
        @param context: A standard dictionary for contextual values
        """

        new_args = args
        for i, arg in enumerate(new_args):
            if arg[0] == 'res_id':
                new_args[i] = (arg[0], arg[1], base_calendar_id2real_id(arg[2]))
        return super(ir_attachment, self).search(cr, uid, new_args, offset=offset,
                            limit=limit, order=order,
                            context=context, count=False)
ir_attachment()

class ir_values(osv.osv):
    _inherit = 'ir.values'

    def set(self, cr, uid, key, key2, name, models, value, replace=True, \
            isobject=False, meta=False, preserve_user=False, company=False):
        """
        Set IR Values
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
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

    def get(self, cr, uid, key, key2, models, meta=False, context={}, \
             res_id_req=False, without_user=True, key2_req=True):
        """
        Get IR Values
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param model: Get The Model
        """

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

    def read(self, cr, uid, ids, fields=None, context={},
            load='_classic_read'):
        """
        Read IR Model
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of IR Model’s IDs.
        @param context: A standard dictionary for contextual values
        """

        data = super(ir_model, self).read(cr, uid, ids, fields=fields, \
                        context=context, load=load)
        if data:
            for val in data:
                val['id'] = base_calendar_id2real_id(val['id'])
        return data

ir_model()

class virtual_report_spool(web_services.report_spool):

    def exp_report(self, db, uid, object, ids, datas=None, context=None):
        """
        Export Report
        @param self: The object pointer
        @param db: get the current database,
        @param uid: the current user’s ID for security checks,
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

class res_users(osv.osv):
    _inherit = 'res.users'

    def _get_user_avail(self, cr, uid, ids, context=None):
        """
        Get USer Availability
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of res user’s IDs.
        @param context: A standard dictionary for contextual values
        """

        current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        res = {}
        attendee_obj = self.pool.get('calendar.attendee')
        attendee_ids = attendee_obj.search(cr, uid, [
                    ('event_date', '<=', current_datetime), ('event_end_date', '<=', current_datetime),
                    ('state', '=', 'accepted'), ('user_id', 'in', ids)
                    ])

       # result = cr.dictfetchall()
        for attendee_data in attendee_obj.read(cr, uid, attendee_ids, ['user_id']):
            user_id = attendee_data['user_id']
            status = 'busy'
            res.update({user_id:status})

        #TOCHECK: Delegated Event
        for user_id in ids:
            if user_id not in res:
                res[user_id] = 'free'

        return res

    def _get_user_avail_fun(self, cr, uid, ids, name, args, context=None):
        """
        Get USer Availability Function
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of res user’s IDs.
        @param context: A standard dictionary for contextual values
        """

        return self._get_user_avail(cr, uid, ids, context=context)

    _columns = {
            'availability': fields.function(_get_user_avail_fun, type='selection', \
                    selection=[('free', 'Free'), ('busy', 'Busy')], \
                    string='Free/Busy', method=True),
    }
res_users()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
