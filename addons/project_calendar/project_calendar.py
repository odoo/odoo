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
from datetime import datetime
from osv import fields, osv
from service import web_services
import base64
import re
import time

class project_task(osv.osv):
    _inherit = "project.task"

    _columns = {
                 'class': fields.selection([('PUBLIC', 'PUBLIC'), ('PRIVATE', 'PRIVATE'), \
                                             ('CONFIDENTIAL', 'CONFIDENTIAL')], 'Class'), 
                'location': fields.text('Location'), 
                'rrule': fields.text('Recurrent Rule'), 
                'exdate' : fields.text('Exception Date/Times', help="This property defines the list\
                                 of date/time exceptions for arecurring calendar component."), 
                'exrule' : fields.text('Exception Rule', help="defines a rule or repeating pattern\
                                 for anexception to a recurrence set"), 
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

    def import_cal(self, cr, uid, data, context={}):
        file_content = base64.decodestring(data)
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
                # 'Computes duration' in days
                start = datetime.strptime(val['date_start'], '%Y-%m-%d %H:%M:%S')
                end = datetime.strptime(val['date_deadline'], '%Y-%m-%d %H:%M:%S')
                diff = end - start
                plan = (diff.seconds/float(86400) + diff.days) * obj_tm.factor
                val['planned_hours'] = plan
            else:
                # Converts timedelta into Project time unit
                val['planned_hours'] = (val['planned_hours'].seconds/float(86400) + \
                                        val['planned_hours'].days) * obj_tm.factor

            is_exists = common.uid2openobjectid(cr, val['id'], self._name )
            val.pop('id')
            if is_exists:
                self.write(cr, uid, [is_exists], val)
            else:
                case_id = self.create(cr, uid, val)
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
        
        ical = todo_obj.export_ical(cr, uid, task_data, {'model': 'project.task'})
        caendar_val = ical.serialize()
        caendar_val = caendar_val.replace('"', '').strip()
        return caendar_val

    def read(self, cr, uid, ids, fields=None, context={},  load='_classic_read'):
        """         logic for recurrent event
         example : 123-20091111170822"""        
        if context and context.has_key('read'):
            return super(project_task, self).read(cr, uid, ids, fields=fields, context=context, \
                                              load=load)
        if not type(ids) == list :
            # Called from code
            return super(project_task, self).read(cr, uid, common.caldevIDs2readIDs(ids), \
                                                      fields=fields, context=context, load=load)
        else:
            ids = map(lambda x:common.caldevIDs2readIDs(x), ids)

        if fields and 'date_start' not in fields:
            fields.append('date_start')
        if not ids:
            return []
        result =  []
        for read_id in ids:
            res = super(project_task, self).read(cr, uid, read_id, fields=fields, context=context, load=load)
            cr.execute("""select id, rrule, date_start, exdate \
                                from project_task where id = %s""" % read_id)
            data = cr.dictfetchall()[0]
            if not data['rrule']:
                strdate = ''.join((re.compile('\d')).findall(data['date_start']))
                idval = str(common.caldevIDs2readIDs(data['id'])) + '-' + strdate
                data['id'] = idval
                res.update(data)
                result.append(res)
            else:
                exdate = data['exdate'] and data['exdate'].split(',') or []
                event_obj = self.pool.get('caldav.event')
                rdates = event_obj.get_recurrent_dates(str(data['rrule']), exdate, data['date_start'])[:10]
                for rdate in rdates:
                    val = res.copy()
                    idval = (re.compile('\d')).findall(rdate)
                    val['date_start'] = rdate
                    id = str(res['id']).split('-')[0]
                    val['id'] = id + '-' + ''.join(idval)
                    val1 = val.copy()
                    result.append(val1)
        return result

    def search(self, cr, uid, args, offset=0, limit=None, order=None, 
            context=None, count=False):
        res = super(project_task, self).search(cr, uid, args, offset, 
                limit, order, context, count)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        new_ids = []
        for id in ids:
            id = common.caldevIDs2readIDs(id)
            if not id in new_ids:
                new_ids.append(id)
        res = super(project_task, self).write(cr, uid, new_ids, vals, context=context)
        return res

    def browse(self, cr, uid, ids, context=None, list_class=None, fields_process={}):
        if isinstance(ids, (str, int, long)):
            select = [ids]
        else:
            select = ids        
        select = map(lambda x:common.caldevIDs2readIDs(x), select)
        res = super(project_task, self).browse(cr, uid, select, context, list_class, fields_process)        
        if isinstance(ids, (str, int, long)):
            return res and res[0] or False
        return res
    
    def copy(self, cr, uid, id, default=None, context={}):
        return super(project_task, self).copy(cr, uid, common.caldevIDs2readIDs(id), default, context)

    def unlink(self, cr, uid, ids, context=None):
        for id in ids:
            if len(str(id).split('-')) > 1:
                date_new = time.strftime("%Y-%m-%d %H:%M:%S", \
                                 time.strptime(str(str(id).split('-')[1]), "%Y%m%d%H%M%S"))
                for record in self.read(cr, uid, [common.caldevIDs2readIDs(id)], \
                                            ['date', 'rrule', 'exdate']):
                    if record['rrule']:
                        exdate = (record['exdate'] and (record['exdate'] + ',' )  or '') + \
                                    ''.join((re.compile('\d')).findall(date_new)) + 'Z'
                        if record['date_start'] == date_new:
                            self.write(cr, uid, [common.caldevIDs2readIDs(id)], {'exdate' : exdate})
                    else:
                        ids = map(lambda x:common.caldevIDs2readIDs(x), ids)
                        return super(project_task, self).unlink(cr, uid, ids)
            else:
                return super(project_task, self).unlink(cr, uid, ids)

    def create(self, cr, uid, vals, context={}):
        if 'case_id' in vals:
            vals['case_id'] = common.caldevIDs2readIDs(vals['case_id'])
        return super(project_task, self).create(cr, uid, vals, context)
project_task()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
