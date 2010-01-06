# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from osv import fields, osv
from service import web_services
from tools.translate import _
import re
import time

months = {1:"January", 2:"February", 3:"March", 4:"April", 5:"May", 6:"June", \
            7:"July", 8:"August", 9:"September", 10:"October", 11:"November", \
            12:"December"}

def caldav_id2real_id(caldav_id = None, with_date=False):
    if caldav_id and isinstance(caldav_id, (str, unicode)):
        res = caldav_id.split('-')
        if len(res) >= 2:
            real_id = res[0]
            if with_date:
                real_date = time.strftime("%Y-%m-%d %H:%M:%S", \
                                 time.strptime(res[1], "%Y%m%d%H%M%S"))
                return (int(real_id), real_date)
            return int(real_id)
    return caldav_id and int(caldav_id) or caldav_id

def real_id2caldav_id(real_id , recurrent_date):    
    if real_id and recurrent_date:
        recurrent_date = time.strftime("%Y%m%d%H%M%S", \
                                 time.strptime(recurrent_date, "%Y-%m-%d %H:%M:%S"))
        return '%d-%s'%(real_id, recurrent_date)
    return real_id

def uid2openobjectid(cr, uidval, oomodel):
    __rege = re.compile(r'OpenObject-([\w|\.]+)_([0-9]+)@(\w+)$')
    wematch = __rege.match(uidval.encode('utf8'))
    if not wematch:
#                raise osv.except_osv('Warning!!', "Cannot locate UID in %s" % val['id'])
        return False
    else:
        model, id, dbname = wematch.groups()
        if (not model == oomodel) or (not dbname == cr.dbname):
            return False
        cr.execute('select distinct(id) from %s' % model.replace('.', '_'))
        ids = map(lambda x: str(x[0]), cr.fetchall())
        if id in ids:
            return id
        return False
    
def openobjectid2uid(cr, uidval, oomodel):
    value = 'OpenObject-%s_%s@%s' % (oomodel, uidval, cr.dbname)
    return value

class crm_caldav_attendee(osv.osv):
    _name = 'crm.caldav.attendee'
    _description = 'Attendee information'
    _rec_name = 'cutype'

    __attribute__ = {
        'cutype': {'field':'cutype', 'type':'text'}, 
        'member': {'field':'member', 'type':'text'}, 
        'role': {'field':'role', 'type':'selection'}, 
        'partstat': {'field':'partstat', 'type':'text'}, 
        'rsvp': {'field':'rsvp', 'type':'boolean'}, 
        'delegated-to': {'field':'delegated_to', 'type':'char'}, 
        'delegated-from': {'field':'delegated_from', 'type':'char'}, 
        'sent-by': {'field':'sent_by', 'type':'text'}, 
        'cn': {'field':'cn', 'type':'text'}, 
        'dir': {'field':'dir', 'type':'text'}, 
        'language': {'field':'language', 'type':'text'}, 
    }

    _columns = {
            'cutype': fields.selection([('INDIVIDUAL', 'INDIVIDUAL'), ('GROUP', 'GROUP'), \
                                             ('RESOURCE', 'RESOURCE'), ('ROOM', 'ROOM'), \
                                              ('UNKNOWN', 'UNKNOWN') ], 'CUTYPE', \
                                              help="Specify the type of calendar user"), 
            'member': fields.char('Member', size=124, help="Indicate the groups that the attendee belongs to"), 
            'role': fields.selection([ ('REQ-PARTICIPANT', 'REQ-PARTICIPANT'), \
                                ('CHAIR', 'CHAIR'), ('OPT-PARTICIPANT', 'OPT-PARTICIPANT'), \
                                ('NON-PARTICIPANT', 'NON-PARTICIPANT')], 'ROLE', \
                                help='Participation role for the calendar user'), 
            'partstat': fields.selection([('TENTATIVE', 'TENTATIVE'), 
                                    ('NEEDS-ACTION', 'NEEDS-ACTION'), 
                                    ('ACCEPTED', 'ACCEPTED'), 
                                    ('DECLINED', 'DECLINED'), 
                                    ('DELEGATED', 'DELEGATED')], 'PARTSTAT', \
                                    help="Status of the attendee's participation"), 
            'rsvp':  fields.boolean('RSVP', help="Indicats whether the favor of a reply is requested"), 
            'delegated_to': fields.char('DELEGATED-TO', size=124, \
                                        help="The calendar users that the original request was delegated to"), 
            'delegated_from': fields.char('DELEGATED-FROM', size=124, \
                              help="Indicates whom the request was delegated from"), 
            'sent_by': fields.char('SENT-BY', size=124, \
                                   help="Specify the calendar user that is acting on behalf of the calendar user"), 
            'cn': fields.char('CN', size=124, help="The common or displayable name to be associated with the calendar user"), 
            'dir': fields.char('DIR', size=124, help="Reference to the URI that points to the directory information corresponding to the attendee."), 
            'language': fields.char('LANGUAGE', size=124, help="To specify the language for text values in a property or property parameter."),
            'user_id': fields.many2one('res.users', 'Responsible'),
                }

