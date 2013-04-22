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

import datetime
import time

from openerp.osv import fields, osv
from openerp.report.interface import report_rml
from openerp.report.interface import toxml

from openerp import pooler
import time
from openerp.report import report_sxw
from openerp.tools import ustr
from openerp.tools.translate import _
from openerp.tools import to_xml

def lengthmonth(year, month):
    if month == 2 and ((year % 4 == 0) and ((year % 100 != 0) or (year % 400 == 0))):
        return 29
    return [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]

def strToDate(dt):
    if dt:
        dt_date=datetime.date(int(dt[0:4]),int(dt[5:7]),int(dt[8:10]))
        return dt_date
    else:
        return


def emp_create_xml(self, cr, uid, dept, holiday_type, row_id, empid, name, som, eom):
    display={}
    if dept==0:
        count=0
        p_id=pooler.get_pool(cr.dbname).get('hr.holidays').search(cr, uid, [('employee_id','in',[empid,False]), ('type', '=', 'remove')])
        ids_date = pooler.get_pool(cr.dbname).get('hr.holidays').read(cr, uid, p_id, ['date_from','date_to','holiday_status_id','state'])

        for index in range(1,61):
            diff=index-1
            current=som+datetime.timedelta(diff)

            for item in ids_date:
                if current >= strToDate(item['date_from']) and current <= strToDate(item['date_to']):
                    if item['state'] in holiday_type:
                        display[index]=item['holiday_status_id'][0]
                        count=count +1
                    else:
                        display[index]=' '
                    break
                else:
                    display[index]=' '
    else:
         for index in range(1,61):
              display[index]=' '
              count=''
              
    data_xml=['<info id="%d" number="%d" val="%s" />' % (row_id,x,display[x]) for x in range(1,len(display)+1) ]
    
    # Computing the xml
    xml = '''
    %s
    <employee row="%d" id="%d" name="%s" sum="%s">
    </employee>
    ''' % (data_xml,row_id,dept, ustr(toxml(name)),count)

    return xml

class report_custom(report_rml):
    def create_xml(self, cr, uid, ids, data, context):
        obj_dept = pooler.get_pool(cr.dbname).get('hr.department')
        obj_emp = pooler.get_pool(cr.dbname).get('hr.employee')
        depts=[]
        emp_id={}
#        done={}
        rpt_obj = pooler.get_pool(cr.dbname).get('hr.holidays')
        rml_obj=report_sxw.rml_parse(cr, uid, rpt_obj._name,context)
        cr.execute("SELECT name FROM res_company")
        res=cr.fetchone()[0]
        date_xml=[]
        date_today=time.strftime('%Y-%m-%d %H:%M:%S')
        date_xml +=['<res name="%s" today="%s" />' % (to_xml(res),date_today)]

        cr.execute("SELECT id, name, color_name FROM hr_holidays_status ORDER BY id")
        legend=cr.fetchall()
        today=datetime.datetime.today()

        first_date=data['form']['date_from']
        som = strToDate(first_date)
        eom = som+datetime.timedelta(59)
        day_diff=eom-som

        name = ''
        if len(data['form'].get('emp', ())) == 1:
            name = obj_emp.read(cr, uid, data['form']['emp'][0], ['name'])['name']

        if data['form']['holiday_type']!='both':
            type=data['form']['holiday_type']
            if data['form']['holiday_type']=='Confirmed':
                holiday_type=('confirm')
            else:
                holiday_type=('validate')
        else:
            type="Confirmed and Approved"
            holiday_type=('confirm','validate')
        date_xml.append('<from>%s</from>\n'% (str(rml_obj.formatLang(som.strftime("%Y-%m-%d"),date=True))))
        date_xml.append('<to>%s</to>\n' %(str(rml_obj.formatLang(eom.strftime("%Y-%m-%d"),date=True))))
        date_xml.append('<type>%s</type>'%(type))
        date_xml.append('<name>%s</name>'%(name))

