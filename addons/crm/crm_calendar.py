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

from caldav import common
from dateutil.rrule import *
from osv import fields, osv
import  datetime
import base64
import re
import time
import tools

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
#        'categories' : {'field':None , 'sub-field':'name', 'type':'text'}, 
        'comment' : None, 
        'contact' : None, 
        'exdate'  : {'field':'exdate', 'type':'datetime'}, 
        'exrule'  : {'field':'exrule', 'type':'text'}, 
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
        for case in self.read(cr, uid, ids, ['date', 'rrule', 'exdate', 'exrule'], context=context):
            if case['rrule']:
                rule = case['rrule']
                exdate = case['exdate'] and case['exdate'].split(',') or []
                event_obj = self.pool.get('caldav.event')
                res[case['id']] = str(event_obj.get_recurrent_dates(str(rule), exdate, case['date']))
        return res

    _columns = {
        'class' : fields.selection([('PUBLIC', 'PUBLIC'), ('PRIVATE', 'PRIVATE'), \
                 ('CONFIDENTIAL', 'CONFIDENTIAL')], 'Class'), 
        'location' : fields.function(_get_location, method=True, store=True, \
                                     string='Location', type='text'), 
        'freebusy' : fields.text('FreeBusy'), 
        'transparent' : fields.selection([('TRANSPARENT', 'TRANSPARENT'), \
                                          ('OPAQUE', 'OPAQUE')], 'Trensparent'), 
        'caldav_url' : fields.char('Caldav URL', size=34), 
        'exdate' : fields.text('Exception Date/Times', help="This property defines the list\
                 of date/time exceptions for arecurring calendar component."), 
        'exrule' : fields.text('Exception Rule', help="defines a rule or repeating pattern\
                                 for anexception to a recurrence set"), 
        'rrule' : fields.text('Recurrent Rule', readonly=True), 
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
            context = {}
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
            if alarmdata['trigger_interval'] == 'DAYS':
                delta = datetime.timedelta(days=alarmdata['trigger_duration'])
            if alarmdata['trigger_interval'] == 'HOURS':
                delta = datetime.timedelta(hours=alarmdata['trigger_duration'])
            if alarmdata['trigger_interval'] == 'MINUTES':
                delta = datetime.timedelta(minutes=alarmdata['trigger_duration'])
            alarm_time =  dtstart + (alarmdata['trigger_occurs']== 'AFTER' and delta or -delta)
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
        
        ical = event_obj.export_ical(cr, uid, crm_data, {'model': 'crm.case'})
        caendar_val = ical.serialize()
        caendar_val = caendar_val.replace('"', '').strip()
        return caendar_val

    def import_cal(self, cr, uid, ids, data, context={}):
        file_content = base64.decodestring(data)
        event_obj = self.pool.get('caldav.event')
        event_obj.__attribute__.update(self.__attribute__)

        attendee_obj = self.pool.get('caldav.attendee')
        crm_attendee = self.pool.get('crm.caldav.attendee')
        attendee_obj.__attribute__.update(crm_attendee.__attribute__)
        
        alarm_obj = self.pool.get('caldav.alarm')
        crm_alarm = self.pool.get('crm.caldav.alarm')
        alarm_obj.__attribute__.update(crm_alarm.__attribute__)
        vals = event_obj.import_ical(cr, uid, file_content)
        for val in vals:
            # TODO: Select proper section
            section_id = self.pool.get('crm.case.section').search(cr, uid, [])[0]
            val.update({'section_id' : section_id})
            is_exists = common.uid2openobjectid(cr, val['id'], self._name )
            val.pop('id')
            val.pop('create_date')
            if is_exists:
                self.write(cr, uid, [is_exists], val)
            else:
                case_id = self.create(cr, uid, val)
        return {'count': len(vals)}

    def search(self, cr, uid, args, offset=0, limit=None, order=None, 
            context=None, count=False):
        res = super(crm_case, self).search(cr, uid, args, offset, 
                limit, order, context, count)
        return res

    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        new_ids = []
        for id in ids:
            id = common.caldevIDs2readIDs(id)
            if not id in new_ids:
                new_ids.append(id)
        if 'case_id' in vals :
            vals['case_id'] = common.caldevIDs2readIDs(vals['case_id'])
        res = super(crm_case, self).write(cr, uid, new_ids, vals, context=context)
        return res

    def browse(self, cr, uid, select, context=None, list_class=None, fields_process={}):
        if not isinstance(select, list): select = [select]
        select = map(lambda x:common.caldevIDs2readIDs(x), select)
        return super(crm_case, self).browse(cr, uid, select, context, list_class, fields_process)

    def read(self, cr, uid, ids, fields=None, context={},  load='_classic_read'):
        """         logic for recurrent event
         example : 123-20091111170822"""
        if context and context.has_key('read'):
            return super(crm_case, self).read(cr, uid, ids, fields=fields, context=context, \
                                              load=load)
        if not type(ids) == list :
            # Called from code
            return super(crm_case, self).read(cr, uid, common.caldevIDs2readIDs(ids), \
                                                      fields=fields, context=context, load=load)
        else:
            ids = map(lambda x:common.caldevIDs2readIDs(x), ids)
        fields.append('date')
        res = super(crm_case, self).read(cr, uid, ids, fields=fields, context=context, load=load)
        read_ids = ",".join([str(x) for x in ids])
        if not read_ids:
            return []
        cr.execute('select id,rrule,rdates from crm_case where id in (%s)' % read_ids)
        rrules = filter(lambda x: not x['rrule']==None, cr.dictfetchall())
        rdates = []
        if not rrules:
            for ress in res:
                strdate = ''.join((re.compile('\d')).findall(ress['date']))
                idval = str(common.caldevIDs2readIDs(ress['id'])) + '-' + strdate
                ress['id'] = idval
            return res
        result =  res + []
        for data in rrules:
            if data['rrule'] and data['rdates']:
                rdates = eval(data['rdates'])
            for res_temp in res:
                if res_temp['id'] == data['id']:
                    val = res_temp
                    if rdates:
                        result.remove(val)
                else:
                    strdate = ''.join((re.compile('\d')).findall(res_temp['date']))
                    idval = str(common.caldevIDs2readIDs(res_temp['id'])) + '-' + strdate
                    res_temp['id'] = idval

            for rdate in rdates:
                idval = (re.compile('\d')).findall(rdate)
                val['date'] = rdate
                id = str(val['id']).split('-')[0]
                val['id'] = id + '-' + ''.join(idval)
                val1 = val.copy()
                result += [val1]
        return result

    def copy(self, cr, uid, id, default=None, context={}):
        return super(crm_case, self).copy(cr, uid, common.caldevIDs2readIDs(id), \
                                                          default, context)

    def unlink(self, cr, uid, ids, context=None):
        for id in ids:
            if len(str(id).split('-')) > 1:
                date_new = time.strftime("%Y-%m-%d %H:%M:%S", \
                                 time.strptime(str(str(id).split('-')[1]), "%Y%m%d%H%M%S"))
                for record in self.read(cr, uid, [common.caldevIDs2readIDs(id)], \
                                            ['date', 'rdates', 'rrule', 'exdate']):
                    if record['rrule']:
                        exdate = (record['exdate'] and (record['exdate'] + ',' )  or '') + \
                                    ''.join((re.compile('\d')).findall(date_new)) + 'Z'
                        if record['date'] == date_new:
                            self.write(cr, uid, [common.caldevIDs2readIDs(id)], {'exdate' : exdate})
                    else:
                        ids = map(lambda x:common.caldevIDs2readIDs(x), ids)
                        return super(crm_case, self).unlink(cr, uid, common.caldevIDs2readIDs(ids))
            else:
                return super(crm_case, self).unlink(cr, uid, ids)

    def create(self, cr, uid, vals, context={}):
        if 'case_id' in vals:
            vals['case_id'] = common.caldevIDs2readIDs(vals['case_id'])
        return super(crm_case, self).create(cr, uid, vals, context)

crm_case()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: