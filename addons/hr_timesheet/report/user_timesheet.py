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

from report.interface import report_rml
from report.interface import toxml
from tools.translate import _
import time
import pooler
from report import report_sxw
from tools import ustr

def lengthmonth(year, month):
    if month == 2 and ((year % 4 == 0) and ((year % 100 != 0) or (year % 400 == 0))):
        return 29
    return [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]

class report_custom(report_rml):

    def get_month_name(self, cr, uid, month, context=None):
        _months = {1:_("January"), 2:_("February"), 3:_("March"), 4:_("April"), 5:_("May"), 6:_("June"), 7:_("July"), 8:_("August"), 9:_("September"), 10:_("October"), 11:_("November"), 12:_("December")}
        return _months[month]
    def get_weekday_name(self, cr, uid, weekday, context=None):
        _weekdays = {1:_('Mon'), 2:_('Tue'), 3:_('Wed'), 4:_('Thu'), 5:_('Fri'), 6:_('Sat'), 7:_('Sun')}
        return _weekdays[weekday]

    def create_xml(self, cr, uid, ids, data, context):

        # Get the user id from the selected employee record
        emp_id = data['form']['employee_id']
        emp_obj = pooler.get_pool(cr.dbname).get('hr.employee')
        user_id = emp_obj.browse(cr, uid, emp_id).user_id.id
        empl_name = emp_obj.browse(cr, uid, emp_id).name

        # Computing the dates (start of month: som, and end of month: eom)
        som = datetime.date(data['form']['year'], data['form']['month'], 1)
        eom = som + datetime.timedelta(lengthmonth(som.year, som.month))

        date_xml = ['<date month="%s" year="%d" />' % (self.get_month_name(cr, uid, som.month, context=context), som.year), '<days>']
        date_xml += ['<day number="%d" name="%s" weekday="%d" />' % (x, self.get_weekday_name(cr, uid, som.replace(day=x).weekday()+1, context=context), som.replace(day=x).weekday()+1) for x in range(1, lengthmonth(som.year, som.month)+1)]

        date_xml.append('</days>')
        date_xml.append('<cols>2.5cm%s,2cm</cols>\n' % (',0.7cm' * lengthmonth(som.year, som.month)))

        # Sum attendence by account, then by day
        accounts = {}
        header_xml = ''
        if user_id:
            # Computing the attendence by analytical account
            cr.execute(
                "select line.date, (unit_amount / unit.factor) as amount, account_id, account.name "\
                "from account_analytic_line as line, hr_analytic_timesheet as hr, "\
                "account_analytic_account as account, product_uom as unit "\
                "where hr.line_id=line.id and line.account_id=account.id "\
                "and product_uom_id = unit.id "\
                "and line.user_id=%s and line.date >= %s and line.date < %s "
                "order by line.date",
                (user_id, som.strftime('%Y-%m-%d'), eom.strftime('%Y-%m-%d')))

            for presence in cr.dictfetchall():
                day = int(presence['date'][-2:])
                account = accounts.setdefault((presence['account_id'], presence['name']), {})
                account[day] = account.get(day, 0.0) + presence['amount']

        xml = '''
        <time-element date="%s">
            <amount>%.2f</amount>
        </time-element>
        '''
        rpt_obj = pooler.get_pool(cr.dbname).get('hr.employee')
        rml_obj = report_sxw.rml_parse(cr, uid, rpt_obj._name,context)
        if user_id:
            header_xml = '''
            <header>
            <date>%s</date>
            <company>%s</company>
            </header>
            ''' %  (str(rml_obj.formatLang(time.strftime("%Y-%m-%d"),date=True))+' ' + str(time.strftime("%H:%M")),pooler.get_pool(cr.dbname).get('res.users').browse(cr,uid,user_id).company_id.name)

        account_xml = []
        for account, telems in accounts.iteritems():
            aid, aname = account
            aname = pooler.get_pool(cr.dbname).get('account.analytic.account').name_get(cr, uid, [aid], context)
            aname = aname[0][1]

            account_xml.append('<account id="%d" name="%s">' % (aid, toxml(aname)))
            account_xml.append('\n'.join([xml % (day, amount) for day, amount in telems.iteritems()]))
            account_xml.append('</account>')

        # Computing the xml
        xml = '''<?xml version="1.0" encoding="UTF-8" ?>
        <report>
        %s
        <employee>%s</employee>
        %s
        </report>
        ''' % (header_xml, ustr(toxml(empl_name)), '\n'.join(date_xml) + '\n'.join(account_xml))
        return xml

report_custom('report.hr.analytical.timesheet', 'hr.employee', '', 'addons/hr_timesheet/report/user_timesheet.xsl')