#        date_xml=[]
        for l in range(0,len(legend)):
            date_xml += ['<legend row="%d" id="%d" name="%s" color="%s" />' % (l+1,legend[l][0],_(legend[l][1]),legend[l][2])]
        date_xml += ['<date month="%s" year="%d" />' % (som.strftime('%B'), som.year),'<days>']

        cell=1
        if day_diff.days>=30:
            date_xml += ['<dayy number="%d" name="%s" cell="%d"/>' % (x, _(som.replace(day=x).strftime('%a')),x-som.day+1) for x in range(som.day, lengthmonth(som.year, som.month)+1)]
        else:
            if day_diff.days>=(lengthmonth(som.year, som.month)-som.day):
                date_xml += ['<dayy number="%d" name="%s" cell="%d"/>' % (x, _(som.replace(day=x).strftime('%a')),x-som.day+1) for x in range(som.day, lengthmonth(som.year, som.month)+1)]
            else:
                date_xml += ['<dayy number="%d" name="%s" cell="%d"/>' % (x, _(som.replace(day=x).strftime('%a')),x-som.day+1) for x in range(som.day, eom.day+1)]

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
                    date_xml += ['<dayy number="%d" name="%s" cell="%d"/>' % (x, _(som1.replace(day=x).strftime('%a')),cell+x) for x in range(1, lengthmonth(year,i+month)+1)]
                    i=i+1
                    j=j+1
                    month_dict[j]=som1.strftime('%B')
                    cell=cell+x
                    width_dict[j]=x

                else:
                    som1=datetime.date(year,month+i,1)
                    date_xml += ['<dayy number="%d" name="%s" cell="%d"/>' % (x, _(som1.replace(day=x).strftime('%a')),cell+x) for x in range(1, eom.day+1)]
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
                    date_xml += ['<dayy number="%d" name="%s" cell="%d"/>' % (x, _(som1.replace(day=x).strftime('%a')),cell+x) for x in range(1, lengthmonth(years,i)+1)]
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
                    date_xml += ['<dayy number="%d" name="%s" cell="%d"/>' % (x, _(som1.replace(day=x).strftime('%a')),cell+x) for x in range(1, eom.day+1)]
                    cell=cell+x
                    width_dict[j]=x

                day_diff1=day_diff1-x

        date_xml.append('</days>')
        date_xml.append('<cols>3.5cm%s,0.4cm</cols>\n' % (',0.4cm' * (60)))
        date_xml = ''.join(date_xml)

        st='<cols_months>3.5cm'
        for m in range(1,len(width_dict)+1):
            st+=',' + str(0.4 *width_dict[m])+'cm'
        st+=',0.4cm</cols_months>\n'

        months_xml =['<months  number="%d" name="%s"/>' % (x, _(month_dict[x])) for x in range(1,len(month_dict)+1) ]
        months_xml.append(st)
        
        emp_xml=''
        row_id=1
        
        if data['model']=='hr.employee':
            for id in data['form']['emp']:
                 items = obj_emp.read(cr, uid, id, ['id','name'])
                 
                 emp_xml += emp_create_xml(self, cr, uid, 0, holiday_type, row_id, items['id'], items['name'], som, eom)
                 row_id = row_id +1

        elif data['model']=='ir.ui.menu':
            for id in data['form']['depts']:
                dept = obj_dept.browse(cr, uid, id, context=context)
                cr.execute("""SELECT id FROM hr_employee \
                WHERE department_id = %s""", (id,))
                emp_ids = [x[0] for x in cr.fetchall()]
                if emp_ids==[]:
                    continue
                dept_done=0
                for item in obj_emp.read(cr, uid, emp_ids, ['id', 'name']):
                    if dept_done==0:
                        emp_xml += emp_create_xml(self, cr, uid, 1, holiday_type, row_id, dept.id, dept.name, som, eom)
                        row_id = row_id +1
                    dept_done=1
                    emp_xml += emp_create_xml(self, cr, uid, 0, holiday_type, row_id, item['id'], item['name'], som, eom)
                    row_id = row_id +1
                    
        header_xml = '''
        <header>
        <date>%s</date>
        <company>%s</company>
        </header>
        ''' % (str(rml_obj.formatLang(time.strftime("%Y-%m-%d"),date=True))+' ' + str(time.strftime("%H:%M")),to_xml(pooler.get_pool(cr.dbname).get('res.users').browse(cr,uid,uid).company_id.name))

        # Computing the xml
        xml='''<?xml version="1.0" encoding="UTF-8" ?>
        <report>
        %s
        %s
        %s
        %s
        </report>
        ''' % (header_xml,months_xml,date_xml, ustr(emp_xml))

        return xml

report_custom('report.holidays.summary', 'hr.holidays', '', 'addons/hr_holidays/report/holidays_summary.xsl')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

