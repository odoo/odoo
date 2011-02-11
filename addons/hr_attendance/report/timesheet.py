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


from datetime import datetime
from dateutil.relativedelta import relativedelta

import pooler
from report.interface import report_rml
from report.interface import toxml
import tools

one_week = relativedelta(days=7)
num2day = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

def to_hour(h):
    return int(h), int(round((h - int(h)) * 60, 0))

class report_custom(report_rml):

    def create_xml(self, cr, uid, ids, datas, context=None):
        obj_emp = pooler.get_pool(cr.dbname).get('hr.employee')

        start_date = datetime.strptime(datas['form']['init_date'], '%Y-%m-%d')
        end_date = datetime.strptime(datas['form']['end_date'], '%Y-%m-%d')
        first_monday = start_date - relativedelta(days=start_date.date().weekday())
        last_monday = end_date + relativedelta(days=7 - end_date.date().weekday())

        if last_monday < first_monday:
            first_monday, last_monday = last_monday, first_monday

        user_xml = []

        for employee_id in ids:
            emp = obj_emp.read(cr, uid, [employee_id], ['id', 'name'])[0]
            monday, n_monday = first_monday, first_monday + one_week
            stop, week_xml = False, []
            user_repr = '''
            <user>
              <name>%s</name>
              %%s
            </user>
            ''' % tools.ustr(toxml(emp['name']))
            while monday != last_monday:
                #### Work hour calculation
                sql = '''
                select action, att.name
                from hr_employee as emp inner join hr_attendance as att
                     on emp.id = att.employee_id
                where att.name between %s and %s and emp.id = %s
                order by att.name
                '''
                for idx in range(7):
                    cr.execute(sql, (monday.strftime('%Y-%m-%d %H:%M:%S'), (monday + relativedelta(days=idx+1)).strftime('%Y-%m-%d %H:%M:%S'), employee_id))
                    attendances = cr.dictfetchall()
                    week_wh = {}
                    # Fake sign ins/outs at week ends, to take attendances across week ends into account
                    # XXX this is wrong for the first sign-in ever and the last sign out to this date
                    if attendances and attendances[0]['action'] == 'sign_out':
                        attendances.insert(0, {'name': monday.strftime('%Y-%m-%d %H:%M:%S'), 'action': 'sign_in'})
                    if attendances and attendances[-1]['action'] == 'sign_in':
                        attendances.append({'name': n_monday.strftime('%Y-%m-%d %H:%M:%S'), 'action': 'sign_out'})
                    # sum up the attendances' durations
                    ldt = None
                    for att in attendances:
                        dt = datetime.strptime(att['name'], '%Y-%m-%d %H:%M:%S')
                        if ldt and att['action'] == 'sign_out':
                            week_wh[ldt.date().weekday()] = week_wh.get(ldt.date().weekday(), 0) + (float((dt - ldt).seconds)/3600)
                        else:
                            ldt = dt

                # Week xml representation
                week_repr = ['<week>', '<weekstart>%s</weekstart>' % monday.strftime('%Y-%m-%d'), '<weekend>%s</weekend>' % n_monday.strftime('%Y-%m-%d')]
                for idx in range(7):
                    week_repr.append('<%s>' % num2day[idx])
                    if idx in week_wh:
                        week_repr.append('<workhours>%sh%02d</workhours>' % to_hour(week_wh[idx]))
                    week_repr.append('</%s>' % num2day[idx])
                week_repr.append('<total>')
                week_repr.append('<worked>%sh%02d</worked>' % to_hour(reduce(lambda x,y:x+y, week_wh.values(), 0)))
                week_repr.append('</total>')
                week_repr.append('</week>')
                if len(week_repr) > 21: # 21 = minimal length of week_repr
                    week_xml.append('\n'.join(week_repr))

                monday, n_monday = n_monday, n_monday + one_week
            user_xml.append(user_repr % '\n'.join(week_xml))

        xml = '''<?xml version="1.0" encoding="UTF-8" ?>
        <report>
        %s
        </report>
        ''' % '\n'.join(user_xml)
        return self.post_process_xml_data(cr, uid, xml, context)

report_custom('report.hr.attendance.allweeks', 'hr.employee', '', 'addons/hr_attendance/report/timesheet.xsl')
# vim:noexpandtab:tw=0
