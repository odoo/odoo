# -*- coding: utf-8 -*-
import datetime
import time

from osv import fields, osv
from report.interface import report_rml
from report.interface import toxml

import pooler


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
    

def emp_create_xml(self,cr,uid,dept,holiday_type,row_id,empid,name,som,eom):
    display={}

    if dept==0:
        count=0
        p_id=pooler.get_pool(cr.dbname).get('hr.holidays').search(cr,uid,[('employee_id','in',[empid,False]), ('type', '=', 'remove')])
        ids_date = pooler.get_pool(cr.dbname).get('hr.holidays').read(cr,uid,p_id,['date_from','date_to','holiday_status_id','state'])
        
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

    xml = '''
        <time-element index="%d">
            <value>%s</value>
        </time-element>
        '''
    time_xml = ([xml % (index, value) for index,value in display.iteritems()])
    data_xml=['<info id="%d" number="%d" val="%s" />' % (row_id,x,display[x]) for x in range(1,len(display)+1) ]

    # Computing the xml
    xml = '''
    %s
    <employee row="%d" id="%d" name="%s" sum="%s">
    %s
    </employee>
    ''' % (data_xml,row_id,dept, toxml(name),count, '\n'.join(time_xml))

    return xml

class report_custom(report_rml):
    def create_xml(self, cr, uid, ids, data, context):
        depts=[]
        emp_id={}
#        done={}

        cr.execute("select name from res_company")
        res=cr.fetchone()[0]
        date_xml=[]
        date_today=time.strftime('%Y-%m-%d %H:%M:%S')
        date_xml +=['<res name="%s" today="%s" />' % (res,date_today)]

        cr.execute("select id,name,color_name from hr_holidays_status order by id")
        legend=cr.fetchall()
        today=datetime.datetime.today()

        first_date=data['form']['date_from']

        som = strToDate(first_date)
        eom = som+datetime.timedelta(59)
        day_diff=eom-som

        if data['form']['holiday_type']!='both':
            type=data['form']['holiday_type']
            if data['form']['holiday_type']=='Confirmed':
                holiday_type=('confirm')
            else:
                holiday_type=('validate')
        else:
            type="Confirmed and Validated"
            holiday_type=('confirm','validate')
        date_xml.append('<from>%s</from>\n'% (som))
        date_xml.append('<to>%s</to>\n' %(eom))
        date_xml.append('<type>%s</type>'%(type))

#        date_xml=[]
        for l in range(0,len(legend)):
            date_xml += ['<legend row="%d" id="%d" name="%s" color="%s" />' % (l+1,legend[l][0],legend[l][1],legend[l][2])]

        date_xml += ['<date month="%s" year="%d" />' % (som.strftime('%B'), som.year),'<days>']

        cell=1
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
                if day_diff1>30:
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
        date_xml.append('<cols>3.5cm%s,0.4cm</cols>\n' % (',0.4cm' * (60)))

        st='<cols_months>3.5cm'
        for m in range(1,len(width_dict)+1):
            st+=',' + str(0.4 *width_dict[m])+'cm'
        st+=',0.4cm</cols_months>\n'

        months_xml =['<months  number="%d" name="%s" />' % (x,month_dict[x]) for x in range(1,len(month_dict)+1) ]
        months_xml.append(st)

        emp_xml=''
        row_id=1

        if data['model']=='hr.employee':

            for id in data['form']['emp'][0][2]:
                 items = pooler.get_pool(cr.dbname).get('hr.employee').read(cr,uid,id,['id','name'])

                 emp_xml += emp_create_xml(self,cr,uid,0,holiday_type,row_id,items['id'],items['name'],som, eom)
                 row_id = row_id +1
                 
        elif data['model']=='ir.ui.menu':
            for id in data['form']['depts'][0][2]:
                dept = pooler.get_pool(cr.dbname).get('hr.department').browse(cr, uid, id, context.copy())
                depts.append(dept)
                dept_ids = tuple(data['form']['depts'][0][2])
                
                cr.execute("""select dept_user.user_id \
                from hr_department_user_rel dept_user \
                where dept_user.department_id = %s\
                union\
                select dept.manager_id from hr_department dept\
                where dept.id = %s""", (id, id))

                result=cr.fetchall()
                if result==[]:
                    continue
                dept_done=0
                for d in range(0,len(result)):
                    emp_id[d]=pooler.get_pool(cr.dbname).get('hr.employee').search(cr,uid,[('user_id','=',result[d][0])])
                    items = pooler.get_pool(cr.dbname).get('hr.employee').read(cr,uid,emp_id[d],['id','name'])
                    for item in items:
#                        if item['id'] in done:
#                            continue
#                        else:
                        if dept_done==0:
                            emp_xml += emp_create_xml(self,cr,uid,1,holiday_type,row_id,dept.id,dept.name,som, eom)
                            row_id = row_id +1
                        dept_done=1

#                        done[item['id']] = 1
                        emp_xml += emp_create_xml(self,cr,uid,0,holiday_type,row_id,item['id'],item['name'],som, eom)
                        row_id = row_id +1

        # Computing the xml
        xml='''<?xml version="1.0" encoding="UTF-8" ?>
        <report>
        %s
        %s
        %s
        </report>
        ''' % (months_xml,date_xml, emp_xml)
        
        return xml

report_custom('report.holidays.summary', 'hr.holidays', '', 'addons/hr_holidays/report/holidays_summary.xsl')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

