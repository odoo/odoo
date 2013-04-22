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
from openerp.report.interface import report_rml
from openerp.report.interface import toxml
import time
from openerp import pooler
from openerp.tools.translate import _
from openerp.report import report_sxw
from openerp.tools import ustr
from openerp.tools import to_xml


def lengthmonth(year, month):
    if month == 2 and ((year % 4 == 0) and ((year % 100 != 0) or (year % 400 == 0))):
        return 29
    return [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]

def emp_create_xml(cr, id, som, eom, emp):
    # Computing the attendence by analytical account
    cr.execute(
        "select line.date, (unit_amount / unit.factor) as amount "\
        "from account_analytic_line as line, hr_analytic_timesheet as hr, "\
        "product_uom as unit "\
        "where hr.line_id=line.id "\
        "and product_uom_id = unit.id "\
        "and line.user_id=%s and line.date >= %s and line.date < %s "
        "order by line.date",
        (id, som.strftime('%Y-%m-%d'), eom.strftime('%Y-%m-%d')))

    # Sum by day
    month = {}
    for presence in cr.dictfetchall():
        day = int(presence['date'][-2:])
        month[day] = month.get(day, 0.0) + presence['amount']

    xml = '''
    <time-element date="%s">
        <amount>%.2f</amount>
    </time-element>
    '''
    time_xml = ([xml % (day, amount) for day, amount in month.iteritems()])

    # Computing the xml
    xml = '''
    <employee id="%d" name="%s">
    %s
    </employee>
    ''' % (id, toxml(emp), '\n'.join(time_xml))
    return xml

class report_custom(report_rml):

    def get_month_name(self, cr, uid, month, context=None):
        _months = {1:_("January"), 2:_("February"), 3:_("March"), 4:_("April"), 5:_("May"), 6:_("June"), 7:_("July"), 8:_("August"), 9:_("September"), 10:_("October"), 11:_("November"), 12:_("December")}
        return _months[month]

    def get_weekday_name(self, cr, uid, weekday, context=None):
        _weekdays = {1:_('Mon'), 2:_('Tue'), 3:_('Wed'), 4:_('Thu'), 5:_('Fri'), 6:_('Sat'), 7:_('Sun')}
        return _weekdays[weekday]

    def create_xml(self, cr, uid, ids, data, context):

        # Computing the dates (start of month: som, and end of month: eom)
        som = datetime.date(data['form']['year'], data['form']['month'], 1)
        eom = som + datetime.timedelta(lengthmonth(som.year, som.month))
        date_xml = ['<date month="%s" year="%d" />' % (self.get_month_name(cr, uid, som.month, context=context), som.year), '<days>']
        date_xml += ['<day number="%d" name="%s" weekday="%d" />' % (x, self.get_weekday_name(cr, uid, som.replace(day=x).weekday()+1, context=context), som.replace(day=x).weekday()+1) for x in range(1, lengthmonth(som.year, som.month)+1)]
        date_xml.append('</days>')
        date_xml.append('<cols>2.5cm%s,2cm</cols>\n' % (',0.7cm' * lengthmonth(som.year, som.month)))

        emp_xml=''
        emp_obj = pooler.get_pool(cr.dbname).get('hr.employee')        
        for id in data['form']['employee_ids']:
            user = emp_obj.browse(cr, uid, id).user_id.id
            empl_name = emp_obj.browse(cr, uid, id).name
            if user:
                emp_xml += emp_create_xml(cr, user, som, eom, empl_name)
        # Computing the xml
        #Without this, report don't show non-ascii characters (TO CHECK)
        date_xml = '\n'.join(date_xml)
        rpt_obj = pooler.get_pool(cr.dbname).get('hr.employee')
        rml_obj=report_sxw.rml_parse(cr, uid, rpt_obj._name,context)
        header_xml = '''
        <header>
        <date>%s</date>
        <company>%s</company>
        </header>
        '''  % (str(rml_obj.formatLang(time.strftime("%Y-%m-%d"),date=True))+' ' + str(time.strftime("%H:%M")),to_xml(pooler.get_pool(cr.dbname).get('res.users').browse(cr,uid,uid).company_id.name))

        xml='''<?xml version="1.0" encoding="UTF-8" ?>
        <report>
        %s
        %s
        %s
        </report>
        ''' % (header_xml,date_xml, ustr(emp_xml))
        return xml

report_custom('report.hr.analytical.timesheet_users', 'hr.employee', '', 'addons/hr_timesheet/report/users_timesheet.xsl')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