crm_caldav_attendee()

class crm_caldav_alarm(osv.osv):
    _name = 'crm.caldav.alarm'
    _description = 'Event alarm information'

    __attribute__ = {
            'action': {'field': 'action', 'type': 'text'}, 
            'description': {'field': 'name', 'type': 'text'}, 
            'summary': {'field': 'description', 'type': 'text'}, 
            'attendee': {'field': 'attendee_ids', 'type': 'text'}, 
            'trigger_related': {'field': 'trigger_related', 'type': 'text'}, 
            'trigger_duration': {'field': 'trigger_duration', 'type': 'text'}, 
            'trigger_occurs': {'field': 'trigger_occurs', 'type': 'text'}, 
            'trigger_interval': {'field': 'trigger_interval', 'type': 'text'}, 
            'duration': {'field': 'duration', 'type': 'text'}, 
            'repeat': {'field': 'repeat', 'type': 'text'}, 
            'attach': {'field': 'attach', 'type': 'text'}, 
    }
     
    _columns = {
            'name': fields.char('Summary', size=124, help="""Contains the text to be used as the message subject for EMAIL
or contains the text to be used for DISPLAY"""), 
            'action': fields.selection([('AUDIO', 'AUDIO'), ('DISPLAY', 'DISPLAY'), \
                    ('PROCEDURE', 'PROCEDURE'), ('EMAIL', 'EMAIL') ], 'Action', \
                    required=True, help="Defines the action to be invoked when an alarm is triggered"), 
            'description': fields.text('Description', help='Provides a more complete description of the calendar component, than that provided by the "SUMMARY" property'), 
            'attendee_ids': fields.many2many('crm.caldav.attendee', 'alarm_attendee_rel', \
                                          'alarm_id', 'attendee_id', 'Attendees'), 
            'trigger_occurs': fields.selection([('BEFORE', 'BEFORE'), ('AFTER', 'AFTER')], \
                                        'Trigger time', required=True), 
            'trigger_interval': fields.selection([('MINUTES', 'MINUTES'), ('HOURS', 'HOURS'), \
                    ('DAYS', 'DAYS')], 'Trigger duration', required=True), 
            'trigger_duration':  fields.integer('Time', required=True), 
            'trigger_related':  fields.selection([('start', 'The event starts'), ('end', \
                                           'The event ends')], 'Trigger Occures at', required=True), 
            'duration': fields.integer('Duration', help="""Duration' and 'Repeat' \
are both optional, but if one occurs, so MUST the other"""), 
            'repeat': fields.integer('Repeat'), # TODO 
            'attach': fields.binary('Attachment', help="""* Points to a sound resource, which is rendered when the alarm is triggered for AUDIO, 
* File which is intended to be sent as message attachments for EMAIL,
* Points to a procedure resource, which is invoked when the alarm is triggered for PROCEDURE.
"""), 
            'active': fields.boolean('Active', help="If the active field is set to true, it will allow you to hide the event alarm information without removing it."), 
                }

    _defaults = {
        'action':  lambda *x: 'EMAIL', 
        'trigger_interval':  lambda *x: 'MINUTES', 
        'trigger_duration': lambda *x: 5, 
        'trigger_occurs': lambda *x: 'BEFORE', 
        'trigger_related': lambda *x: 'start', 
        'active': lambda *x: 1, 
                 }

    def do_create(self, cr, uid, ids, context=None, *args):
        datas = self.read(cr, uid, ids)[0]
        summary = str(datas['trigger_duration']) + ' ' + \
                        datas['trigger_interval'].title() + ' '  + \
                        datas['trigger_occurs'].title()
        self.write(cr, uid, ids, {'name': summary})
        if not context or not context.get('model'):
            return {}
        else:
            model = context.get('model')
        obj = self.pool.get(model)
        obj.write(cr, uid, context['active_id'], {'alarm_id': ids[0]})
        return {}
        
crm_caldav_alarm()

class ir_attachment(osv.osv):
    _name = 'ir.attachment'
    _inherit = 'ir.attachment'

    def search_count(self, cr, user, args, context=None):
        args1 = []
        for arg in args:
            args1.append(map(lambda x:str(x).split('-')[0], arg))
        return super(ir_attachment, self).search_count(cr, user, args1, context)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, 
            context=None, count=False):
        new_args = args
        for i, arg in enumerate(new_args):
            if arg[0] == 'res_id':
                new_args[i] = (arg[0], arg[1], caldav_id2real_id(arg[2]))
        return super(ir_attachment, self).search(cr, uid, new_args, offset=offset,
                                                limit=limit, order=order,
                                                context=context, count=False)
ir_attachment()

class ir_values(osv.osv):
    _inherit = 'ir.values'

    def set(self, cr, uid, key, key2, name, models, value, replace=True, isobject=False, \
                         meta=False, preserve_user=False, company=False):
        new_model = []
        for data in models:
            if type(data) in (list, tuple):
                new_model.append((data[0], caldav_id2real_id(data[1])))
            else:
                new_model.append(data)
        return super(ir_values, self).set(cr, uid, key, key2, name, new_model, value, \
                                   replace, isobject, meta, preserve_user, company)

    def get(self, cr, uid, key, key2, models, meta=False, context={}, res_id_req=False, \
                    without_user=True, key2_req=True):
        new_model = []
        for data in models:
            if type(data) in (list, tuple):
                new_model.append((data[0], caldav_id2real_id(data[1])))
            else:
                new_model.append(data)
        return super(ir_values, self).get(cr, uid, key, key2, new_model, meta, context, \
                                      res_id_req, without_user, key2_req)

ir_values()

class ir_model(osv.osv):

    _inherit = 'ir.model'

    def read(self, cr, uid, ids, fields=None, context={}, 
            load='_classic_read'):
        data = super(ir_model, self).read(cr, uid, ids, fields=fields, context=context, load=load)
        if data:
            for val in data:
                val['id'] = caldav_id2real_id(val['id'])
        return data
    
ir_model()

class virtual_report_spool(web_services.report_spool):

    def exp_report(self, db, uid, object, ids, datas=None, context=None):
        if object == 'printscreen.list':
            return super(virtual_report_spool, self).exp_report(db, uid, object, ids, datas, context)
        new_ids = []
        for id in ids:
            new_ids.append(caldav_id2real_id(id))
        datas['id'] = caldav_id2real_id(datas['id'])
        super(virtual_report_spool, self).exp_report(db, uid, object, new_ids, datas, context)
        return super(virtual_report_spool, self).exp_report(db, uid, object, new_ids, datas, context)

virtual_report_spool()

