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

import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import netsvc
import pooler

from report.interface import report_rml
from report.interface import toxml

from report import report_sxw
from tools import ustr

one_day = relativedelta(days=1)
month2name = [0, 'January', 'February', 'March', 'April', 'May', 'Jun', 'July', 'August', 'September', 'October', 'November', 'December']

def hour2str(h):
    hours = int(h)
    minutes = int(round((h - hours) * 60, 0))
    return '%02dh%02d' % (hours, minutes)

def lengthmonth(year, month):
    if month == 2 and ((year % 4 == 0) and ((year % 100 != 0) or (year % 400 == 0))):
        return 29
    return [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]

class report_custom(report_rml):

    def create_xml(self, cr, uid, ids, datas, context=None):
        obj_emp = pooler.get_pool(cr.dbname).get('hr.employee')
        if context is None:
            context = {}
        month = datetime(datas['form']['year'], datas['form']['month'], 1)
        emp_ids = context.get('active_ids', [])
        user_xml = ['<month>%s</month>' % month2name[month.month], '<year>%s</year>' % month.year]
        if emp_ids:
            for emp in obj_emp.read(cr, uid, emp_ids, ['name']):
                stop, days_xml = False, []
                user_repr = '''
                <user>
                  <name>%s</name>
                  %%s
                </user>
                ''' % (ustr(toxml(emp['name'])))
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
                    cr.execute(sql, (today.strftime('%Y-%m-%d %H:%M:%S'), tomor.strftime('%Y-%m-%d %H:%M:%S'), emp['id']))
                    attendences = cr.dictfetchall()
                    wh = 0.0
                    # Fake sign ins/outs at week ends, to take attendances across week ends into account
                    if attendences and attendences[0]['action'] == 'sign_out':
                        attendences.insert(0, {'name': today.strftime('%Y-%m-%d %H:%M:%S'), 'action':'sign_in'})
                    if attendences and attendences[-1]['action'] == 'sign_in':
                        attendences.append({'name': tomor.strftime('%Y-%m-%d %H:%M:%S'), 'action':'sign_out'})
                    # sum up the attendances' durations
                    ldt = None
                    for att in attendences:
                        dt = datetime.strptime(att['name'], '%Y-%m-%d %H:%M:%S')
                        if ldt and att['action'] == 'sign_out':
                            wh += (float((dt - ldt).seconds)/60/60)
                        else:
                            ldt = dt
                    # Week xml representation
                    wh = hour2str(wh)
                    today_xml = '<day num="%s"><wh>%s</wh></day>' % ((today - month).days+1, (wh))
                    dy=(today - month).days+1
                    days_xml.append(today_xml)
                    today, tomor = tomor, tomor + one_day
                user_xml.append(user_repr % '\n'.join(days_xml))

        rpt_obj = pooler.get_pool(cr.dbname).get('hr.employee')
        rml_obj=report_sxw.rml_parse(cr, uid, rpt_obj._name,context)
        header_xml = '''
        <header>
        <date>%s</date>
        <company>%s</company>
        </header>
        ''' % (str(rml_obj.formatLang(time.strftime("%Y-%m-%d"),date=True))+' ' + str(time.strftime("%H:%M")),pooler.get_pool(cr.dbname).get('res.users').browse(cr,uid,uid).company_id.name)

        first_date = str(month)
        som = datetime.strptime(first_date, '%Y-%m-%d %H:%M:%S')
        eom = som + timedelta(int(dy)-1)
        day_diff=eom-som
        date_xml=[]
        cell=1
        date_xml.append('<days>')
        if day_diff.days>=30:
            date_xml += ['<dayy number="%d" name="%s" cell="%d"/>' % (x, som.replace(day=x).strftime('%a'),x-som.day+1) for x in range(som.day, lengthmonth(som.year, som.month)+1)]
        else:
            if day_diff.days>=(lengthmonth(som.year, som.month)-som.day):
                date_xml += ['<dayy number="%d" name="%s" cell="%d"/>' % (x, som.replace(day=x).strftime('%a'),x-som.day+1) for x in range(som.day, lengthmonth(som.year, som.month)+1)]
            else:
                date_xml += ['<dayy number="%d" name="%s" cell="%d"/>' % (x, som.replace(day=x).strftime('%a'),x-som.day+1) for x in range(som.day, eom.day+1)]
        cell=x-som.day+1
        day_diff1=day_diff.days-cell+1
        width_dict={}
        month_dict={}
        i=1
        j=1
        year=som.year
        month=som.month
        month_dict[j]=som.strftime('%B')
        width_dict[j]=cell

        while day_diff1>0:
            if month+i<=12:
                if day_diff1 > lengthmonth(year,i+month): # Not on 30 else you have problems when entering 01-01-2009 for example
                    som1=datetime.date(year,month+i,1)
                    date_xml += ['<dayy number="%d" name="%s" cell="%d"/>' % (x, som1.replace(day=x).strftime('%a'),cell+x) for x in range(1, lengthmonth(year,i+month)+1)]
                    i=i+1
                    j=j+1
                    month_dict[j]=som1.strftime('%B')
                    cell=cell+x
                    width_dict[j]=x
                else:
                    som1=datetime.date(year,month+i,1)
                    date_xml += ['<dayy number="%d" name="%s" cell="%d"/>' % (x, som1.replace(day=x).strftime('%a'),cell+x) for x in range(1, eom.day+1)]
                    i=i+1
                    j=j+1
                    month_dict[j]=som1.strftime('%B')
                    cell=cell+x
                    width_dict[j]=x
                day_diff1=day_diff1-x
            else:
                years=year+1
                year=years
                month=0
                i=1
                if day_diff1>=30:
                    som1=datetime.date(years,i,1)
                    date_xml += ['<dayy number="%d" name="%s" cell="%d"/>' % (x, som1.replace(day=x).strftime('%a'),cell+x) for x in range(1, lengthmonth(years,i)+1)]
                    i=i+1
                    j=j+1
                    month_dict[j]=som1.strftime('%B')
                    cell=cell+x
                    width_dict[j]=x
                else:
                    som1=datetime.date(years,i,1)
                    i=i+1
                    j=j+1
                    month_dict[j]=som1.strftime('%B')
                    date_xml += ['<dayy number="%d" name="%s" cell="%d"/>' % (x, som1.replace(day=x).strftime('%a'),cell+x) for x in range(1, eom.day+1)]
                    cell=cell+x
                    width_dict[j]=x
                day_diff1=day_diff1-x
        date_xml.append('</days>')
        date_xml.append('<cols>3.5cm%s</cols>\n' % (',0.74cm' * (int(dy))))
        xml = '''<?xml version="1.0" encoding="UTF-8" ?>
        <report>
        %s
        %s
        %s
        </report>
        ''' % (header_xml,'\n'.join(user_xml),date_xml)
        return xml

report_custom('report.hr.attendance.bymonth', 'hr.employee', '', 'addons/hr_attendance/report/bymonth.xsl')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
