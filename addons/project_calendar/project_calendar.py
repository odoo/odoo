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

from datetime import datetime
from osv import fields, osv
from service import web_services
import base64
import time
import re

def caldevIDs2readIDs(caldev_ID = None):
    if caldev_ID:
        if isinstance(caldev_ID, str):
            return int(caldev_ID.split('-')[0])
        return caldev_ID

class project_task(osv.osv):
    _inherit = "project.task"
    
    def _get_rdates(self, cr, uid, ids, name, arg, context=None):
        res = {}
        context.update({'read':True})
        for task in self.read(cr, uid, ids, ['date_start', 'rrule', 'exdate', 'exrule'], context=context):
            if task['rrule']:
                rule = task['rrule']
                if rule.upper().find('COUNT') < 0: # Temp fix, needs review
                    rule += ';COUNT=5'
                exdate = task['exdate'] and task['exdate'].split(',') or []
                todo_obj = self.pool.get('caldav.todo')
                res[task['id']] = str(todo_obj.get_recurrent_dates(str(rule), exdate, task['date_start']))
        return res

    _columns = {
                 'class': fields.selection([('PUBLIC', 'PUBLIC'), ('PRIVATE', 'PRIVATE'), \
                                             ('CONFIDENTIAL', 'CONFIDENTIAL')], 'Class'), 
                'location': fields.text('Location'), 
                'rrule': fields.text('Recurrent Rule'), 
                'exdate' : fields.text('Exception Date/Times', help="This property defines the list\
                                 of date/time exceptions for arecurring calendar component."), 
                'exrule' : fields.text('Exception Rule', help="defines a rule or repeating pattern\
                                 for anexception to a recurrence set"), 
                'rdates': fields.function(_get_rdates, method=True, string='Recurrent Dates', \
                                   store=True, type='text'), 
               'attendee_ids': fields.many2many('crm.caldav.attendee', 'task_attendee_rel', 'case_id', \
                                              'attendee_id', 'Attendees'), 
               'alarm_id': fields.many2one('crm.caldav.alarm', 'Alarm'), 
               'caldav_url': fields.char('Caldav URL', size=34), 
    }
    
    __attribute__ = {
        'class': {'field': 'class', 'type': 'text'}, 
        'completed': {'field': 'date_close', 'type': 'datetime'}, 
#        'created': {'field': 'field', 'type': 'text'}, 
        'description': {'field': 'description', 'type': 'text'}, 
#        'dtstamp': {'field': 'field', 'type': 'text'}, 
        'dtstart': {'field': 'date_start', 'type': 'datetime'}, 
        'duration': {'field': 'planned_hours', 'type': 'timedelta'}, 
        'due': {'field': 'date_deadline', 'type': 'datetime'}, 
#        'geo': {'field': 'field', 'type': 'text'}, 
#        'last-mod ': {'field': 'field', 'type': 'text'}, 
        'location': {'field': 'location', 'type': 'text'}, # To add
        'organizer': {'field': 'partner_id', 'type': 'many2one', 'object': 'res.partner'}, 
        'percent': {'field': 'progress_rate', 'type': 'int'}, 
        'priority': {'field': 'priority', 'type': 'text'}, 
#        'recurid': {'field': 'field', 'type': 'text'}, 
        'seq': {'field': 'sequence', 'type': 'text'}, 
        'status': {'field': 'state', 'type': 'selection', 'mapping': {'NEEDS-ACTION': 'draft', \
                                              'COMPLETED': 'done', 'IN-PROCESS': 'open', \
                                              'CANCELLED': 'cancelled'}}, 
        'summary': {'field': 'name', 'type': 'text'}, 
        'uid': {'field': 'id', 'type': 'int'}, 
        'url': {'field': 'caldav_url', 'type': 'text'}, # To add 
#        'attach': {'field': 'field', 'type': 'text'}, 
        'attendee': {'field': 'attendee_ids', 'type': 'many2many', 'object': 'crm.caldav.attendee'}, 
#        'categories': {'field': 'type', 'type': 'text'}, # Needs review 
        'comment': {'field': 'notes', 'type': 'text'}, 
#        'contact': {'field': 'field', 'type': 'text'}, 
        'exdate'  : {'field':'exdate', 'type':'datetime'}, 
        'exrule'  : {'field':'exrule', 'type':'text'}, 
#        'rstatus': {'field': 'field', 'type': 'text'}, 
#        'related': {'field': 'field', 'type': 'text'}, 
#        'resources': {'field': 'field', 'type': 'text'}, 
#        'rdate': {'field': 'field', 'type': 'text'}, 
        'rrule': {'field': 'rrule', 'type': 'text'}, 
        'valarm' : {'field':'alarm_id', 'type':'many2one', 'object' : 'crm.caldav.alarm'},
                     }

    def import_cal(self, cr, uid, ids, data, context={}):
        file_content = base64.decodestring(data['form']['file_path'])
        todo_obj = self.pool.get('caldav.todo')
        todo_obj.__attribute__.update(self.__attribute__)
        
        attendee_obj = self.pool.get('caldav.attendee')
        crm_attendee = self.pool.get('crm.caldav.attendee')
        attendee_obj.__attribute__.update(crm_attendee.__attribute__)
        
        alarm_obj = self.pool.get('caldav.alarm')
        crm_alarm = self.pool.get('crm.caldav.alarm')
        alarm_obj.__attribute__.update(crm_alarm.__attribute__)

        vals = todo_obj.import_ical(cr, uid, file_content)
        for val in vals:
            obj_tm = self.pool.get('res.users').browse(cr, uid, uid, context).company_id.project_time_mode_id
            if not val.has_key('planned_hours'):
                # 'Compute duration' in days
                val['planned_hours'] = 16
            else:
                # Convert timedelta into Project time unit
                val['planned_hours'] = (val['planned_hours'].seconds/float(86400) + \
                                        val['planned_hours'].days) * obj_tm.factor
            val.pop('id')
            task_id = self.create(cr, uid, val)
        return {'count': len(vals)}
    
    def export_cal(self, cr, uid, ids, context={}):
        task_data = self.read(cr, uid, ids, [], context ={'read': True})
        todo_obj = self.pool.get('caldav.todo')
        todo_obj.__attribute__.update(self.__attribute__)
        
        attendee_obj = self.pool.get('caldav.attendee')
        attendee = self.pool.get('crm.caldav.attendee')
        attendee_obj.__attribute__.update(attendee.__attribute__)
        
        alarm_obj = self.pool.get('caldav.alarm')
        alarm = self.pool.get('crm.caldav.alarm')
        alarm_obj.__attribute__.update(alarm.__attribute__)
        
        ical = todo_obj.export_ical(cr, uid, task_data)
        caendar_val = ical.serialize()
        caendar_val = caendar_val.replace('"', '').strip()
        return caendar_val

    def read(self, cr, uid, ids, fields=None, context={}, load='_classic_read'):
        """ Logic for recurrent task
                     example : 123-20091111170822"""
        if context and context.has_key('read'):
            return super(project_task, self).read(cr, uid, ids, fields, context, load)
        if not type(ids) == list :
            # Called from code
            return super(project_task, self).read(cr, uid, caldevIDs2readIDs(ids),\
                                                  fields=fields, context=context, load=load)
        else:
            ids = map(lambda x:caldevIDs2readIDs(x), ids)
        res = super(project_task, self).read(cr, uid, ids, fields=fields, context=context, load=load)
        read_ids = ",".join([str(x) for x in ids])
        if not read_ids:
            return []
        cr.execute('select id,rrule,rdates from project_task where id in (%s)' % read_ids)
        rrules = filter(lambda x: not x['rrule']==None, cr.dictfetchall())
        rdates = []
        if not rrules:
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

            for rdate in rdates:
                idval = (re.compile('\d')).findall(rdate)
                val['date_start'] = rdate
                id = str(val['id']).split('-')[0]
                val['id'] = id + '-' + ''.join(idval)
                val1 = val.copy()
                result += [val1]
        return result
    def search(self, cr, uid, args, offset=0, limit=None, order=None, 
            context=None, count=False):
        res = super(project_task, self).search(cr, uid, args, offset, 
                limit, order, context, count)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        new_ids = []
        for id in ids:
            id = caldevIDs2readIDs(id)
            if not id in new_ids:
                new_ids.append(id)
        res = super(project_task, self).write(cr, uid, new_ids, vals, context=context)
        return res

    def browse(self, cr, uid, select, context=None, list_class=None, fields_process={}):
        if not isinstance(select, list): select = [select]
        select = map(lambda x:caldevIDs2readIDs(x), select)
        return super(project_task, self).browse(cr, uid, select, context, list_class, fields_process)

    def copy(self, cr, uid, id, default=None, context={}):
        return super(project_task, self).copy(cr, uid, caldevIDs2readIDs(id), default, context)

    def unlink(self, cr, uid, ids, context=None):
        #TODO: Change RRULE
        for id in ids:
            if len(str(id).split('-')) > 1:
                date_new = time.strftime("%Y-%m-%d %H:%M:%S", \
                                 time.strptime(str(str(id).split('-')[1]), "%Y%m%d%H%M%S"))
                for record in self.read(cr, uid, [caldevIDs2readIDs(id)], \
                                            ['date', 'rdates', 'rrule', 'exdate']):
                    exdate = (record['exdate'] and (record['exdate'] + ',' )  or '') + \
                                ''.join((re.compile('\d')).findall(date_new)) + 'Z'
                    if record['date_start'] == date_new:
                        self.write(cr, uid, [caldevIDs2readIDs(id)], {'exdate' : exdate})
            else:
                return super(project_task, self).unlink(cr, uid, ids)

    def create(self, cr, uid, vals, context={}):
        if 'case_id' in vals:
            vals['case_id'] = caldevIDs2readIDs(vals['case_id'])
        return super(project_task, self).create(cr, uid, vals, context)
project_task()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
