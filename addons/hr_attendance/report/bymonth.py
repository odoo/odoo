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
        
        for employee_id in ids:
            emp = service.execute(cr.dbname, uid, 'hr.employee', 'read', [employee_id])[0]
            stop, days_xml = False, []
            user_repr = '''
            <user>
              <name>%s</name>
              %%s
            </user>
            ''' % (toxml(emp['name']))
            today, tomor = month, month + one_day
            while today.month == month.month:
                #### Work hour calculation
                sql = '''
                select action, att.name
                from hr_employee as emp inner join hr_attendance as att
                     on emp.id = att.employee_id
                where att.name between %s and %s and emp.id = %s
                order by att.name
                '''
                cr.execute(sql, (today.strftime('%Y-%m-%d %H:%M:%S'), tomor.strftime('%Y-%m-%d %H:%M:%S'), employee_id))
                attendences = cr.dictfetchall()
                wh = 0
                # Fake sign ins/outs at week ends, to take attendances across week ends into account
                if attendences and attendences[0]['action'] == 'sign_out':
                    attendences.insert(0, {'name': today.strftime('%Y-%m-%d %H:%M:%S'), 'action':'sign_in'})
                if attendences and attendences[-1]['action'] == 'sign_in':
                    attendences.append({'name' : tomor.strftime('%Y-%m-%d %H:%M:%S'), 'action':'sign_out'})
                # sum up the attendances' durations
                for att in attendences:
                    dt = DateTime.strptime(att['name'], '%Y-%m-%d %H:%M:%S')
                    if att['action'] == 'sign_out':
                        wh += (dt - ldt).hours
                    ldt = dt
                
                # Week xml representation
                wh = hour2str(wh)
                today_xml = '<day num="%s"><wh>%s</wh></day>' % ((today - month).days+1, wh)
                days_xml.append(today_xml)
                today, tomor = tomor, tomor + one_day
                
            user_xml.append(user_repr % '\n'.join(days_xml))
        
        xml = '''<?xml version="1.0" encoding="UTF-8" ?>
        <report>
        %s
        </report>
        ''' % '\n'.join(user_xml)

        return xml

report_custom('report.hr.attendance.bymonth', 'hr.employee', '', 'addons/hr_attendance/report/bymonth.xsl')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

