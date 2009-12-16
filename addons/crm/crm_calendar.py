# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv
from time import strftime
import time
import base64
import vobject
from dateutil.rrule import *
from dateutil import parser
import  datetime
from time import strftime
from pytz import timezone
import tools
from service import web_services

def caldevIDs2readIDs(caldev_ID = None):
    if caldev_ID:
        if isinstance(caldev_ID, str):
            return int(caldev_ID.split('-')[0])
        return caldev_ID


class crm_caldav_attendee(osv.osv):
    _name = 'crm.caldav.attendee'
    _description = 'Attendee information'
    _rec_name = 'cutype'

    __attribute__ = {
        'cutype' : {'field':'cutype', 'type':'text'}, # Use: 0-1    Specify the type of calendar user specified by the property like "INDIVIDUAL"/"GROUP"/"RESOURCE"/"ROOM"/"UNKNOWN".
        'member' : {'field':'member', 'type':'text'}, # Use: 0-1    Specify the group or list membership of the calendar user specified by the property.
        'role' : {'field':'role', 'type':'selection'}, # Use: 0-1    Specify the participation role for the calendar user specified by the property like "CHAIR"/"REQ-PARTICIPANT"/"OPT-PARTICIPANT"/"NON-PARTICIPANT"
        'partstat' : {'field':'partstat', 'type':'text'}, # Use: 0-1    Specify the participation status for the calendar user specified by the property. like use for VEVENT :- "NEEDS-ACTION"/"ACCEPTED"/"DECLINED"/"TENTATIVE"/"DELEGATED", use for VTODO :-"NEEDS-ACTION"/"ACCEPTED"/"DECLINED"/"TENTATIVE"/"DELEGATED"/"COMPLETED"/"IN-PROCESS" and use for VJOURNAL :- "NEEDS-ACTION"/"ACCEPTED"/"DECLINED".
        'rsvp' : {'field':'rsvp', 'type':'boolean'}, # Use: 0-1    Specify whether there is an expectation of a favor of a reply from the calendar user specified by the property value like TRUE / FALSE.
        'delegated-to' : {'field':'delegated_to', 'type':'char'}, # Use: 0-1    Specify the calendar users to whom the calendar user specified by the property has delegated participation.
        'delegated-from' : {'field':'delegated_from', 'type':'char'}, # Use: 0-1    Specify the calendar users that have delegated their participation to the calendar user specified by the property.
        'sent-by' : {'field':'sent_by', 'type':'text'}, # Use: 0-1    Specify the calendar user that is acting on behalf of the calendar user specified by the property.
        'cn' : {'field':'cn', 'type':'text'}, # Use: 0-1    Specify the common name to be associated with the calendar user specified by the property.
        'dir' : {'field':'dir', 'type':'text'}, # Use: 0-1    Specify reference to a directory entry associated with the calendar user specified by the property.
        'language' : {'field':'language', 'type':'text'}, # Use: 0-1    Specify the language for text values in a property or property parameter.
    }

    _columns = {
                'cutype' : fields.selection([('INDIVIDUAL', 'INDIVIDUAL'), ('GROUP', 'GROUP'), \
                        ('RESOURCE', 'RESOURCE'), ('ROOM', 'ROOM'), ('UNKNOWN', 'UNKNOWN') ], 'CUTYPE'), 
                'member' : fields.char('Member', size=124), 
                'role' : fields.selection([('CHAIR', 'CHAIR'), ('REQ-PARTICIPANT', 'REQ-PARTICIPANT'), \
                        ('OPT-PARTICIPANT', 'OPT-PARTICIPANT'), ('NON-PARTICIPANT', 'NON-PARTICIPANT')], 'ROLE'), 
                'partstat' : fields.selection([('NEEDS-ACTION', 'NEEDS-ACTION'), ('ACCEPTED', 'ACCEPTED'), \
                                ('DECLINED', 'DECLINED'), ('TENTATIVE', 'TENTATIVE'), \
                                ('DELEGATED', 'DELEGATED')], 'PARTSTAT'), 
                'rsvp' :  fields.boolean('RSVP'), 
                'delegated_to' : fields.char('DELEGATED-TO', size=124), 
                'delegated_from' : fields.char('DELEGATED-FROM', size=124), 
                'sent_by' : fields.char('SENT-BY', size=124), 
                'cn' : fields.char('CN', size=124), 
                'dir' : fields.char('DIR', size=124), 
                'language' : fields.char('LANGUAGE', size=124), 
                }
    _defaults = {
        'cn' :  lambda *x: 'MAILTO:', 
        }
    
