# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

from mx import DateTime
from mx.DateTime import now
import time

import netsvc
import pooler

from report.interface import report_rml
from report.interface import toxml

one_day = DateTime.RelativeDateTime(days=1)
month2name = [0,'Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

def hour2str(h):
    hours = int(h)
    minutes = int(round((h - hours) * 60, 0))
    return '%02dh%02d' % (hours, minutes)

class report_custom(report_rml):
    def create_xml(self, cr, uid, ids, datas, context):
        service = netsvc.LocalService('object_proxy')

        month = DateTime.DateTime(datas['form']['year'], datas['form']['month'], 1)
        
        user_xml = ['<month>%s</month>' % month2name[month.month], '<year>%s</year>' % month.year]
        
        # Public holidays
        jf_sql = """select hol.date_from, hol.date_to from hr_holidays as hol, hr_holidays_status as stat
                    where hol.holiday_status = stat.id and stat.name = 'Public holidays' """
        cr.execute(jf_sql)
        jfs = []
        jfs = [(DateTime.strptime(l['date_from'], '%Y-%m-%d %H:%M:%S'), DateTime.strptime(l['date_to'], '%Y-%m-%d %H:%M:%S')) for l in cr.dictfetchall()]
        
        for employee_id in ids:
            emp = service.execute(cr.dbname, uid, 'hr.employee', 'read', [employee_id])[0]
            stop, days_xml = False, []
            user_repr = '''
            <user>
              <name>%s</name>
              <regime>%s</regime>
              <holiday>%s</holiday>
              %%s
            </user>
            ''' % (toxml(emp['name']),emp['regime'],emp['holiday_max'])
            today, tomor = month, month + one_day
            while today.month == month.month:
                #### Work hour calculation
                sql = '''
                select action, att.name
                from hr_employee as emp inner join hr_attendance as att
                     on emp.id = att.employee_id
                where att.name between '%s' and '%s' and emp.id = %s
                order by att.name
                '''
                cr.execute(sql, (today, tomor, employee_id))
                attendences = cr.dictfetchall()
                wh = 0
                if attendences and attendences[0]['action'] == 'sign_out':
                    attendences.insert(0, {'name': today.strftime('%Y-%m-%d %H:%M:%S'), 'action':'sign_in'})
                if attendences and attendences[-1]['action'] == 'sign_in':
                    attendences.append({'name' : tomor.strftime('%Y-%m-%d %H:%M:%S'), 'action':'sign_out'})
                for att in attendences:
                    dt = DateTime.strptime(att['name'], '%Y-%m-%d %H:%M:%S')
                    if att['action'] == 'sign_out':
                        wh += (dt - ldt).hours
                    ldt = dt

                #### Theoretical workhour calculation
                sql = '''
                select t.hour_from, t.hour_to
                from hr_timesheet as t
                     inner join (hr_timesheet_group as g inner join hr_timesheet_employee_rel as rel
                                 on rel.tgroup_id = g.id and rel.emp_id = %s)
                     on t.tgroup_id = g.id
                where dayofweek = %s 
                      and date_from = (select max(date_from) 
                                       from hr_timesheet inner join (hr_timesheet_employee_rel 
                                                                        inner join hr_timesheet_group 
                                                                        on hr_timesheet_group.id = hr_timesheet_employee_rel.tgroup_id
                                                                            and hr_timesheet_employee_rel.emp_id = %s)
                                                         on hr_timesheet.tgroup_id = hr_timesheet_group.id
                                       where dayofweek = %s and date_from <= '%s') 
                order by date_from desc
                '''
                isPH = False
                for jf_start, jf_end in jfs:
                    if jf_start <= today <= jf_end:
                        isPH = True
                        break
                if isPH:
                    twh = 0
                else:
                    cr.execute(sql, (emp['id'], today.day_of_week, emp['id'], today.day_of_week, today))
                    ths = cr.dictfetchall()
                    twh = reduce(lambda x,y:x+(DateTime.strptime(y['hour_to'], '%H:%M:%S') - DateTime.strptime(y['hour_from'], '%H:%M:%S')).hours,ths, 0)

                #### Holiday calculation
                hh = 0
                sql = '''
                select hol.date_from, hol.date_to, stat.name as status
                from hr_employee as emp 
                     inner join (hr_holidays as hol left join hr_holidays_status as stat
                                 on hol.holiday_status = stat.id)
                     on emp.id = hol.employee_id
                where ((hol.date_from <= '%s' and hol.date_to >= '%s') 
                       or (hol.date_from < '%s' and hol.date_to >= '%s')
                       or (hol.date_from > '%s' and hol.date_to < '%s'))
                      and emp.id = %s
                order by hol.date_from
                '''
                cr.execute(sql, (today, today, tomor, tomor, today, tomor, employee_id))
                holidays = cr.dictfetchall()
                for hol in holidays:
                    df = DateTime.strptime(hol['date_from'], '%Y-%m-%d %H:%M:%S')
                    dt = DateTime.strptime(hol['date_to'], '%Y-%m-%d %H:%M:%S')
                    if (df.year, df.month, df.day) <= (today.year, today.month, today.day) <= (dt.year, dt.month, dt.day):
                        if (df.year, df.month, df.day) == (dt.year, dt.month, dt.day):
                            hh += (dt - df).hours
                        else:
                            hh = twh
                
                # Week xml representation
                twh, wh, hh = map(hour2str, (twh, wh, hh))
                today_xml = '<day num="%s"><th>%s</th><wh>%s</wh><hh>%s</hh></day>' % ((today - month).days+1, twh, wh, hh)
                days_xml.append(today_xml)
                today, tomor = tomor, tomor + one_day
                
            user_xml.append(user_repr % '\n'.join(days_xml))
        
        xml = '''<?xml version="1.0" encoding="UTF-8" ?>
        <report>
        %s
        </report>
        ''' % '\n'.join(user_xml)

        return xml

report_custom('report.hr.timesheet.bymonth', 'hr.employee', '', 'addons/hr/report/bymonth.xsl')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

