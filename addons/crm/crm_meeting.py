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
from datetime import datetime, timedelta
from dateutil import parser
from osv import fields, osv
from tools.translate import _
import base64
import re
import time
import tools

class crm_meeting_categ(osv.osv):
    _name = "crm.meeting.categ"
    _description = "Category of Meetings"
    _columns = {
        'name': fields.char('Meeting Category Name', size=64, required=True, \
                                 translate=True), 
        'probability': fields.float('Probability (%)', required=True), 
        'section_id': fields.many2one('crm.case.section', 'Case Section'), 
    }
    _defaults = {
        'probability': lambda *args: 0.0
    }
crm_meeting_categ()

class crm_meeting(osv.osv):
    _name = 'crm.meeting'
    _description = "Meeting Cases"
    _order = "id desc"
    _inherit = "crm.case"

    __attribute__ = {
        'class': {'field': 'class', 'type': 'selection'}, 
        'created': {'field': 'create_date', 'type': 'datetime'}, 
        'description': {'field': 'description', 'type': 'text'}, 
        'dtstart': {'field': 'date', 'type': 'datetime'}, 
        'location': {'field': 'location', 'type': 'text'}, 
        #'organizer': {'field': 'partner_id', 'sub-field': 'name', 'type': 'many2one'},
        'priority': {'field': 'priority', 'type': 'int'}, 
        'dtstamp': {'field': 'date', 'type': 'datetime'}, 
        'seq': None, 
        'status': {'field': 'state', 'type': 'selection', 'mapping': \
                                {'tentative': 'draft', 'confirmed': 'open', \
                                'cancelled': 'cancel'}}, 
        'summary': {'field': 'name', 'type': 'text'}, 
        'transp': {'field': 'transparent', 'type': 'text'}, 
        'uid': {'field': 'id', 'type': 'text'}, 
        'url': {'field': 'caldav_url', 'type': 'text'}, 
        'recurid': None, 
#        'attach': {'field': 'attachment_ids', 'sub-field': 'datas', 'type': 'list'},
        'attendee': {'field': 'attendee_ids', 'type': 'many2many', 'object': 'crm.caldav.attendee'}, 
        'categories': {'field': 'categ_id', 'type': 'many2one', 'object': 'crm.meeting.categ'}, 
        'comment': None, 
        'contact': None, 
        'exdate': {'field': 'exdate', 'type': 'datetime'}, 
        'exrule': {'field': 'exrule', 'type': 'text'}, 
        'rstatus': None, 
        'related': None, 
        'resources': None, 
        'rdate': None, 
        'rrule': {'field': 'rrule', 'type': 'text'}, 
        'x-openobject-model': {'value': _name, 'type': 'text'}, 
        'dtend': {'field': 'date_deadline', 'type': 'datetime'}, 
        'valarm': {'field': 'caldav_alarm_id', 'type': 'many2one', 'object': 'calendar.alarm'}, 
    }

    def _get_duration(self, cr, uid, ids, name, arg, context):
        res = {}
        for meeting in self.browse(cr, uid, ids, context=context):
            start = datetime.strptime(meeting.date, "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(meeting.date_deadline[:19], "%Y-%m-%d %H:%M:%S")
            diff = end - start
            duration =  float(diff.days)* 24 + (float(diff.seconds) / 3600)
            res[meeting.id] = round(duration, 2)
        return res

    def _set_duration(self, cr, uid, id, name, value, arg, context):
        meeting = self.browse(cr, uid, id, context=context)
        start = datetime.strptime(meeting.date, "%Y-%m-%d %H:%M:%S")
        end = start + timedelta(hours=value)
        cr.execute("UPDATE crm_meeting set date_deadline='%s' \
                        where id=%s"% (end.strftime("%Y-%m-%d %H:%M:%S"), id))
        return True

    def onchange_rrule_type(self, cr, uid, ids, type, *args, **argv):
        if type == 'none':
            return {'value': {'rrule': ''}}
        if type == 'custom':
            return {}
        rrule = self.pool.get('calendar.custom.rrule')
        rrulestr = rrule.compute_rule_string(cr, uid, {'freq': type.upper(), \
                                 'interval': 1})
        return {'value': {'rrule': rrulestr}}

    _columns = {
        'id': fields.integer('ID', readonly=True), 
        'name': fields.char('Description', size=64, required=True), 
        'section_id': fields.many2one('crm.case.section', 'Section', select=True, help='Section to which Case belongs to. Define Responsible user and Email \
account for mail gateway.'), 
        'priority': fields.selection([('5','Lowest'),
                                                    ('4','Low'),
                                                    ('3','Normal'),
                                                    ('2','High'),
                                                    ('1','Highest')
                                                    ], 'Priority'), 
        'date': fields.datetime('Date'), 
        'date_deadline': fields.datetime('Deadline'), 
        'duration': fields.function(_get_duration, method=True, \
                                    fnct_inv=_set_duration, string='Duration'), 
        'categ_id': fields.many2one('crm.meeting.categ', 'Category', \
            domain="[('section_id','=',section_id)]", \
            help='Category related to the section.Subdivide the CRM cases \
independently or section-wise.'), 
        'description': fields.text('Your action'), 
        'user_id': fields.many2one('res.users', 'Responsible'), 
        'class': fields.selection([('public', 'Public'), ('private', 'Private'), \
                 ('confidential', 'Confidential')], 'Mark as'), 
        'location': fields.char('Location', size=264, help="Location of Meeting"), 
        'show_as': fields.selection([('free', 'Free'), \
                                  ('busy', 'Busy')], 
                                   'Show as'), 
        'caldav_url': fields.char('Caldav URL', size=264), 
        'exdate': fields.text('Exception Date/Times', help="This property \
defines the list of date/time exceptions for arecurring calendar component."), 
        'exrule': fields.char('Exception Rule', size=352, help="defines a \
rule or repeating pattern for anexception to a recurrence set"), 
        'rrule': fields.char('Recurrent Rule', size=124), 
        'rrule_type': fields.selection([('none', 'None'), ('daily', 'Daily'), \
                            ('weekly', 'Weekly'), ('monthly', 'Monthly'), \
                            ('yearly', 'Yearly'), ('custom', 'Custom')], 'Recurrency'), 
        'attendee_ids': fields.many2many('calendar.attendee', 'crm_attendee_rel', 'case_id', 'attendee_id', 'Attendees'), 
        'alarm_id': fields.many2one('res.alarm', 'Alarm'), 
        'caldav_alarm_id': fields.many2one('calendar.alarm', 'Alarm'), 
    }

    _defaults = {
         'class': lambda *a: 'public', 
         'show_as': lambda *a: 'busy', 
    }

    def do_alarm_create(self, cr, uid, ids, context={}):
        alarm_obj = self.pool.get('calendar.alarm')
        model_obj = self.pool.get('ir.model')
        model_id = model_obj.search(cr, uid, [('model', '=', self._name)])[0]

        for meeting in self.browse(cr, uid, ids):
            basic_alarm = meeting.alarm_id
            self.do_alarm_unlink(cr, uid, [meeting.id])
            if basic_alarm:
                vals = {
                    'action': 'display', 
                    'description': meeting.description, 
                    'name': meeting.name, 
                    'attendee_ids': [(6, 0, map(lambda x:x.id, meeting.attendee_ids))], 
                    'trigger_related': basic_alarm.trigger_related, 
                    'trigger_duration': basic_alarm.trigger_duration, 
                    'trigger_occurs': basic_alarm.trigger_occurs, 
                    'trigger_interval': basic_alarm.trigger_interval, 
                    'duration': basic_alarm.duration, 
                    'repeat': basic_alarm.repeat, 
                    'state': 'run', 
                    'event_date': meeting.date, 
                    'res_id': meeting.id, 
                    'model_id': model_id, 
                    'user_id': uid
                 }
                alarm_id = alarm_obj.create(cr, uid, vals)
                cr.execute('Update crm_meeting set caldav_alarm_id=%s, \
                    alarm_id=%s where id=%s' % (alarm_id, basic_alarm.id, meeting.id))
        cr.commit()
        return True

    def do_alarm_unlink(self, cr, uid, ids, context={}):
        alarm_obj = self.pool.get('calendar.alarm')
        model_obj = self.pool.get('ir.model')
        model_id = model_obj.search(cr, uid, [('model', '=', self._name)])[0]
        for meeting in self.browse(cr, uid, ids):
            alarm_ids = alarm_obj.search(cr, uid, [('model_id', '=', model_id), ('res_id', '=', meeting.id)])
            if alarm_ids and len(alarm_ids):
                alarm_obj.unlink(cr, uid, alarm_ids)
                cr.execute('Update crm_meeting set caldav_alarm_id=NULL, \
                               alarm_id=NULL  where id=%s' % (meeting.id))
        cr.commit()
        return True

    def on_change_duration(self, cr, uid, id, date, duration):
        if not date:
            return {}
        start_date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        if duration >= 0:
            end = start_date + datetime.timedelta(hours=duration)
        if duration < 0:
            raise osv.except_osv(_('Warning !'), 
                    _('You can not set negative Duration.'))
        res = {'value': {'date_deadline': end.strftime('%Y-%m-%d %H:%M:%S')}}
        return res

    def export_cal(self, cr, uid, ids, context={}):
        ids = map(lambda x: common.caldav_id2real_id(x), ids)
        crm_data = self.read(cr, uid, ids)
        event_obj = self.pool.get('basic.calendar.event')
        event_obj.__attribute__.update(self.__attribute__)
        ical = event_obj.export_ical(cr, uid, crm_data, {'model': self._name})
        cal_val = ical.serialize()
        cal_val = cal_val.replace('"', '').strip()
        return cal_val

    def import_cal(self, cr, uid, data, context={}):
        file_content = base64.decodestring(data)
        event_obj = self.pool.get('basic.calendar.event')
        event_obj.__attribute__.update(self.__attribute__)
        
        attendee_obj = self.pool.get('basic.calendar.attendee')
        attendee = self.pool.get('calendar.attendee')
        attendee_obj.__attribute__.update(attendee.__attribute__)
        
        alarm_obj = self.pool.get('basic.calendar.alarm')
        alarm = self.pool.get('calendar.alarm')
        alarm_obj.__attribute__.update(alarm.__attribute__)

        vals = event_obj.import_ical(cr, uid, file_content)
        ids = []
        for val in vals:
            is_exists = common.uid2openobjectid(cr, val['id'], self._name)
            if val.has_key('create_date'): val.pop('create_date')
            val['caldav_url'] = context.get('url') or ''
            val.pop('id')
            if is_exists:
                self.write(cr, uid, [is_exists], val)
                ids.append(is_exists)
            else:
                case_id = self.create(cr, uid, val)
                ids.append(case_id)
        return ids

    def get_recurrent_ids(self, cr, uid, select, base_start_date, base_until_date, limit=100):
        if not limit:
            limit = 100
        if isinstance(select, (str, int, long)):
            ids = [select]
        else:
            ids = select
        result = []
        if ids and (base_start_date or base_until_date):
            cr.execute("select m.id, m.rrule, m.date, m.exdate \
                            from crm_meeting m\
                         where m.id in ("+ ','.join(map(lambda x: str(x), ids))+")")

            count = 0
            for data in cr.dictfetchall():
                start_date = base_start_date and datetime.strptime(base_start_date, "%Y-%m-%d") or False
                until_date = base_until_date and datetime.strptime(base_until_date, "%Y-%m-%d") or False
                if count > limit:
                    break
                event_date = datetime.strptime(data['date'], "%Y-%m-%d %H:%M:%S")
                if start_date and start_date <= event_date:
                    start_date = event_date
                if not data['rrule']:
                    if start_date and event_date < start_date:
                        continue
                    if until_date and event_date > until_date:
                        continue
                    idval = common.real_id2caldav_id(data['id'], data['date'])
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
                    start_date = datetime.strptime(data['date'], "%Y-%m-%d %H:%M:%S")
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
            if arg[0] not in ('date', unicode('date')):
                args_without_date.append(arg)
            else:
                if arg[1] in ('>', '>='):
                    start_date = arg[2]
                elif arg[1] in ('<', '<='):
                    until_date = arg[2]
        res = super(crm_meeting, self).search(cr, uid, args_without_date, offset, 
                limit, order, context, count)
        return self.get_recurrent_ids(cr, uid, res, start_date, until_date, limit)


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
        res = super(crm_meeting, self).write(cr, uid, new_ids, vals, context=context)
        if vals.get('alarm_id'):
            self.do_alarm_create(cr, uid, new_ids)
        return res

    def browse(self, cr, uid, ids, context=None, list_class=None, fields_process={}):
        if isinstance(ids, (str, int, long)):
            select = [ids]
        else:
            select = ids
        select = map(lambda x: common.caldav_id2real_id(x), select)
        res = super(crm_meeting, self).browse(cr, uid, select, context, list_class, fields_process)
        if isinstance(ids, (str, int, long)):
            return res and res[0] or False
        return res

    def read(self, cr, uid, ids, fields=None, context={}, load='_classic_read'):
        if isinstance(ids, (str, int, long)):
            select = [ids]
        else:
            select = ids
        select = map(lambda x: (x, common.caldav_id2real_id(x)), select)
        result = []
        if fields and 'date' not in fields:
            fields.append('date')
        for caldav_id, real_id in select:
            res = super(crm_meeting, self).read(cr, uid, real_id, fields=fields, context=context, \
                                              load=load)
            ls = common.caldav_id2real_id(caldav_id, with_date=True)
            if not isinstance(ls, (str, int, long)) and len(ls) >= 2:
                res['date'] = ls[1]
            res['id'] = caldav_id

            result.append(res)
        if isinstance(ids, (str, int, long)):
            return result and result[0] or False
        return result

    def copy(self, cr, uid, id, default=None, context={}):
        res = super(crm_meeting, self).copy(cr, uid, common.caldav_id2real_id(id), default, context)
        self.do_alarm_create(cr, uid, [res])
        return res

    def unlink(self, cr, uid, ids, context=None):
        res = False
        for id in ids:
            ls = common.caldav_id2real_id(id)
            if not isinstance(ls, (str, int, long)) and len(ls) >= 2:
                date_new = ls[1]
                for record in self.read(cr, uid, [common.caldav_id2real_id(id)], \
                                            ['date', 'rrule', 'exdate']):
                    if record['rrule']:
                        exdate = (record['exdate'] and (record['exdate'] + ',')  or '') + \
                                    ''.join((re.compile('\d')).findall(date_new)) + 'Z'
                        if record['date'] == date_new:
                            res = self.write(cr, uid, [common.caldav_id2real_id(id)], {'exdate': exdate})
                    else:
                        ids = map(lambda x: common.caldav_id2real_id(x), ids)
                        res = super(crm_meeting, self).unlink(cr, uid, common.caldav_id2real_id(ids))
                        self.do_alarm_unlink(cr, uid, ids)
            else:
                ids = map(lambda x: common.caldav_id2real_id(x), ids)
                res = super(crm_meeting, self).unlink(cr, uid, ids)
                self.do_alarm_unlink(cr, uid, ids)
        return res

    def create(self, cr, uid, vals, context={}):
        res = super(crm_meeting, self).create(cr, uid, vals, context)
        self.do_alarm_create(cr, uid, [res])
        return res


    def msg_new(self, cr, uid, msg):
        mailgate_obj = self.pool.get('mail.gateway')
        msg_body = mailgate_obj.msg_body_get(msg)
        data = {
            'name': msg['Subject'], 
            'email_from': msg['From'], 
            'email_cc': msg['Cc'], 
            'user_id': False, 
            'description': msg_body['body'], 
            'history_line': [(0, 0, {'description': msg_body['body'], 'email': msg['From'] })], 
        }
        res = mailgate_obj.partner_get(cr, uid, msg['From'])
        if res:
            data.update(res)
        res = self.create(cr, uid, data)
        return res

crm_meeting()

class res_users(osv.osv):
    _inherit = 'res.users'
    def _get_user_avail(self, cr, uid, ids, context=None):
        current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        res = super(res_users, self)._get_user_avail(cr, uid, ids, context)
        cr.execute("SELECT m.user_id, 'busy' as status \
                    FROM crm_meeting m\
                    where m.date <= %s and m.date_deadline >= %s \
                        and m.user_id = ANY(%s) and m.show_as = %s", 
                        (current_datetime, current_datetime, ids, 'busy'))
        result = cr.dictfetchall()
        for user_data in result:
            user_id = user_data['user_id']
            status = user_data['status']
            res.update({user_id:status})
        return res
res_users()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