crm_caldav_attendee()


class crm_caldav_alarm(osv.osv):
    _name = 'crm.caldav.alarm'
    _description = 'Event alarm information'

    __attribute__ = {
            'action': {'field': 'action', 'type': 'text'},
            'description': {'field': 'name', 'type': 'text'},
            'summary': {'field': 'description', 'type': 'text'},
            'attendee': {'field': 'attendee', 'type': 'text'},
            'trigger_related': {'field': 'trigger_related', 'type': 'text'}, 
            'trigger_duration': {'field': 'trigger_duration', 'type': 'text'},
            'trigger_occurs': {'field': 'trigger_occurs', 'type': 'text'}, 
            'trigger_interval': {'field': 'trigger_interval', 'type': 'text'}, 
            'duration': {'field': 'duration', 'type': 'text'},
            'repeat': {'field': 'repeat', 'type': 'text'},
            'attach': {'field': 'attach', 'type': 'text'},
    }
     
    _columns = {
                'name' : fields.char('Summary', size=124), 
                'action' : fields.selection([('AUDIO', 'AUDIO'), ('DISPLAY', 'DISPLAY'), \
                        ('PROCEDURE', 'PROCEDURE'), ('EMAIL', 'EMAIL') ], 'Action' , required=True), 
                'description' : fields.text('Description'), 
                'attendee': fields.many2many('crm.caldav.attendee', 'alarm_attendee_rel', \
                                              'alarm_id', 'attendee_id', 'Attendees'), 
                'trigger_occurs' : fields.selection([('BEFORE', 'BEFORE'), ('AFTER', 'AFTER')]\
                                                 , 'Trigger time', required=True), 
                'trigger_interval' : fields.selection([('MINUTES', 'MINUTES'), ('HOURS', 'HOURS'), \
                        ('DAYS', 'DAYS')], 'Trugger duration', required=True), 
                'trigger_duration' :  fields.integer('TIme' , required=True), 
                'trigger_related' :  fields.selection([('starts', 'The event starts'), ('end', \
                                               'The event ends')], 'Trigger Occures at', required=True), 
                'duration' : fields.integer('Duration'), 
                'repeat' : fields.integer('Repeat'), # TODO 
                'attach' : fields.binary('Attachment'), 
                'active' : fields.boolean('Active'), 
                }

    _defaults = {
        'action' :  lambda *x: 'EMAIL', 
        'trigger_interval' :  lambda *x: 'MINUTES',
        'trigger_duration' : lambda *x: 5,  
        'trigger_occurs' : lambda *x: 'BEFORE', 
        'trigger_related' : lambda *x: 'starts', 
                 }
    
crm_caldav_alarm()

