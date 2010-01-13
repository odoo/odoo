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
        'class': fields.selection([('public', 'Public'), ('private', 'Private'), \
                 ('confidential', 'Confidential')], 'Mark as'), 
        'location': fields.char('Location', size=264, help="Location of Task"), 
        'exdate': fields.text('Exception Date/Times', help="This property \
defines the list of date/time exceptions for arecurring calendar component."), 
        'exrule': fields.char('Exception Rule', size=352, help="defines a rule\
 or repeating pattern for anexception to a recurrence set"), 
        'attendee_ids': fields.many2many('calendar.attendee', 'task_attendee_rel', 'task_id', 'attendee_id', 'Attendees'), 
        'caldav_url': fields.char('Calendar URL', size=34), 
        'rrule': fields.char('Recurrent Rule', size=124), 
        'rrule_type': fields.selection([('none', 'None'), ('daily', 'Daily'), \
                    ('weekly', 'Weekly'), ('monthly', 'Monthly'), \
                    ('yearly', 'Yearly'), ('custom', 'Custom')], 'Recurrency'), 
        'alarm_id': fields.many2one('res.alarm', 'Alarm'), 
        'caldav_alarm_id': fields.many2one('calendar.alarm', 'Alarm'), 
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
        'location': {'field': 'location', 'type': 'text'}, 
        'organizer': {'field': 'partner_id', 'type': 'many2one', 'object': 'res.partner'}, 
        'percent': {'field': 'progress_rate', 'type': 'int'}, 
        'priority': {'field': 'priority', 'type': 'text'}, 
#        'recurid': {'field': 'field', 'type': 'text'},
        'seq': {'field': 'sequence', 'type': 'text'}, 
        'status': {'field': 'state', 'type': 'selection', \
                            'mapping': {'needs-action': 'draft', \
                              'completed': 'done', 'in-process': 'open', \
                              'cancelled': 'cancelled'}}, 
        'summary': {'field': 'name', 'type': 'text'}, 
        'uid': {'field': 'id', 'type': 'int'}, 
        'url': {'field': 'caldav_url', 'type': 'text'}, 
#        'attach': {'field': 'field', 'type': 'text'},
        'attendee': {'field': 'attendee_ids', 'type': 'many2many', 'object': 'calendar.attendee'}, 
        'comment': {'field': 'notes', 'type': 'text'}, 
#        'contact': {'field': 'field', 'type': 'text'},
        'exdate': {'field':'exdate', 'type':'datetime'}, 
        'exrule': {'field':'exrule', 'type':'text'}, 