class set_rrule_wizard(osv.osv_memory):
    _name = "caldav.set.rrule"
    _description = "Set RRULE"

    _columns = {
        'freq': fields.selection([('None', 'No Repeat'), \
                            ('SECONDLY', 'SECONDLY'), \
                            ('MINUTELY', 'MINUTELY'), \
                            ('HOURLY', 'HOURLY'), \
                            ('DAILY', 'DAILY'), \
                            ('WEEKLY', 'WEEKLY'), \
                            ('MONTHLY', 'MONTHLY'), \
                            ('YEARLY', 'YEARLY')], 'Frequency', required=True), 
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
                            ('day', 'Day of month')], 'Select Option'), 
        'day': fields.integer('Day of month'), 
        'week_list': fields.selection([('MO', 'Monday'), ('TU', 'Tuesday'), \
                                       ('WE', 'Wednesday'), ('TH', 'Thursday'), \
                                       ('FR', 'Friday'), ('SA', 'Saturday'), \
                                       ('SU', 'Sunday')], 'Weekday'), 
        'byday': fields.selection([('1', 'First'), ('2', 'Second'), \
                                   ('3', 'Third'), ('4', 'Fourth'), \
                                   ('5', 'Fifth'), ('-1', 'Last')], 'By day'), 
        'month_list': fields.selection(months.items(), 'Month'), 
        'end_date': fields.date('Repeat Until')
    }

    _defaults = {
                 'freq':  lambda *x: 'DAILY', 
                 'select1':  lambda *x: 'date', 
                 'interval':  lambda *x: 1, 
                 }

    def compute_rule_string(self, cr, uid, datas, context=None, *args):
        weekdays = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
        weekstring = ''
        monthstring = ''
        yearstring = ''

#    logic for computing rrule string

        freq = datas.get('freq')
        if freq == 'None':
            obj.write(cr, uid, [res_obj.id], {'rrule' : ''})
            return {}

        if freq == 'WEEKLY':
            byday = map(lambda x: x.upper(), filter(lambda x: datas.get(x) and x in weekdays, datas))
            if byday: 
                weekstring = ';BYDAY=' + ','.join(byday)

        elif freq == 'MONTHLY':
            byday = ''
            if datas.get('select1')=='date'  and (datas.get('day') < 1 or datas.get('day') > 31):
                raise osv.except_osv(_('Error!'), ("Please select proper Day of month"))
            if datas.get('byday') and datas.get('week_list'):
                byday = ';BYDAY=' + datas.get('byday') + datas.get('week_list')
            monthstring = byday or (';BYMONTHDAY=' + str(datas.get('day')))

        elif freq == 'YEARLY':
            bymonth = ''
            byday = ''
            if datas.get('select1')=='date'  and (datas.get('day') < 1 or datas.get('day') > 31):
                raise osv.except_osv(_('Error!'), ("Please select proper Day of month"))
            if datas.get('byday') and datas.get('week_list'):
                byday = ';BYDAY=' + datas.get('byday') + datas.get('week_list')
            if datas.get('month_list'):
                bymonth = ';BYMONTH=' + str(datas.get('month_list'))
            bymonthday = ';BYMONTHDAY=' + str(datas.get('day'))
            yearstring = bymonth + (datas.get('day') and bymonthday or '') + byday

        if datas.get('end_date'):
            datas['end_date'] = ''.join((re.compile('\d')).findall(datas.get('end_date'))) + '235959Z'
        enddate = (datas.get('count') and (';COUNT=' +  str(datas.get('count'))) or '') +\
                             ((datas.get('end_date') and (';UNTIL=' + datas.get('end_date'))) or '')

        rrule_string = 'FREQ=' + freq +  weekstring + ';INTERVAL=' + \
                str(datas.get('interval')) + enddate + monthstring + yearstring

#        End logic 
        return rrule_string

    def do_add(self, cr, uid, ids, context={}):
        datas = self.read(cr, uid, ids)[0]
        if datas.get('interval') <= 0:
            raise osv.except_osv(_('Error!'), ("Please select proper Interval"))
        

        if not context or not context.get('model'):
            return {}
        else:
            model = context.get('model')
        obj = self.pool.get(model)
        res_obj = obj.browse(cr, uid, context['active_id'])
        
        rrule_string = self.compute_rule_string(cr, uid, datas)
        obj.write(cr, uid, [res_obj.id], {'rrule' : rrule_string})
        return {}

set_rrule_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