class crm_case(osv.osv):
    _name = 'crm.case'
    _inherit = 'crm.case'
    _description = 'Cases'

    __attribute__ = {
        'class' : {'field':'class', 'type':'text'}, 
        'created' : {'field':'create_date', 'type':'datetime'}, # keep none for now
        'description' : {'field':'description', 'type':'text'}, 
        'dtstart' : {'field':'date', 'type':'datetime'}, 
        #'last-mod' : {'field':'write_date', 'type':'datetime'},
        'location' : {'field':'location', 'type':'text'}, 
#        'organizer' : {'field':'partner_id', 'sub-field':'name', 'type':'many2one'}, 
        'priority' : {'field':'priority', 'type':'int'}, 
        'dtstamp'  : {'field':'date', 'type':'datetime'}, 
        'seq' : None, 
        'status' : {'field':'state', 'type':'selection', 'mapping' : {'TENTATIVE' : 'draft', \
                                                  'CONFIRMED' : 'open' , 'CANCELLED' : 'cancel'}}, 
        'summary' : {'field':'name', 'type':'text'}, 
        'transp' : {'field':'transparent', 'type':'text'}, 
        'uid' : {'field':'id', 'type':'text'}, 
        'url' : {'field':'caldav_url', 'type':'text'}, 
        'recurid' : None, 
#        'attach' : {'field':'attachment_ids', 'sub-field':'datas', 'type':'list'}, 
        'attendee' : {'field':'attendees', 'type':'many2many', 'object' : 'crm.caldav.attendee'}, 
#        'categories' : {'field':'categ_id', 'sub-field':'name'},
#        'categories' : {'field':None , 'sub-field':'name', 'type':'text'}, # keep none for now
        'comment' : None, 
        'contact' : None, 
        'exdate'  : None, 
        'exrule'  : None, 
        'rstatus' : None, 
        'related' : None, 
        'resources' : None, 
        'rdate' : None, 
        'rrule' : {'field':'rrule', 'type':'text'}, 
        'x-openobject-id' : {'field':'id', 'type':'text'}, 
        'x-openobject-model' : {'value':_name, 'type':'text'}, 
#        'duration' : {'field':'duration'},
        'dtend' : {'field':'date_closed', 'type':'datetime'}, 
        'valarm' : {'field':'alarm_id', 'type':'many2one', 'object' : 'crm.caldav.alarm'}, 
    }

    def _get_location(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for case in self.browse(cr, uid, ids):
            if case.partner_address_id:
                add = case.partner_address_id
                st = add.street and add.street+',\n'  or ''
                st2 = add.street2 and add.street2+',\n'  or ''
                ct = add.city and add.city+',\n'  or ''
                zip = add.zip and add.zip or ''
                country = add.country_id and add.country_id.name+',\n'  or ''
                res[case.id] = st + st2+ ct + country + zip
            else:
                res[case.id] = ''
        return res

    def _get_rdates(self, cr, uid, ids, name, arg, context=None):
        res = {}
        context.update({'read':True})
        for case in self.read(cr, uid, ids, ['date', 'rrule'], context=context):
            if case['rrule']:
                rule = case['rrule'].split('\n')[0]
                exdate = case['rrule'].split('\n')[1:]
                event_obj = self.pool.get('caldav.event')
                res[case['id']] = str(event_obj.get_recurrent_dates(str(rule), exdate, case['date']))
        return res

    _columns = {
        'class' : fields.selection([('PUBLIC', 'PUBLIC'), ('PRIVATE', 'PRIVATE'), \
                 ('CONFIDENTIAL', 'CONFIDENTIAL')], 'Class'), 
        'location' : fields.function(_get_location, method=True, store=True, \
                                     string='Location', type='text'), 
        'freebusy' : fields.text('FreeBusy'), 
        'transparent' : fields.selection([('OPAQUE', 'OPAQUE'), ('TRANSPARENT', 'TRANSPARENT')], 'Trensparent'), 
        'caldav_url' : fields.char('Caldav URL', size=34), 
        'rrule' : fields.text('Recurrent Rule'), 
        'rdates' : fields.function(_get_rdates, method=True, string='Recurrent Dates', \
                                   store=True, type='text'), 
       'attendees': fields.many2many('crm.caldav.attendee', 'crm_attendee_rel', 'case_id', \
                                      'attendee_id', 'Attendees'), 
       'alarm_id' : fields.many2one('crm.caldav.alarm', 'Alarm'), 
    }

    _defaults = {
             'caldav_url': lambda *a: 'http://localhost:8080', 
             'class': lambda *a: 'PUBLIC', 
             'transparent': lambda *a: 'OPAQUE', 
        }
    
    
    def run_scheduler(self, cr, uid, automatic=False, use_new_cursor=False, \
                       context=None):
        if not context:
            context={}
        cr.execute('select c.id as id, c.date as date, alarm.id as alarm_id, alarm.name as name,\
                                alarm.trigger_interval, alarm.trigger_duration, alarm.trigger_related, \
                                alarm.trigger_occurs from crm_case c \
                                   join crm_caldav_alarm alarm on (alarm.id=c.alarm_id) \
                               where alarm_id is not null and alarm.active=True')
        case_with_alarm = cr.dictfetchall() 
        case_obj = self.pool.get('crm.case')
        attendee_obj = self.pool.get('crm.caldav.attendee')
        mail_to = []
        for alarmdata in case_with_alarm:
            dtstart = datetime.datetime.strptime(alarmdata['date'], "%Y-%m-%d %H:%M:%S")
            if alarmdata['trigger_duration'] == 'DAYS':
                delta = datetime.timedelta(days=alarmdata['trigger_interval'])
            if alarmdata['trigger_duration'] == 'HOURS':
                delta = datetime.timedelta(hours=alarmdata['trigger_interval'])
            if alarmdata['trigger_duration'] == 'MINUTES':
                delta = datetime.timedelta(minutes=alarmdata['trigger_interval'])
            alarm_time =  dtstart + (alarmdata['trigger_related']== 'AFTER' and delta or -delta)
            if datetime.datetime.now() >= alarm_time:
                case_val = case_obj.browse(cr, uid, alarmdata.get('id'), context)[0]
                for att in case_val.attendees:
                    if att.cn.rsplit(':')[-1]:
                        mail_to.append(att.cn.rsplit(':')[-1])
                if mail_to:
                    sub = 'Event Reminder for ' +  case_val.name or '' 
                    body = (case_val.name or '')+ '\n\t' + (case_val.description or '') + '\n\nEvent time: ' \
                                    +(case_val.date) + '\n\nLocation: ' + (case_val.location or '') + \
                                    '\n\nMembers Details: ' + '\n'.join(mail_to)
                    tools.email_send(
                        case_val.user_id.address_id.email, 
                        mail_to, 
                        sub, 
                        body
                    )
                cr.execute('update crm_caldav_alarm set active=False\
                         where id = %s' % alarmdata['alarm_id'])
                cr.commit()
        return True

    def export_cal(self, cr, uid, ids, context={}):
        crm_data = self.read(cr, uid, ids, [], context ={'read' :True})
        event_obj = self.pool.get('caldav.event')
        event_obj.__attribute__.update(self.__attribute__)
        
        attendee_obj = self.pool.get('caldav.attendee')
        crm_attendee = self.pool.get('crm.caldav.attendee')
        attendee_obj.__attribute__.update(crm_attendee.__attribute__)
        
        alarm_obj = self.pool.get('caldav.alarm')
        crm_alarm = self.pool.get('crm.caldav.alarm')
        alarm_obj.__attribute__.update(crm_alarm.__attribute__)
        
        ical = event_obj.export_ical(cr, uid, crm_data)
        caendar_val = ical.serialize()
        caendar_val = caendar_val.replace('"', '').strip()
        return caendar_val

    def import_cal(self, cr, uid, ids, data, context={}):
        file_content = base64.decodestring(data['form']['file_path'])
        event_obj = self.pool.get('caldav.event')
        event_obj.__attribute__.update(self.__attribute__)
        
        attendee_obj = self.pool.get('caldav.attendee')
        crm_attendee = self.pool.get('crm.caldav.attendee')
        attendee_obj.__attribute__.update(crm_attendee.__attribute__)
        
        alarm_obj = self.pool.get('caldav.alarm')
        crm_alarm = self.pool.get('crm.caldav.alarm')
        alarm_obj.__attribute__.update(crm_alarm.__attribute__)
        
        vals = event_obj.import_ical(cr, uid, file_content)
        # TODO: Select proper section
        section_id = self.pool.get('crm.case.section').search(cr, uid, [])[0]
        vals.update({'section_id' : section_id})
        vals.pop('id')
        vals.pop('create_date')
        case_id = self.create(cr, uid, vals)
        return

    def search(self, cr, uid, args, offset=0, limit=None, order=None, 
            context=None, count=False):
        res = super(crm_case, self).search(cr, uid, args, offset, 
                limit, order, context, count)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        new_ids = []
        for id in ids:
            id = caldevIDs2readIDs(id)
            if not id in new_ids:
                new_ids.append(id)
        if 'case_id' in vals :
            vals['case_id'] = caldevIDs2readIDs(vals['case_id'])
        res = super(crm_case, self).write(cr, uid, new_ids, vals, context=context)
        return res

    def browse(self, cr, uid, select, context=None, list_class=None, fields_process={}):
        if not isinstance(select, list): select = [select]
        select = map(lambda x:caldevIDs2readIDs(x), select)
        return super(crm_case, self).browse(cr, uid, select, context, list_class, fields_process)

    def read(self, cr, uid, ids, fields=None, context={}, 
            load='_classic_read'):
        """         logic for recurrent event
         example : 123-20091111170822"""
        if context and context.has_key('read'):
            return super(crm_case, self).read(cr, uid, ids, fields=fields, context=context, \
                                              load=load)
        if not type(ids) == list :
            # Called from code
            return super(crm_case, self).read(cr, uid, caldevIDs2readIDs(ids), fields=fields, \
                                               context=context, load=load)
        else:
            ids = map(lambda x:caldevIDs2readIDs(x), ids)
        res = super(crm_case, self).read(cr, uid, ids, fields=fields, context=context, load=load)
        read_ids = ",".join([str(x) for x in ids])
        if not read_ids:
            return []
        cr.execute('select id,rrule,rdates from crm_case where id in (%s)' % read_ids)
        rrules = filter(lambda x: not x['rrule']==None, cr.dictfetchall())
        rdates = []
        if not rrules:
            return res
        result =  res + []
        for data in rrules:
            if data['rrule'] and data['rdates']: # delete 2nd condition at last
                rdates = eval(data['rdates'])
            for res_temp in res:
                if res_temp['id'] == data['id']:
                    val = res_temp
                    if rdates:
                        result.remove(val)

            for rdate in rdates:
                import re
                idval = (re.compile('\d')).findall(rdate)
                val['date'] = rdate
                id = str(val['id']).split('-')[0]
                val['id'] = id + '-' + ''.join(idval)
                val1 = val.copy()
                result += [val1]
        return result

    def copy(self, cr, uid, id, default=None, context={}):
        return super(crm_case, self).copy(cr, uid, caldevIDs2readIDs(id), default, context)

    def unlink(self, cr, uid, ids, context=None):
        #TODO: Change RRULE
        for id in ids:
            if len(str(id).split('-')) > 1:
                date_new = time.strftime("%Y-%m-%d %H:%M:%S", \
                                 time.strptime(str(str(id).split('-')[1]), "%Y%m%d%H%M%S"))
                for record in self.read(cr, uid, [caldevIDs2readIDs(id)], ['date', 'rdates', 'rrule']):
                    if record['date'] == date_new:
                        self.write(cr, uid, [caldevIDs2readIDs(id)], \
                                   {'rrule' : record['rrule'] +"\n" + str(date_new)})
            else:
                return super(crm_case, self).unlink(cr, uid, ids)

    def create(self, cr, uid, vals, context={}):
        if 'case_id' in vals:
            vals['case_id'] = caldevIDs2readIDs(vals['case_id'])
        return super(crm_case, self).create(cr, uid, vals, context)

crm_case()


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
        new_args = []
        if len(args) > 1:
            new_args = [args[0]]
            if args[1][0] == 'res_id':
                new_args.append((args[1][0], args[1][1], caldevIDs2readIDs(args[1][2])))
        if new_args:
            args = new_args
        return super(ir_attachment, self).search(cr, uid, args, offset=offset, 
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
                new_model.append((data[0], caldevIDs2readIDs(data[1])))
            else:
                new_model.append(data)
        return super(ir_values, self).set(cr, uid, key, key2, name, new_model, value, \
                                   replace, isobject, meta, preserve_user, company)

    def get(self, cr, uid, key, key2, models, meta=False, context={}, res_id_req=False, \
                    without_user=True, key2_req=True):
        new_model = []
        for data in models:
            if type(data) in (list, tuple):
                new_model.append((data[0], caldevIDs2readIDs(data[1])))
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
                val['id'] = caldevIDs2readIDs(val['id'])
        return data
    
ir_model()

class virtual_report_spool(web_services.report_spool):

    def exp_report(self, db, uid, object, ids, datas=None, context=None):
        if object == 'printscreen.list':
            return super(virtual_report_spool, self).exp_report(db, uid, object, ids, datas, context)
        new_ids = []
        for id in ids:
            new_ids.append(caldevIDs2readIDs(id))
        datas['id'] = caldevIDs2readIDs(datas['id'])
        super(virtual_report_spool, self).exp_report(db, uid, object, new_ids, datas, context)
        return super(virtual_report_spool, self).exp_report(db, uid, object, new_ids, datas, context)

virtual_report_spool()

class virtual_wizard(web_services.wizard):
    def exp_execute(self, db, uid, wiz_id, datas, action='init', context=None):
        new_ids = []
        if 'id' in datas:
            datas['id'] = caldevIDs2readIDs(datas['id'])
            for id in datas['ids']:
               new_ids.append(caldevIDs2readIDs(id))
            datas['ids'] = new_ids
        res=super(virtual_wizard, self).exp_execute(db, uid, wiz_id, datas, action, context)
        return res

virtual_wizard()