#        'rstatus': {'field': 'field', 'type': 'text'},
#        'related': {'field': 'field', 'type': 'text'},
#        'resources': {'field': 'field', 'type': 'text'},
#        'rdate': {'field': 'field', 'type': 'text'},
        'rrule': {'field': 'rrule', 'type': 'text'}, 
        'valarm': {'field':'caldav_alarm_id', 'type':'many2one', 'object': 'calendar.alarm'}, 
                     }

    def onchange_rrule_type(self, cr, uid, ids, type, *args, **argv):
        if type == 'none':
            return {'value': {'rrule': ''}}
        if type == 'custom':
            return {}
        rrule = self.pool.get('calendar.custom.rrule')
        rrulestr = rrule.compute_rule_string(cr, uid, {'freq': type.upper(), \
                                 'interval': 1})
        return {'value': {'rrule': rrulestr}}

    def import_cal(self, cr, uid, data, context={}):
        file_content = base64.decodestring(data)
        todo_obj = self.pool.get('basic.calendar.todo')
        todo_obj.__attribute__.update(self.__attribute__)

        attendee_obj = self.pool.get('basic.calendar.attendee')
        crm_attendee = self.pool.get('calendar.attendee')
        attendee_obj.__attribute__.update(crm_attendee.__attribute__)

        alarm_obj = self.pool.get('basic.calendar.alarm')
        crm_alarm = self.pool.get('calendar.alarm')
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
                # Converts timedelta into hours
                hours = (val['planned_hours'].seconds / float(3600)) + \
                                        (val['planned_hours'].days * 24)
                val['planned_hours'] = hours
            is_exists = common.uid2openobjectid(cr, val['id'], self._name)
            val.pop('id')
            if is_exists:
                self.write(cr, uid, [is_exists], val)
            else:
                task_id = self.create(cr, uid, val)
        return {'count': len(vals)}

    def export_cal(self, cr, uid, ids, context={}):
        task_datas = self.read(cr, uid, ids, [], context ={'read': True})
        tasks = []
        for task in task_datas:
            if task.get('planned_hours', None) and task.get('date_deadline', None):
                task.pop('planned_hours')
            tasks.append(task)
        todo_obj = self.pool.get('basic.calendar.todo')
        todo_obj.__attribute__.update(self.__attribute__)

        attendee_obj = self.pool.get('basic.calendar.attendee')
        attendee = self.pool.get('calendar.attendee')
        attendee_obj.__attribute__.update(attendee.__attribute__)

        alarm_obj = self.pool.get('basic.calendar.alarm')
        alarm = self.pool.get('calendar.alarm')
        alarm_obj.__attribute__.update(alarm.__attribute__)

        ical = todo_obj.export_ical(cr, uid, tasks, {'model': 'project.task'})
        caendar_val = ical.serialize()
        caendar_val = caendar_val.replace('"', '').strip()
        return caendar_val

    def get_recurrent_ids(self, cr, uid, select, base_start_date, base_until_date, limit=100):
        if not limit:
            limit = 100
        if isinstance(select, (str, int, long)):
            ids = [select]
        else:
            ids = select
        result = []
        if ids and (base_start_date or base_until_date):
            cr.execute("select t.id, t.rrule, t.date_start, t.exdate \
                            from project_task t\
                         where t.id in ("+ ','.join(map(lambda x: str(x), ids))+")")

            count = 0
            for data in cr.dictfetchall():
                start_date = base_start_date and datetime.strptime(base_start_date, "%Y-%m-%d") or False
                until_date = base_until_date and datetime.strptime(base_until_date, "%Y-%m-%d") or False
                if count > limit:
                    break
                event_date = datetime.strptime(data['date_start'], "%Y-%m-%d %H:%M:%S")
                if start_date and start_date <= event_date:
                    start_date = event_date
                if not data['rrule']:
                    if start_date and event_date < start_date:
                        continue
                    if until_date and event_date > until_date:
                        continue
                    idval = common.real_id2caldav_id(data['id'], data['date_start'])
                    result.append(idval)
                    count += 1
                else:
                    exdate = data['exdate'] and data['exdate'].split(',') or []
                    event_obj = self.pool.get('basic.calendar.event')
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
                    start_date = datetime.strptime(data['date_start'], "%Y-%m-%d %H:%M:%S")
                    rdates = event_obj.get_recurrent_dates(str(new_rrule_str), exdate, start_date)
                    for rdate in rdates:
                        r_date = datetime.strptime(rdate, "%Y-%m-%d %H:%M:%S")
                        if start_date and r_date < start_date:
                            continue
                        if until_date and r_date > until_date:
                            continue
                        idval = common.real_id2caldav_id(data['id'], rdate)
                        result.append(idval)
                        count += 1
        if result:
            ids = result
        if isinstance(select, (str, int, long)):
            return ids and ids[0] or False
        return ids

    def search(self, cr, uid, args, offset=0, limit=100, order=None, 
            context=None, count=False):
        args_without_date = []
        start_date = False
        until_date = False
        for arg in args:
            if arg[0] not in ('date_start', unicode('date_start')):
                args_without_date.append(arg)
            else:
                if arg[1] in ('>', '>='):
                    start_date = arg[2]
                elif arg[1] in ('<', '<='):
                    until_date = arg[2]
        res = super(project_task, self).search(cr, uid, args_without_date, offset, 
                limit, order, context, count)
        return self.get_recurrent_ids(cr, uid, res, start_date, until_date, limit)

    def read(self, cr, uid, ids, fields=None, context={}, load='_classic_read'):
        if isinstance(ids, (str, int, long)):
            select = [ids]
        else:
            select = ids
        select = map(lambda x: (x, common.caldav_id2real_id(x)), select)
        result = []
        if fields and 'date_start' not in fields:
            fields.append('date_start')
        for caldav_id, real_id in select:
            res = super(project_task, self).read(cr, uid, real_id, fields=fields, context=context, load=load)
            ls = common.caldav_id2real_id(caldav_id, with_date=True)
            if not isinstance(ls, (str, int, long)) and len(ls) >= 2:
                res['date_start'] = ls[1]
            res['id'] = caldav_id

            result.append(res)
        if isinstance(ids, (str, int, long)):
            return result and result[0] or False
        return result

    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        if isinstance(ids, (str, int, long)):
            select = [ids]
        else:
            select = ids
        new_ids = []
        for id in select:
            id = common.caldav_id2real_id(id)
            if not id in new_ids:
                new_ids.append(id)
        res = super(project_task, self).write(cr, uid, new_ids, vals, context=context)
        return res

    def browse(self, cr, uid, ids, context=None, list_class=None, fields_process={}):
        if isinstance(ids, (str, int, long)):
            select = [ids]
        else:
            select = ids
        select = map(lambda x:common.caldav_id2real_id(x), select)
        res = super(project_task, self).browse(cr, uid, select, context, list_class, fields_process)
        if isinstance(ids, (str, int, long)):
            return res and res[0] or False
        return res

    def copy(self, cr, uid, id, default=None, context={}):
        return super(project_task, self).copy(cr, uid, common.caldav_id2real_id(id), default, context)

    def unlink(self, cr, uid, ids, context=None):
        for id in ids:
            if len(str(id).split('-')) > 1:
                date_new = time.strftime("%Y-%m-%d %H:%M:%S", \
                                 time.strptime(str(str(id).split('-')[1]), "%Y%m%d%H%M%S"))
                for record in self.read(cr, uid, [common.caldav_id2real_id(id)], \
                                            ['date_start', 'rrule', 'exdate']):
                    if record['rrule']:
                        exdate = (record['exdate'] and (record['exdate'] + ',')  or '') + \
                                    ''.join((re.compile('\d')).findall(date_new)) + 'Z'
                        if record['date_start'] == date_new:
                            self.write(cr, uid, [common.caldav_id2real_id(id)], {'exdate': exdate})
                    else:
                        ids = map(lambda x:common.caldav_id2real_id(x), ids)
                        return super(project_task, self).unlink(cr, uid, ids)
            else:
                return super(project_task, self).unlink(cr, uid, ids)

project_task()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
